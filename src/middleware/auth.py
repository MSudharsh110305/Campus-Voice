"""
Authentication middleware for protected routes.
"""

import logging
from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from src.utils.jwt_utils import extract_token_from_header, get_current_user_from_token
from src.utils.exceptions import InvalidTokenError, TokenExpiredError

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate JWT tokens for protected routes.
    Attaches user info to request.state if token is valid.
    """
    
    # Routes that don't require authentication
    PUBLIC_ROUTES = [
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/api/health",
        "/api/students/register",
        "/api/students/login",
        "/api/authorities/login",
        "/api/auth/refresh",
    ]
    
    # Route prefixes that don't require authentication
    PUBLIC_PREFIXES = [
        "/static",
        "/uploads",
        "/health",
        "/ping",
        "/metrics",
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request through authentication middleware.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
        
        Returns:
            Response
        """
        # Check if route is public
        if self._is_public_route(request.url.path):
            return await call_next(request)
        
        # Extract token from header, or fall back to ?token= query param
        # (query param is used for file download/attachment links opened in new tab)
        authorization = request.headers.get("Authorization")

        if not authorization:
            token_param = request.query_params.get("token")
            if token_param:
                authorization = f"Bearer {token_param}"

        if not authorization:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": "Missing authorization header",
                    "error_code": "MISSING_TOKEN"
                }
            )

        token = extract_token_from_header(authorization)
        
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": "Invalid authorization format",
                    "error_code": "INVALID_TOKEN_FORMAT"
                }
            )
        
        # Validate token
        try:
            user_info = get_current_user_from_token(token)

            # Reject refresh tokens being used as access tokens
            payload = user_info.get("payload", {})
            if payload.get("type", "access") != "access":
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "success": False,
                        "error": "Refresh tokens cannot be used for API access. Use your access token.",
                        "error_code": "WRONG_TOKEN_TYPE"
                    }
                )

            # Attach user info to request state
            request.state.user = user_info
            request.state.user_id = user_info.get("user_id")
            request.state.role = user_info.get("role")

            logger.debug(f"Authenticated user: {user_info.get('user_id')} ({user_info.get('role')})")

        except TokenExpiredError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": "Token has expired",
                    "error_code": "TOKEN_EXPIRED"
                }
            )
        except InvalidTokenError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": "Invalid token",
                    "error_code": "INVALID_TOKEN"
                }
            )
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": "Authentication failed",
                    "error_code": "AUTH_ERROR"
                }
            )
        
        # Continue to next middleware/route
        return await call_next(request)
    
    def _is_public_route(self, path: str) -> bool:
        """
        Check if route is public (doesn't require authentication).
        
        Args:
            path: Request path
        
        Returns:
            True if public route
        """
        # Check exact matches
        if path in self.PUBLIC_ROUTES:
            return True
        
        # Check prefixes
        for prefix in self.PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False


def require_role(allowed_roles: list):
    """
    Decorator to require specific roles for route access.
    
    Args:
        allowed_roles: List of allowed roles
    
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            user_role = getattr(request.state, "role", None)
            
            if not user_role or user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "success": False,
                        "error": "Insufficient permissions",
                        "error_code": "INSUFFICIENT_PERMISSIONS"
                    }
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


__all__ = ["AuthMiddleware", "require_role"]
