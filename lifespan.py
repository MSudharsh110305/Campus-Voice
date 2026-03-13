"""
Application lifespan management.

Startup and shutdown event handlers.

✅ Consolidated startup/shutdown tasks
✅ Proper error handling with warnings
✅ Development-only table creation
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database.connection import engine
from src.config.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown tasks:
    - Database initialization and table creation (dev only)
    - Service initialization (LLM, rate limiter)
    - Graceful shutdown and cleanup
    """
    # ========== STARTUP ==========
    logger.info("=" * 80)
    logger.info(f"🚀 Starting CampusVoice API ({settings.ENVIRONMENT})")
    logger.info("=" * 80)
    
    # 1. Database connection
    try:
        from src.database.connection import init_db
        await init_db()
        logger.info("✅ Database connection verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # 2. Create tables (development only)
    if settings.ENVIRONMENT == "development":
        try:
            from src.database.models import (
                Base, Student, Authority, Department, ComplaintCategory,
                Complaint, Vote, StatusUpdate, AuthorityUpdate, Notification
            )
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables initialized")
        except Exception as e:
            logger.warning(f"⚠️  Table creation skipped: {e}")
    
    # 3. Initialize services (non-critical)
    try:
        from src.services.llm_service import llm_service
        logger.info("✅ LLM service ready")
    except Exception as e:
        logger.warning(f"⚠️  LLM service warning: {e}")
    
    try:
        from src.utils.rate_limiter import rate_limiter
        logger.info("✅ Rate limiter ready")
    except Exception as e:
        logger.warning(f"⚠️  Rate limiter warning: {e}")
    
    logger.info("=" * 80)
    logger.info("✅ Startup complete - Ready to accept requests")
    logger.info("=" * 80)
    
    yield  # Application runs here
    
    # ========== SHUTDOWN ==========
    logger.info("🛑 Shutting down...")
    
    try:
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Database shutdown error: {e}")
    
    try:
        from src.utils.rate_limiter import rate_limiter
        rate_limiter.clear()
        logger.info("✅ Rate limiter cleared")
    except Exception as e:
        logger.warning(f"⚠️  Cleanup warning: {e}")
    
    logger.info("✅ Shutdown complete")


__all__ = ["lifespan"]
