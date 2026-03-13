"""
Rate limiting middleware.
"""

import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from src.utils.rate_limiter import rate_limiter
from src.config.settings import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits on API requests.
    Uses token bucket algorithm for rate limiting.
    """
    
    # Routes exempt from rate limiting
    EXEMPT_ROUTES = [
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    # Route patterns exempt from rate limiting (voting, profile viewing, etc.)
    EXEMPT_PATTERNS = [
        "/api/complaints/",  # GET endpoints for viewing complaints
        "/api/students/profile",  # Profile viewing
        "/api/complaints/public-feed",  # Feed viewing
    ]
    
    def __init__(self, app, enabled: bool = True):
        """
        Initialize rate limit middleware.
        
        Args:
            app: FastAPI application
            enabled: Whether rate limiting is enabled
        """
        super().__init__(app)
        self.enabled = enabled and settings.RATE_LIMIT_ENABLED
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request through rate limiting middleware.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
        
        Returns:
            Response
        """
        if not self.enabled:
            return await call_next(request)
        
        # Check if route is exempt
        if self._is_exempt_route(request.url.path):
            return await call_next(request)
        
        # Get user identifier
        user_id = self._get_user_identifier(request)
        
        if not user_id:
            # No user identifier, allow but log
            logger.warning(f"No user identifier for rate limiting: {request.url.path}")
            return await call_next(request)
        
        # Determine rate limit based on user role
        rate_limit = self._get_rate_limit_for_user(request)
        
        if not rate_limit:
            return await call_next(request)
        
        max_requests, window_seconds = rate_limit
        
        # Check rate limit
        try:
            allowed = await rate_limiter.check_rate_limit(
                key=user_id,
                max_requests=max_requests,
                window_seconds=window_seconds
            )
            
            if not allowed:
                # Get bucket for wait time calculation
                bucket_key = f"{user_id}:{max_requests}:{window_seconds}"
                bucket = rate_limiter.buckets.get(bucket_key)
                
                wait_time = 0
                if bucket:
                    wait_time = int(await bucket.get_wait_time())
                
                logger.warning(f"Rate limit exceeded for {user_id}")
                
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": "Rate limit exceeded",
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "details": {
                            "retry_after": wait_time,
                            "limit": max_requests,
                            "window": window_seconds
                        }
                    },
                    headers={
                        "X-Rate-Limit-Limit": str(max_requests),
                        "X-Rate-Limit-Remaining": "0",
                        "X-Rate-Limit-Reset": str(wait_time),
                        "Retry-After": str(wait_time)
                    }
                )
            
            # Add rate limit headers to response
            response = await call_next(request)
            
            # Calculate remaining requests (approximate)
            bucket_key = f"{user_id}:{max_requests}:{window_seconds}"
            bucket = rate_limiter.buckets.get(bucket_key)
            remaining = int(bucket.tokens) if bucket else max_requests
            
            response.headers["X-Rate-Limit-Limit"] = str(max_requests)
            response.headers["X-Rate-Limit-Remaining"] = str(max(0, remaining))
            response.headers["X-Rate-Limit-Reset"] = str(window_seconds)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # On error, allow request but log
            return await call_next(request)
    
    def _is_exempt_route(self, path: str) -> bool:
        """
        Check if route is exempt from rate limiting.

        Args:
            path: Request path

        Returns:
            True if exempt
        """
        # Check exact matches
        if path in self.EXEMPT_ROUTES:
            return True

        # Check pattern matches (GET requests to viewing endpoints)
        # ✅ Exempt voting endpoints
        if "/vote" in path:
            return True

        # ✅ Exempt GET requests (only rate limit POST for complaint submission)
        # This is handled in _get_rate_limit_for_user by only applying limits to specific POST routes
        return False
    
    def _get_user_identifier(self, request: Request) -> str:
        """
        Get user identifier for rate limiting.
        
        Args:
            request: FastAPI request
        
        Returns:
            User identifier (user_id or IP)
        """
        # Try to get authenticated user
        user_id = getattr(request.state, "user_id", None)
        role = getattr(request.state, "role", None)
        
        if user_id and role:
            return f"{role}:{user_id}"
        
        # Fall back to IP address for unauthenticated requests
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _get_rate_limit_for_user(self, request: Request) -> tuple:
        """
        Get rate limit configuration for user.

        Args:
            request: FastAPI request

        Returns:
            Tuple of (max_requests, window_seconds) or None (if no limit)
        """
        role = getattr(request.state, "role", None)

        if role == "Student":
            # Only rate limit complaint submission (not voting or viewing)
            if request.url.path == "/api/complaints/submit" and request.method == "POST":
                # 5 complaints per day
                return (
                    settings.RATE_LIMIT_STUDENT_COMPLAINTS_PER_DAY,
                    86400  # 24 hours
                )

            # Students can freely view, vote, and interact without rate limits
            return None

        elif role in ["Authority", "Admin"]:
            # Authorities/Admins not rate limited
            return None

        else:
            # Unauthenticated requests - global rate limit (login, registration)
            return (
                settings.RATE_LIMIT_GLOBAL_PER_MINUTE,
                60
            )


__all__ = ["RateLimitMiddleware"]
