"""
General utility helper functions.
"""

import hashlib
import secrets
import string
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from uuid import UUID


def generate_random_string(length: int = 32) -> str:
    """
    Generate random string.
    
    Args:
        length: Length of string
    
    Returns:
        Random string
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_verification_token() -> str:
    """
    Generate email verification token.
    
    Returns:
        Verification token
    """
    return secrets.token_urlsafe(32)


def hash_string(text: str) -> str:
    """
    Hash string using SHA256.
    
    Args:
        text: Text to hash
    
    Returns:
        Hexadecimal hash
    """
    return hashlib.sha256(text.encode()).hexdigest()


def calculate_age_from_dob(dob: datetime) -> int:
    """
    Calculate age from date of birth.
    
    Args:
        dob: Date of birth
    
    Returns:
        Age in years
    """
    today = datetime.now()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime to string.
    
    Args:
        dt: Datetime object
        format_str: Format string
    
    Returns:
        Formatted datetime string
    """
    return dt.strftime(format_str)


def parse_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse datetime from string.
    
    Args:
        dt_str: Datetime string
        format_str: Format string
    
    Returns:
        Datetime object
    """
    return datetime.strptime(dt_str, format_str)


def get_time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string.
    
    Args:
        dt: Datetime object (timezone-aware or naive UTC)
    
    Returns:
        Time ago string (e.g., "2 hours ago")
    """
    # Ensure dt is timezone-aware (assume UTC if naive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"


def paginate_list(items: List[Any], page: int, page_size: int) -> Dict[str, Any]:
    """
    Paginate a list of items.
    
    Args:
        items: List of items
        page: Page number (1-indexed)
        page_size: Items per page
    
    Returns:
        Dictionary with paginated data
    """
    total = len(items)
    total_pages = (total + page_size - 1) // page_size
    
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1
    }


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def mask_email(email: str) -> str:
    """
    Mask email address for privacy.
    
    Args:
        email: Email address
    
    Returns:
        Masked email (e.g., j***@example.com)
    """
    if "@" not in email:
        return email
    
    local, domain = email.split("@")
    
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def is_valid_uuid(value: str) -> bool:
    """
    Check if string is valid UUID.
    
    Args:
        value: String to check
    
    Returns:
        True if valid UUID
    """
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def dict_to_camel_case(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert dictionary keys from snake_case to camelCase.
    
    Args:
        data: Dictionary with snake_case keys
    
    Returns:
        Dictionary with camelCase keys
    """
    def to_camel(snake_str: str) -> str:
        components = snake_str.split("_")
        return components[0] + "".join(x.title() for x in components[1:])
    
    return {to_camel(key): value for key, value in data.items()}


def remove_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove None values from dictionary.
    
    Args:
        data: Dictionary
    
    Returns:
        Dictionary without None values
    """
    return {key: value for key, value in data.items() if value is not None}


def calculate_percentage(part: float, total: float) -> float:
    """
    Calculate percentage.
    
    Args:
        part: Part value
        total: Total value
    
    Returns:
        Percentage (0-100)
    """
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


__all__ = [
    "generate_random_string",
    "generate_verification_token",
    "hash_string",
    "calculate_age_from_dob",
    "format_datetime",
    "parse_datetime",
    "get_time_ago",
    "paginate_list",
    "truncate_text",
    "mask_email",
    "is_valid_uuid",
    "dict_to_camel_case",
    "remove_none_values",
    "calculate_percentage",
]
