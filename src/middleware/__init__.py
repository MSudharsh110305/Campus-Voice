"""
Middleware package initialization.
All FastAPI middleware components.
"""

from fastapi import FastAPI
from .cors import setup_cors
from .auth import AuthMiddleware, require_role
from .rate_limit import RateLimitMiddleware
from .logging import RequestLoggingMiddleware, PerformanceLoggingMiddleware
from .error_handler import setup_exception_handlers


def setup_middleware(app: FastAPI):
    """
    Setup all middleware for the application.
    Middleware is executed in reverse order of addition.
    
    Order (execution):
    1. CORS (first to handle preflight)
    2. Request Logging (log all requests)
    3. Performance Logging (monitor slow requests)
    4. Rate Limiting (enforce limits)
    5. Authentication (validate tokens)
    
    Args:
        app: FastAPI application instance
    """
    # Setup exception handlers first
    setup_exception_handlers(app)
    
    # 1. CORS (must be first)
    setup_cors(app)
    
    # 2. Request Logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # 3. Performance Logging (1 second threshold)
    app.add_middleware(PerformanceLoggingMiddleware, slow_threshold_ms=1000)
    
    # 4. Rate Limiting
    app.add_middleware(RateLimitMiddleware, enabled=True)
    
    # 5. Authentication (last, so it runs first in execution)
    app.add_middleware(AuthMiddleware)


__all__ = [
    "setup_middleware",
    "setup_cors",
    "setup_exception_handlers",
    "AuthMiddleware",
    "RateLimitMiddleware",
    "RequestLoggingMiddleware",
    "PerformanceLoggingMiddleware",
    "require_role",
]
