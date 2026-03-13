"""Push notification subscription endpoints (Web Push Protocol)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel
from src.api.dependencies import get_db, get_current_user
from src.database.models import PushSubscription
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications/push", tags=["Push Notifications"])


class PushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class PushSubscribeResponse(BaseModel):
    success: bool
    message: str


@router.post("/subscribe", response_model=PushSubscribeResponse)
async def subscribe_push(
    data: PushSubscribeRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Store or update a push subscription for the current user."""
    # user_id is the JWT sub (roll_no for students, email for authorities)
    user_id = str(user.get("user_id") or "")
    role = (user.get("role") or "").lower()
    user_type = "student" if role == "student" else "authority"

    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to identify user")

    # Upsert: update if endpoint exists, otherwise insert
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == data.endpoint)
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub.p256dh = data.p256dh
        sub.auth = data.auth
        sub.user_id = user_id
        sub.user_type = user_type
    else:
        sub = PushSubscription(
            user_type=user_type,
            user_id=user_id,
            endpoint=data.endpoint,
            p256dh=data.p256dh,
            auth=data.auth,
        )
        db.add(sub)

    await db.commit()
    return PushSubscribeResponse(success=True, message="Push subscription saved")


@router.delete("/unsubscribe")
async def unsubscribe_push(
    endpoint: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a push subscription by endpoint."""
    user_id = str(user.get("user_id") or "")
    await db.execute(
        text("DELETE FROM push_subscriptions WHERE endpoint = :endpoint AND user_id = :user_id"),
        {"endpoint": endpoint, "user_id": user_id},
    )
    await db.commit()
    return {"success": True, "message": "Push subscription removed"}
