"""
Hybrid settings resolver — reads from SystemSetting table with fallback to env-based settings.
Uses a short TTL cache to avoid per-request DB hits.
"""

import time
import logging
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings

logger = logging.getLogger(__name__)

# In-memory cache: { key: (value, timestamp) }
_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 60  # seconds


# Mapping from SystemSetting keys → settings.py attribute names
_ENV_FALLBACKS = {
    "enable_spam_detection": "ENABLE_SPAM_DETECTION",
    "enable_image_verification": "ENABLE_IMAGE_VERIFICATION",
    "enable_auto_escalation": "ENABLE_AUTO_ESCALATION",
    "enable_push_notifications": "ENABLE_PUSH_NOTIFICATIONS",
    "enable_email_verification": "ENABLE_EMAIL_VERIFICATION",
    "rate_limit_student_complaints_per_day": "RATE_LIMIT_STUDENT_COMPLAINTS_PER_DAY",
    "rate_limit_global_per_minute": "RATE_LIMIT_GLOBAL_PER_MINUTE",
    "data_retention_months": "DATA_RETENTION_MONTHS",
    "auto_delete_old_complaints": "AUTO_DELETE_OLD_COMPLAINTS",
}


async def get_setting(key: str, db: AsyncSession) -> str:
    """
    Get effective setting value: DB override first, then env fallback.
    Results are cached for 60 seconds.
    """
    now = time.time()

    # Check cache
    if key in _cache:
        value, ts = _cache[key]
        if now - ts < _CACHE_TTL:
            return value

    # Query DB
    try:
        result = await db.execute(
            text("SELECT value FROM system_settings WHERE key = :k"),
            {"k": key}
        )
        row = result.first()
        if row and row[0] is not None:
            _cache[key] = (row[0], now)
            return row[0]
    except Exception as e:
        logger.debug(f"Settings resolver DB lookup failed for '{key}': {e}")

    # Fallback to env
    env_attr = _ENV_FALLBACKS.get(key)
    if env_attr and hasattr(settings, env_attr):
        val = str(getattr(settings, env_attr))
        # Normalize booleans from Python True/False → "true"/"false"
        if val in ("True", "False"):
            val = val.lower()
        _cache[key] = (val, now)
        return val

    return ""


async def get_bool(key: str, db: AsyncSession) -> bool:
    """Get a boolean setting."""
    val = await get_setting(key, db)
    return val.lower() == "true"


async def get_int(key: str, db: AsyncSession, default: int = 0) -> int:
    """Get an integer setting."""
    val = await get_setting(key, db)
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def get_cached_int(key: str, default: int = 0) -> int:
    """
    Synchronous read from the in-memory cache only — no DB access.
    Returns `default` when the cache has no entry for `key`.
    Useful in sync middleware that cannot await.
    """
    now = time.time()
    if key in _cache:
        value, ts = _cache[key]
        if now - ts < _CACHE_TTL:
            try:
                return int(value)
            except (ValueError, TypeError):
                pass
    return default


def invalidate(key: Optional[str] = None):
    """Invalidate cache for a key (or all keys)."""
    if key:
        _cache.pop(key, None)
    else:
        _cache.clear()


__all__ = ["get_setting", "get_bool", "get_int", "get_cached_int", "invalidate"]
