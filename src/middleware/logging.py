"""
Request/response logging middleware.
"""

import time
import logging
import json
from typing import Callable
from uuid import uuid4
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.
    Includes request ID, duration, status code, etc.
    """
    
    # Routes to skip detailed logging
    SKIP_ROUTES = [
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request through logging middleware.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
        
        Returns:
            Response with logging
        """
        # Generate request ID
        request_id = str(uuid4())
        request.state.request_id = request_id
        
        # Skip detailed logging for certain routes
        should_skip = any(route in request.url.path for route in self.SKIP_ROUTES)
        
        # Start timer
        start_time = time.time()
        
        # Log request
        if not should_skip:
            await self._log_request(request, request_id)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration:.4f}"
            
            # Log response
            if not should_skip:
                await self._log_response(request, response, duration, request_id)
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed | "
                f"ID: {request_id} | "
                f"Method: {request.method} | "
                f"Path: {request.url.path} | "
                f"Duration: {duration:.4f}s | "
                f"Error: {str(e)}"
            )
            raise
    
    async def _log_request(self, request: Request, request_id: str):
        """
        Log incoming request details.
        
        Args:
            request: FastAPI request
            request_id: Request ID
        """
        # Get user info if available
        user_id = getattr(request.state, "user_id", "anonymous")
        role = getattr(request.state, "role", "unauthenticated")
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        
        # Build log data
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params) if request.query_params else None,
            "user_id": user_id,
            "role": role,
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent", "unknown")
        }
        
        # Log body for POST/PUT/PATCH (be careful with sensitive data)
        if request.method in ["POST", "PUT", "PATCH"]:
            # Don't log password fields
            # In production, be more careful about what you log
            log_data["has_body"] = True
        
        logger.info(f"Incoming request | {json.dumps(log_data)}")
    
    async def _log_response(
        self,
        request: Request,
        response: Response,
        duration: float,
        request_id: str
    ):
        """
        Log response details.
        
        Args:
            request: FastAPI request
            response: Response object
            duration: Request duration in seconds
            request_id: Request ID
        """
        # Get user info
        user_id = getattr(request.state, "user_id", "anonymous")
        
        # Build log data
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "user_id": user_id
        }
        
        # Log at appropriate level based on status code
        if response.status_code >= 500:
            logger.error(f"Response | {json.dumps(log_data)}")
        elif response.status_code >= 400:
            logger.warning(f"Response | {json.dumps(log_data)}")
        else:
            logger.info(f"Response | {json.dumps(log_data)}")


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log slow requests for performance monitoring.
    """
    
    def __init__(self, app, slow_threshold_ms: float = 1000):
        """
        Initialize performance logging middleware.
        
        Args:
            app: FastAPI application
            slow_threshold_ms: Threshold in milliseconds for slow request warning
        """
        super().__init__(app)
        self.slow_threshold_ms = slow_threshold_ms
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request and log if slow.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
        
        Returns:
            Response
        """
        start_time = time.time()
        
        response = await call_next(request)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Log slow requests
        if duration_ms > self.slow_threshold_ms:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(
                f"SLOW REQUEST | "
                f"ID: {request_id} | "
                f"Method: {request.method} | "
                f"Path: {request.url.path} | "
                f"Duration: {duration_ms:.2f}ms"
            )
        
        return response


__all__ = ["RequestLoggingMiddleware", "PerformanceLoggingMiddleware"]
