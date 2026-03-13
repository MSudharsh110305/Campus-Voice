"""
Custom exception classes for CampusVoice application.
"""

from typing import Optional, Any, Dict
from fastapi import HTTPException, status


class CampusVoiceException(Exception):
    """Base exception for CampusVoice application"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


# ==================== AUTHENTICATION EXCEPTIONS ====================

class AuthenticationError(CampusVoiceException):
    """Authentication failed"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        if "error_code" not in kwargs:
            kwargs["error_code"] = "AUTH_ERROR"
        super().__init__(message, **kwargs)


class InvalidCredentialsError(AuthenticationError):
    """Invalid email or password"""
    
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message, error_code="INVALID_CREDENTIALS")


class TokenExpiredError(AuthenticationError):
    """JWT token expired"""
    
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, error_code="TOKEN_EXPIRED")


class InvalidTokenError(AuthenticationError):
    """Invalid JWT token"""
    
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, error_code="INVALID_TOKEN")


class AccountInactiveError(AuthenticationError):
    """Account is inactive"""
    
    def __init__(self, message: str = "Account is inactive"):
        super().__init__(message, error_code="ACCOUNT_INACTIVE")


# ==================== AUTHORIZATION EXCEPTIONS ====================

class AuthorizationError(CampusVoiceException):
    """Authorization/permission error"""
    
    def __init__(self, message: str = "Unauthorized access", **kwargs):
        if "error_code" not in kwargs:
            kwargs["error_code"] = "UNAUTHORIZED"
        super().__init__(message, **kwargs)


class InsufficientPermissionsError(AuthorizationError):
    """Insufficient permissions"""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, error_code="INSUFFICIENT_PERMISSIONS")


# ==================== VALIDATION EXCEPTIONS ====================

class ValidationError(CampusVoiceException):
    """Data validation error"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        kwargs["details"] = details
        if "error_code" not in kwargs:
            kwargs["error_code"] = "VALIDATION_ERROR"
        super().__init__(message, **kwargs)


class InvalidInputError(ValidationError):
    """Invalid input data"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, field=field)


class DuplicateEntryError(ValidationError):
    """Duplicate entry in database"""
    
    def __init__(self, message: str = "Duplicate entry", field: Optional[str] = None):
        super().__init__(message, field=field, error_code="DUPLICATE_ENTRY")


# ==================== RESOURCE EXCEPTIONS ====================

class ResourceNotFoundError(CampusVoiceException):
    """Resource not found"""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Any,
        message: Optional[str] = None
    ):
        if not message:
            message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(
            message,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": str(resource_id)}
        )


class StudentNotFoundError(ResourceNotFoundError):
    """Student not found"""
    
    def __init__(self, roll_no: str):
        super().__init__("Student", roll_no)


class ComplaintNotFoundError(ResourceNotFoundError):
    """Complaint not found"""
    
    def __init__(self, complaint_id: str):
        super().__init__("Complaint", complaint_id)


class AuthorityNotFoundError(ResourceNotFoundError):
    """Authority not found"""
    
    def __init__(self, authority_id: int):
        super().__init__("Authority", authority_id)


# ==================== BUSINESS LOGIC EXCEPTIONS ====================

class BusinessLogicError(CampusVoiceException):
    """Business logic violation"""
    
    def __init__(self, message: str, **kwargs):
        if "error_code" not in kwargs:
            kwargs["error_code"] = "BUSINESS_LOGIC_ERROR"
        super().__init__(message, **kwargs)


class SpamDetectedError(BusinessLogicError):
    """Complaint flagged as spam"""
    
    def __init__(self, reason: str = "Complaint flagged as spam"):
        super().__init__(reason, error_code="SPAM_DETECTED")


class BlacklistedError(BusinessLogicError):
    """User is blacklisted"""
    
    def __init__(self, reason: str = "Account temporarily suspended"):
        super().__init__(reason, error_code="BLACKLISTED")


