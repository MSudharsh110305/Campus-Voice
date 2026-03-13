"""
JWT utility functions (additional helpers beyond auth_service).
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.services.auth_service import auth_service
from src.utils.exceptions import InvalidTokenError, TokenExpiredError


security = HTTPBearer()


def extract_token_from_header(authorization: str) -> Optional[str]:
    """
    Extract JWT token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Token string or None
    """
    if not authorization:
        return None
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]


def get_current_user_from_token(token: str) -> Dict[str, Any]:
    """
    Get current user info from JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        User info dictionary
        
    Raises:
        InvalidTokenError: If token is invalid
        TokenExpiredError: If token is expired
    """
    payload = auth_service.decode_token(token)
    if not payload:
        raise InvalidTokenError()
    
    # Check expiration with timezone-aware datetime
    exp = payload.get("exp")
    if exp:
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        if datetime.now(timezone.utc) > exp_datetime:
            raise TokenExpiredError()
    
    return {
        "user_id": payload.get("sub"),
        "role": payload.get("role"),
        "payload": payload
    }


def verify_token_role(token: str, allowed_roles: list) -> bool:
    """
    Verify if token has required role.
    
    Args:
        token: JWT token string
        allowed_roles: List of allowed roles
        
    Returns:
        True if role is allowed
    """
    try:
        user_info = get_current_user_from_token(token)
        return user_info.get("role") in allowed_roles
    except Exception:
        return False


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current user from token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User info dictionary
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        return get_current_user_from_token(credentials.credentials)
    except (InvalidTokenError, TokenExpiredError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_student(
    user: Dict[str, Any] = Depends(get_current_user)
) -> str:
    """
    FastAPI dependency to get current student.
    
    Args:
        user: Current user from token
        
    Returns:
        Student roll number
        
    Raises:
        HTTPException: If user is not a student
    """
    if user.get("role") != "Student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required"
        )
    
    return user.get("user_id")


async def get_current_authority(
    user: Dict[str, Any] = Depends(get_current_user)
) -> int:
    """
    FastAPI dependency to get current authority.
    
    Args:
        user: Current user from token
        
    Returns:
        Authority ID
        
    Raises:
        HTTPException: If user is not an authority
    """
    if user.get("role") not in ["Authority", "Admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authority access required"
        )
    
    return int(user.get("user_id"))


__all__ = [
    "extract_token_from_header",
    "get_current_user_from_token",
    "verify_token_role",
    "get_current_user",
    "get_current_student",
    "get_current_authority",
    "security",
]
