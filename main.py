"""
CampusVoice - Campus Complaint Management System
Main application entry point.

Uses the production-ready app from src/api/__init__.py with proper
architecture: route -> service -> repository pattern, LLM integration,
database initialization via lifespan, and middleware stack.
"""

import sys
import uvicorn
from pathlib import Path

# Ensure project root is on sys.path so 'src' is importable
sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import settings
from src.utils.logger import app_logger
from src.api import create_app

# Create the production FastAPI application
app = create_app()


def main():
    """
    Main function to run the application.

    The app created by create_app() includes:
    - Lifespan handler that initializes DB tables and seeds data on startup
    - All middleware (CORS, auth, rate limiting, logging)
    - All API routes (students, complaints, authorities, admin, health)
    - Global exception handlers
    """
    app_logger.info("=" * 60)
    app_logger.info("CampusVoice - Campus Complaint Management System")
    app_logger.info("=" * 60)
    app_logger.info(f"Environment: {settings.ENVIRONMENT}")
    app_logger.info(f"Host: {settings.HOST}")
    app_logger.info(f"Port: {settings.PORT}")
    app_logger.info(f"Debug Mode: {settings.DEBUG}")
    app_logger.info(f"Workers: {settings.WORKERS}")
    app_logger.info(
        f"Database: {'PostgreSQL' if 'postgresql' in settings.DATABASE_URL else 'Other'}"
    )
    app_logger.info("=" * 60)

    # Run with Uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info",
        access_log=True,
        use_colors=True,
        loop="asyncio",
    )


if __name__ == "__main__":
    main()