class RateLimitExceededError(BusinessLogicError):
    """Rate limit exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded. Please try again later"):
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED")


class InvalidStatusTransitionError(BusinessLogicError):
    """Invalid complaint status transition"""
    
    def __init__(self, old_status: str, new_status: str):
        message = f"Cannot transition from '{old_status}' to '{new_status}'"
        super().__init__(
            message,
            error_code="INVALID_STATUS_TRANSITION",
            details={"old_status": old_status, "new_status": new_status}
        )


class DuplicateVoteError(BusinessLogicError):
    """User already voted"""
    
    def __init__(self, message: str = "You have already voted on this complaint"):
        super().__init__(message, error_code="DUPLICATE_VOTE")


# ==================== FILE UPLOAD EXCEPTIONS ====================

class FileUploadError(CampusVoiceException):
    """File upload error"""
    
    def __init__(self, message: str, **kwargs):
        if "error_code" not in kwargs:
            kwargs["error_code"] = "FILE_UPLOAD_ERROR"
        super().__init__(message, **kwargs)


class InvalidFileTypeError(FileUploadError):
    """Invalid file type"""
    
    def __init__(self, allowed_types: list):
        message = f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        super().__init__(message, error_code="INVALID_FILE_TYPE")


class FileTooLargeError(FileUploadError):
    """File size exceeds limit"""
    
    def __init__(self, max_size: int):
        message = f"File size exceeds maximum limit of {max_size} bytes"
        super().__init__(message, error_code="FILE_TOO_LARGE")


# ==================== EXTERNAL SERVICE EXCEPTIONS ====================

class ExternalServiceError(CampusVoiceException):
    """External service error"""
    
    def __init__(self, service: str, message: str, **kwargs):
        details = kwargs.get("details", {})
        details["service"] = service
        kwargs["details"] = details
        if "error_code" not in kwargs:
            kwargs["error_code"] = "EXTERNAL_SERVICE_ERROR"
        super().__init__(f"{service} error: {message}", **kwargs)


class LLMServiceError(ExternalServiceError):
    """LLM service error"""
    
    def __init__(self, message: str = "LLM service unavailable"):
        super().__init__("LLM", message)


class DatabaseError(ExternalServiceError):
    """Database error"""
    
    def __init__(self, message: str = "Database error occurred"):
        super().__init__("Database", message)


# ==================== HTTP EXCEPTION CONVERTER ====================

def to_http_exception(exc: CampusVoiceException) -> HTTPException:
    """
    Convert CampusVoiceException to FastAPI HTTPException.
    
    Args:
        exc: CampusVoiceException instance
    
    Returns:
        HTTPException with appropriate status code
    """
    status_code_map = {
        "AUTH_ERROR": status.HTTP_401_UNAUTHORIZED,
        "INVALID_CREDENTIALS": status.HTTP_401_UNAUTHORIZED,
        "TOKEN_EXPIRED": status.HTTP_401_UNAUTHORIZED,
        "INVALID_TOKEN": status.HTTP_401_UNAUTHORIZED,
        "ACCOUNT_INACTIVE": status.HTTP_403_FORBIDDEN,
        "UNAUTHORIZED": status.HTTP_403_FORBIDDEN,
        "INSUFFICIENT_PERMISSIONS": status.HTTP_403_FORBIDDEN,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "DUPLICATE_ENTRY": status.HTTP_409_CONFLICT,
        "RESOURCE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "SPAM_DETECTED": status.HTTP_400_BAD_REQUEST,
        "BLACKLISTED": status.HTTP_403_FORBIDDEN,
        "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
        "INVALID_STATUS_TRANSITION": status.HTTP_400_BAD_REQUEST,
        "DUPLICATE_VOTE": status.HTTP_409_CONFLICT,
        "FILE_UPLOAD_ERROR": status.HTTP_400_BAD_REQUEST,
        "INVALID_FILE_TYPE": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        "FILE_TOO_LARGE": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        "EXTERNAL_SERVICE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
    }
    
    status_code = status_code_map.get(
        exc.error_code,
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    
    return HTTPException(
        status_code=status_code,
        detail={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )


__all__ = [
    "CampusVoiceException",
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "InvalidTokenError",
    "AccountInactiveError",
    "AuthorizationError",
    "InsufficientPermissionsError",
    "ValidationError",
    "InvalidInputError",
    "DuplicateEntryError",
    "ResourceNotFoundError",
    "StudentNotFoundError",
    "ComplaintNotFoundError",
    "AuthorityNotFoundError",
    "BusinessLogicError",
    "SpamDetectedError",
    "BlacklistedError",
    "RateLimitExceededError",
    "InvalidStatusTransitionError",
    "DuplicateVoteError",
    "FileUploadError",
    "InvalidFileTypeError",
    "FileTooLargeError",
    "ExternalServiceError",
    "LLMServiceError",
    "DatabaseError",
    "to_http_exception",
]
