"""
Global error handler middleware.
"""

import logging
from typing import Callable
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from src.utils.exceptions import CampusVoiceException, to_http_exception

logger = logging.getLogger(__name__)


async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for all unhandled exceptions.
    
    Args:
        request: FastAPI request
        exc: Exception raised
    
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Handle CampusVoiceException
    if isinstance(exc, CampusVoiceException):
        http_exc = to_http_exception(exc)
        logger.warning(
            f"Application error | "
            f"ID: {request_id} | "
            f"Error: {exc.error_code} | "
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
    
    # Handle Starlette HTTPException
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
                "error_code": f"HTTP_{exc.status_code}",
                "request_id": request_id
            }
        )
    
    # Handle validation errors
    if isinstance(exc, RequestValidationError):
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in error["loc"][1:]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(
            f"Validation error | "
            f"ID: {request_id} | "
            f"Errors: {errors}"
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
    
    # Handle all other exceptions
    logger.error(
        f"Unhandled exception | "
        f"ID: {request_id} | "
        f"Type: {type(exc).__name__} | "
        f"Message: {str(exc)}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "request_id": request_id
        }
    )


def setup_exception_handlers(app):
    """
    Setup global exception handlers.
    
    Args:
        app: FastAPI application
    """
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(CampusVoiceException, global_exception_handler)
    app.add_exception_handler(RequestValidationError, global_exception_handler)


__all__ = ["global_exception_handler", "setup_exception_handlers"]
