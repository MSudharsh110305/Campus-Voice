"""
Auth endpoints — token refresh.

POST /api/auth/refresh — exchange a valid refresh token for a new access token.
This route is intentionally public (no auth middleware protection) so it can
be called even when the access token has expired.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.services.auth_service import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ==================== REQUEST / RESPONSE SCHEMAS ====================

class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ==================== REFRESH ENDPOINT ====================

@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Refresh access token",
    description=(
        "Exchange a valid refresh token for a new short-lived access token. "
        "Returns 401 if the refresh token is expired, invalid, or is not a refresh token."
    ),
)
async def refresh_access_token(body: RefreshRequest):
    """
    Refresh an access token using a refresh token.

    - **refresh_token**: A long-lived refresh token previously issued at login.

    Returns a new access token. The refresh token itself is NOT rotated.
    """
    token = body.refresh_token

    # Decode — returns None if expired or invalid
    payload = auth_service.decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is expired or invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Must be a refresh token, not an access token
    token_type = payload.get("type", "access")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided token is not a refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    subject = payload.get("sub")
    role = payload.get("role")

    if not subject or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing required claims.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue a new access token
    try:
        new_access_token = auth_service.create_access_token(
            subject=subject,
            role=role,
        )
    except Exception as e:
        logger.error(f"Failed to create access token during refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not issue new access token.",
        )

    expires_in = int(auth_service._access_token_expiry(role).total_seconds())

    logger.info(f"Access token refreshed for subject={subject} role={role}")

    return RefreshResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=expires_in,
    )
