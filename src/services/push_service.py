"""Push notification sender using the Web Push Protocol.

Requires pywebpush: pip install pywebpush
If pywebpush is not installed, all push sends are silently skipped.
"""
import json
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database.models import PushSubscription
from src.config.settings import settings

logger = logging.getLogger(__name__)


async def send_push_to_user(
    db: AsyncSession,
    user_id: str,
    title: str,
    body: str,
    url: str = "/",
    urgency: str = "normal",
) -> int:
    """Send a push notification to all subscriptions for a user.

    Args:
        db: Async database session
        user_id: The student roll_no or authority id (as string)
        title: Notification title
        body: Notification body text
        url: URL to open when notification is clicked
        urgency: "very-low" | "low" | "normal" | "high"

    Returns:
        Number of subscriptions successfully sent to
    """
    if not settings.ENABLE_PUSH_NOTIFICATIONS:
        return 0
    if not settings.VAPID_PRIVATE_KEY:
        logger.debug("VAPID_PRIVATE_KEY not configured — skipping push notification")
        return 0

    result = await db.execute(
        select(PushSubscription).where(PushSubscription.user_id == str(user_id))
    )
    subscriptions = result.scalars().all()

    if not subscriptions:
        return 0

    payload = {"title": title, "body": body, "url": url, "urgency": urgency}
    sent = 0
    stale_endpoints = []

    for sub in subscriptions:
        try:
            success = await _send_push(sub, payload)
            if success:
                sent += 1
            else:
                stale_endpoints.append(sub.endpoint)
        except Exception as e:
            logger.warning(f"Push send failed for endpoint {sub.endpoint[:50]}…: {e}")

    # Remove stale subscriptions (410 Gone responses)
    if stale_endpoints:
        try:
            from sqlalchemy import text
            for ep in stale_endpoints:
                await db.execute(
                    text("DELETE FROM push_subscriptions WHERE endpoint = :ep"),
                    {"ep": ep},
                )
            await db.commit()
            logger.info(f"Removed {len(stale_endpoints)} stale push subscription(s)")
        except Exception as e:
            logger.warning(f"Failed to remove stale push subscriptions: {e}")

    return sent


async def _send_push(sub: PushSubscription, payload: dict) -> bool:
    """Send a single push notification via pywebpush.

    Returns True on success, False if subscription is gone (should be removed).
    Raises on unexpected errors.
    """
    try:
        from pywebpush import webpush, WebPushException
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
        )
        return True
    except ImportError:
        logger.debug("pywebpush not installed — push not sent. Install with: pip install pywebpush")
        return False
    except Exception as e:
        err_str = str(e)
        # 410 Gone = subscription expired/unregistered
        if "410" in err_str or "Gone" in err_str:
            logger.debug(f"Push subscription gone (410): {sub.endpoint[:50]}")
            return False
        # 404 = endpoint not found
        if "404" in err_str:
            return False
        raise
