"""
CORS middleware configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings


def setup_cors(app: FastAPI):
    """
    Setup CORS middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        expose_headers=[
            "X-Total-Count",
            "X-Page-Number",
            "X-Page-Size",
            "X-Total-Pages",
            "X-Rate-Limit-Limit",
            "X-Rate-Limit-Remaining",
            "X-Rate-Limit-Reset"
        ],
        max_age=3600,  # Cache preflight requests for 1 hour
    )


__all__ = ["setup_cors"]
