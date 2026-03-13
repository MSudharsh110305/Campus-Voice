"""
Utilities package initialization.
All helper utilities and functions.
"""

from .logger import setup_logger, log_with_context, app_logger
from .exceptions import (
    CampusVoiceException,
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
    InvalidTokenError,
    AuthorizationError,
    ValidationError,
    ResourceNotFoundError,
    StudentNotFoundError,
    ComplaintNotFoundError,
    AuthorityNotFoundError,
    SpamDetectedError,
    RateLimitExceededError,
    InvalidStatusTransitionError,
    DuplicateVoteError,
    FileUploadError,
    InvalidFileTypeError,
    FileTooLargeError,
    to_http_exception,
)

# Robust import of JWT utilities (some projects expose different names)
try:
    from .jwt_utils import (
        get_current_user,
        get_current_student,
        get_current_authority,
        extract_token_from_header,
        verify_token_role,
        security,
    )
except Exception:
    def _missing(name: str):
        def _fn(*args, **kwargs):
            raise ImportError(f"'{name}' is not available in src.utils.jwt_utils. "
                              "Ensure jwt_utils exports this symbol.")
        return _fn

    # placeholders to fail with helpful message if called
    get_current_user = _missing("get_current_user")
    get_current_student = _missing("get_current_student")
    get_current_authority = _missing("get_current_authority")
    extract_token_from_header = _missing("extract_token_from_header")
    verify_token_role = _missing("verify_token_role")
    security = None

from .rate_limiter import RateLimiter, rate_limiter
from .validators import (
    validate_email,
    validate_roll_no,
    validate_phone,
    validate_complaint_text,
    validate_file_extension,
    sanitize_text,
    validate_status_transition,
)
from .file_upload import FileUploadHandler, file_upload_handler
from .helpers import (
    generate_random_string,
    generate_verification_token,
    hash_string,
    get_time_ago,
    paginate_list,
    truncate_text,
    mask_email,
    is_valid_uuid,
)

__all__ = [
    # Logger
    "setup_logger",
    "log_with_context",
    "app_logger",
    
    # Exceptions
    "CampusVoiceException",
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "InvalidTokenError",
    "AuthorizationError",
    "ValidationError",
    "ResourceNotFoundError",
    "StudentNotFoundError",
    "ComplaintNotFoundError",
    "AuthorityNotFoundError",
    "SpamDetectedError",
    "RateLimitExceededError",
    "InvalidStatusTransitionError",
    "DuplicateVoteError",
    "FileUploadError",
    "InvalidFileTypeError",
    "FileTooLargeError",
    "to_http_exception",
    
    # JWT Utils (may be placeholders if jwt_utils missing symbols)
    "get_current_user",
    "get_current_student",
    "get_current_authority",
    "extract_token_from_header",
    "verify_token_role",
    "security",
    
    # Rate Limiter
    "RateLimiter",
    "rate_limiter",
    
    # Validators
    "validate_email",
    "validate_roll_no",
    "validate_phone",
    "validate_complaint_text",
    "validate_file_extension",
    "sanitize_text",
    "validate_status_transition",
    
    # File Upload
    "FileUploadHandler",
    "file_upload_handler",
    
    # Helpers
    "generate_random_string",
    "generate_verification_token",
    "hash_string",
    "get_time_ago",
    "paginate_list",
    "truncate_text",
    "mask_email",
    "is_valid_uuid",
]
