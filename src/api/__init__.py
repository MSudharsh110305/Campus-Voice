"""
API package initialization.

FastAPI application setup and route registration.

✅ FIXED: Proper lifespan context manager instead of deprecated events
✅ FIXED: Import from src.database.connection
✅ ADDED: Database initialization on startup
✅ ADDED: Comprehensive exception handlers
✅ ADDED: Request ID tracking
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Path to built frontend (relative to this file: src/api/__init__.py → project root)
_FRONTEND_DIST = Path(__file__).parent.parent.parent / "Campus-Voice-SREC-main" / "frontend" / "dist"

from src.config.settings import settings
from src.middleware import setup_middleware
from src.api.routes import create_api_router
from src.utils.exceptions import CampusVoiceException, to_http_exception

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    ✅ FIXED: Lifespan context manager for startup/shutdown.
    
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown").
    """
    # Startup
    logger.info(f"🚀 Starting CampusVoice API in {settings.ENVIRONMENT} mode")
    logger.info(f"📊 Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Local'}")
    logger.info(f"🌐 CORS Origins: {settings.CORS_ORIGINS}")
    
    # Initialize database (optional - tables should already exist from migrations)
    try:
        from src.database.connection import init_db
        await init_db()
        logger.info("✅ Database connection verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        # Don't raise - let health checks handle it
    
    # Start background task: check image upload deadlines every hour
    async def _image_deadline_loop():
        while True:
            await asyncio.sleep(3600)  # run every hour
            try:
                from src.database.connection import AsyncSessionLocal
                from src.services.complaint_service import check_expired_image_deadlines
                async with AsyncSessionLocal() as _sess:
                    count = await check_expired_image_deadlines(_sess)
                    if count:
                        logger.info(f"[BG] Image deadline check: processed {count} complaints")
            except Exception as _bg_err:
                logger.error(f"[BG] Image deadline check failed: {_bg_err}")

    _deadline_task = asyncio.create_task(_image_deadline_loop())

    yield  # Application runs here

    # Shutdown
    _deadline_task.cancel()
    try:
        await _deadline_task
    except asyncio.CancelledError:
        pass
    logger.info("🛑 Shutting down CampusVoice API")
    
    # Close database connections
    try:
        from src.database.connection import engine
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    # Create FastAPI app with lifespan
    app = FastAPI(
        title="CampusVoice API",
        description="Campus Complaint Management System with AI-powered categorization and intelligent routing",
        version="1.0.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,  # ✅ FIXED: Use lifespan instead of deprecated events
    )
    
    # Setup middleware
    setup_middleware(app)
    
    # Register routes
    api_router, root_router = create_api_router()
    app.include_router(api_router)
    app.include_router(root_router)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Serve frontend static assets
    if _FRONTEND_DIST.exists():
        assets_dir = _FRONTEND_DIST / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Root + SPA catch-all: serve index.html for all non-API paths
    @app.get("/", tags=["Root"])
    async def root():
        if _FRONTEND_DIST.exists():
            return FileResponse(str(_FRONTEND_DIST / "index.html"))
        return {
            "service": "CampusVoice API",
            "version": "1.0.0",
            "status": "running",
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve frontend SPA for all non-API routes."""
        if _FRONTEND_DIST.exists():
            # Serve root-level files (favicon.ico, manifest.json, sw.js, etc.)
            candidate = _FRONTEND_DIST / full_path
            if candidate.exists() and candidate.is_file():
                return FileResponse(str(candidate))
            # SPA fallback
            return FileResponse(str(_FRONTEND_DIST / "index.html"))
        return JSONResponse({"error": "Frontend not built"}, status_code=404)

    return app


def setup_exception_handlers(app: FastAPI):
    """
    Setup global exception handlers.
    
    Handles:
    - Custom CampusVoiceException
    - HTTP exceptions
    - Validation errors
    - Unhandled exceptions
    
    Args:
        app: FastAPI application
    """
    
    @app.exception_handler(CampusVoiceException)
    async def campus_voice_exception_handler(request: Request, exc: CampusVoiceException):
        """
        Handle custom CampusVoiceException.
        
        Converts application exceptions to proper HTTP responses.
        """
        http_exc = to_http_exception(exc)
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.warning(
            f"Application error | "
            f"ID: {request_id} | "
            f"Path: {request.url.path} | "
            f"Code: {exc.error_code} | "
            f"Message: {exc.message}"
        )
        
        return JSONResponse(
            status_code=http_exc.status_code,
            content={
                "success": False,
                "error": exc.message,
                "error_code": exc.error_code,
                "details": exc.details,
                "request_id": request_id
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """
        Handle standard HTTP exceptions.
        
        Provides consistent error response format.
        """
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.warning(
            f"HTTP exception | "
            f"ID: {request_id} | "
            f"Path: {request.url.path} | "
            f"Status: {exc.status_code} | "
            f"Detail: {exc.detail}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
                "error_code": f"HTTP_{exc.status_code}",
                "request_id": request_id
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """
        Handle Pydantic validation errors.
        
        Formats validation errors in a user-friendly way.
        """
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Format validation errors
        errors = []
        for error in exc.errors():
            field_path = ".".join(str(x) for x in error["loc"][1:]) if len(error["loc"]) > 1 else str(error["loc"][0])
            errors.append({
                "field": field_path,
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(
            f"Validation error | "
            f"ID: {request_id} | "
            f"Path: {request.url.path} | "
            f"Errors: {len(errors)}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": "Validation error",
                "error_code": "VALIDATION_ERROR",
                "details": {"validation_errors": errors},
                "request_id": request_id
            }
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Handle all unhandled exceptions.
        
        Last resort error handler for unexpected errors.
        """
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.error(
            f"Unhandled exception | "
            f"ID: {request_id} | "
            f"Path: {request.url.path} | "
            f"Type: {type(exc).__name__} | "
            f"Message: {str(exc)}",
            exc_info=True
        )
        
        # In production, don't expose internal errors
        if settings.ENVIRONMENT == "production":
            error_message = "Internal server error"
            error_details = None
        else:
            error_message = str(exc)
            error_details = {
                "type": type(exc).__name__,
                "traceback": str(exc.__traceback__) if hasattr(exc, '__traceback__') else None
            }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": error_message,
                "error_code": "INTERNAL_ERROR",
                "details": error_details,
                "request_id": request_id
            }
        )


# Create application instance
app = create_app()


__all__ = ["app", "create_app"]
