"""
Custom validators for data validation.
"""

import re
from typing import Optional
from src.config.constants import (
    EMAIL_PATTERN,
    ROLL_NO_PATTERN,
    PHONE_PATTERN,
    MIN_COMPLAINT_LENGTH,
    MAX_COMPLAINT_LENGTH
)


def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email format.
    
    Args:
        email: Email address
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    if not EMAIL_PATTERN.match(email):
        return False, "Invalid email format"
    
    return True, None


def validate_roll_no(roll_no: str) -> tuple[bool, Optional[str]]:
    """
    Validate roll number format.
    
    Args:
        roll_no: Roll number
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not roll_no:
        return False, "Roll number is required"
    
    if not ROLL_NO_PATTERN.match(roll_no):
        return False, "Invalid roll number format"
    
    return True, None


def validate_phone(phone: str) -> tuple[bool, Optional[str]]:
    """
    Validate phone number format (Indian).
    
    Args:
        phone: Phone number
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    if not PHONE_PATTERN.match(phone):
        return False, "Invalid phone number format (must be 10 digits starting with 6-9)"
    
    return True, None


def validate_complaint_text(text: str) -> tuple[bool, Optional[str]]:
    """
    Validate complaint text.
    
    Args:
        text: Complaint text
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text:
        return False, "Complaint text is required"
    
    text = text.strip()
    
    if len(text) < MIN_COMPLAINT_LENGTH:
        return False, f"Complaint must be at least {MIN_COMPLAINT_LENGTH} characters"
    
    if len(text) > MAX_COMPLAINT_LENGTH:
        return False, f"Complaint must not exceed {MAX_COMPLAINT_LENGTH} characters"
    
    # Check for all caps (potential spam)
    if text.isupper() and len(text) > 50:
        return False, "Please avoid writing in all caps"
    
    # Check for minimum word count
    words = text.split()
    if len(words) < 3:
        return False, "Complaint must contain at least 3 words"
    
    return True, None


def validate_file_extension(filename: str, allowed_extensions: list) -> tuple[bool, Optional[str]]:
    """
    Validate file extension.
    
    Args:
        filename: File name
        allowed_extensions: List of allowed extensions
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "Filename is required"
    
    if "." not in filename:
        return False, "File must have an extension"
    
    ext = filename.rsplit(".", 1)[1].lower()
    
    if ext not in allowed_extensions:
        return False, f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
    
    return True, None


def sanitize_text(text: str) -> str:
    """
    Sanitize text input (remove dangerous characters).
    
    Args:
        text: Text to sanitize
    
    Returns:
        Sanitized text
    """
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Remove excessive whitespace
    text = " ".join(text.split())
    
    # Remove control characters except newlines and tabs
    text = "".join(char for char in text if ord(char) >= 32 or char in ["\n", "\t"])
    
    return text.strip()


def validate_status_transition(old_status: str, new_status: str) -> tuple[bool, Optional[str]]:
    """
    Validate complaint status transition.
    
    Args:
        old_status: Current status
        new_status: New status
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    from src.config.constants import VALID_STATUS_TRANSITIONS
    
    allowed_transitions = VALID_STATUS_TRANSITIONS.get(old_status, [])
    
    if new_status not in allowed_transitions:
        return False, f"Cannot transition from '{old_status}' to '{new_status}'"
    
    return True, None


def validate_priority(priority: str) -> tuple[bool, Optional[str]]:
    """
    Validate priority level.
    
    Args:
        priority: Priority level
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_priorities = ["Low", "Medium", "High", "Critical"]
    
    if priority not in valid_priorities:
        return False, f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"
    
    return True, None


def validate_visibility(visibility: str) -> tuple[bool, Optional[str]]:
    """
    Validate visibility level.
    
    Args:
        visibility: Visibility level
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_visibility = ["Private", "Department", "Public"]
    
    if visibility not in valid_visibility:
        return False, f"Invalid visibility. Must be one of: {', '.join(valid_visibility)}"
    
    return True, None


__all__ = [
    "validate_email",
    "validate_roll_no",
    "validate_phone",
    "validate_complaint_text",
    "validate_file_extension",
    "sanitize_text",
    "validate_status_transition",
    "validate_priority",
    "validate_visibility",
]
