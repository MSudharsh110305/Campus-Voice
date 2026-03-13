"""
FastAPI dependencies for dependency injection.

Database sessions, authentication, authorization, pagination, validation, etc.

✅ UPDATED: Fixed import to use src.database.connection
✅ UPDATED: Added visibility checking, complaint validation, notification helpers
✅ UPDATED: Added proper service dependencies
✅ UPDATED: Enhanced filter classes with proper validation
"""

import logging
from typing import Optional, Generator, AsyncGenerator, Dict, Any, Tuple
from functools import wraps
from uuid import UUID
from datetime import datetime

from fastapi import Depends, HTTPException, status, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db as get_db_session  # ✅ FIXED IMPORT
from src.repositories.student_repo import StudentRepository
from src.repositories.authority_repo import AuthorityRepository
from src.services.auth_service import auth_service
from src.utils.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    AccountInactiveError,
    InsufficientPermissionsError,
    to_http_exception,
)

logger = logging.getLogger(__name__)

security = HTTPBearer()


# ==================== DATABASE ====================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
    
    Usage:
        @router.get("/")
        async def route(db: AsyncSession = Depends(get_db)):
            pass
    """
    async for session in get_db_session():
        yield session


# ==================== AUTHENTICATION ====================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
    
    Returns:
        User information dictionary
    
    Raises:
        HTTPException: If token is invalid or expired
    
    Usage:
        @router.get("/protected")
        async def route(user: Dict = Depends(get_current_user)):
            user_id = user["user_id"]
            role = user["role"]
    """
    try:
        token = credentials.credentials
        payload = auth_service.decode_token(token)

        if not payload:
            raise InvalidTokenError()

        # Reject refresh tokens used as access tokens
        token_type = payload.get("type", "access")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh tokens cannot be used for API access. Use your access token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "user_id": payload.get("sub"),
            "role": payload.get("role"),
            "payload": payload
        }

    except HTTPException:
        raise
    except (InvalidTokenError, TokenExpiredError) as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_student(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> str:
    """
    Dependency to get current student (requires Student role).
    
    Args:
        user: Current user from token
        db: Database session
    
    Returns:
        Student roll number
    
    Raises:
        HTTPException: If not a student or student not found
    
    Usage:
        @router.get("/student-only")
        async def route(roll_no: str = Depends(get_current_student)):
            pass
    """
    if user.get("role") != "Student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required"
        )
    
    roll_no = user.get("user_id")
    
    # Verify student exists and is active
    student_repo = StudentRepository(db)
    student = await student_repo.get(roll_no)
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    if not student.is_active:
        raise AccountInactiveError()
    
    return roll_no


async def get_current_authority(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> int:
    """
    Dependency to get current authority (requires Authority/Admin role).
    
    Args:
        user: Current user from token
        db: Database session
    
    Returns:
        Authority ID
    
    Raises:
        HTTPException: If not an authority or authority not found
    
    Usage:
        @router.get("/authority-only")
        async def route(authority_id: int = Depends(get_current_authority)):
            pass
    """
    if user.get("role") not in ["Authority", "Admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authority access required"
        )
    
    authority_id = int(user.get("user_id"))
    
    # Verify authority exists and is active
    authority_repo = AuthorityRepository(db)
    authority = await authority_repo.get(authority_id)
    
    if not authority:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority not found"
        )
    
    if not authority.is_active:
        raise AccountInactiveError()
    
    return authority_id


async def get_current_admin(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> int:
    """
    Dependency to get current admin (requires Admin role).
    
    Args:
        user: Current user from token
        db: Database session
    
    Returns:
        Admin ID
    
    Raises:
        HTTPException: If not an admin
    
    Usage:
        @router.get("/admin-only")
        async def route(admin_id: int = Depends(get_current_admin)):
            pass
    """
    if user.get("role") != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    authority_id = int(user.get("user_id"))
    
    # Verify admin exists
    authority_repo = AuthorityRepository(db)
    authority = await authority_repo.get(authority_id)
    
    if not authority or authority.authority_type != "Admin":
        raise InsufficientPermissionsError()
    
    return authority_id


# ==================== OPTIONAL AUTHENTICATION ====================

async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """
    Dependency to get current user if authenticated, None otherwise.
    Useful for routes that work differently for authenticated users.
    
    Args:
        request: FastAPI request
        db: Database session
    
    Returns:
        User info or None
    
    Usage:
        @router.get("/public-or-private")
        async def route(user: Optional[Dict] = Depends(get_optional_user)):
            if user:
                # Authenticated behavior
            else:
                # Public behavior
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        payload = auth_service.decode_token(token)
        
        if not payload:
            return None
        
        return {
            "user_id": payload.get("sub"),
            "role": payload.get("role"),
            "payload": payload
        }
        
    except Exception:
        return None


# ==================== PAGINATION ====================

class PaginationParams:
    """Pagination parameters for list endpoints."""
    
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(20, ge=1, le=100, description="Maximum records to return")
    ):
        self.skip = skip
        self.limit = limit
        self.page = (skip // limit) + 1
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "skip": self.skip,
            "limit": self.limit,
            "page": self.page
        }


def get_pagination(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return")
) -> PaginationParams:
    """
    Dependency to get pagination parameters.

    Returns:
        PaginationParams with skip, limit, page

    Usage:
        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends(get_pagination)):
            skip = pagination.skip
            limit = pagination.limit
    """
    return PaginationParams(skip=skip, limit=limit)


# ==================== QUERY FILTERS ====================

class ComplaintFilters:
    """Filter parameters for complaint queries."""
    
    def __init__(
        self,
        status: Optional[str] = Query(None, description="Filter by status (Raised, In Progress, Resolved, Closed)"),
        priority: Optional[str] = Query(None, description="Filter by priority (Low, Medium, High, Critical)"),
        category_id: Optional[int] = Query(None, description="Filter by category ID"),
        department_id: Optional[int] = Query(None, description="Filter by department ID"),
        date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
        date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
        has_image: Optional[bool] = Query(None, description="Filter by image presence"),
        is_verified: Optional[bool] = Query(None, description="Filter by image verification status")
    ):
        self.status = status
        self.priority = priority
        self.category_id = category_id
        self.department_id = department_id
        self.date_from = date_from
        self.date_to = date_to
        self.has_image = has_image
        self.is_verified = is_verified
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {
            k: v for k, v in {
                "status": self.status,
                "priority": self.priority,
                "category_id": self.category_id,
                "department_id": self.department_id,
                "date_from": self.date_from,
                "date_to": self.date_to,
                "has_image": self.has_image,
                "is_verified": self.is_verified
            }.items() if v is not None
        }


# ==================== ROLE-BASED ACCESS ====================

def require_roles(*allowed_roles: str):
    """
    Decorator to require specific roles for endpoint access.
    
    Args:
        *allowed_roles: Allowed role names
    
    Returns:
        Dependency function
    
    Usage:
        @router.get("/admin-or-authority")
        @require_roles("Admin", "Authority")
        async def route(user: Dict = Depends(get_current_user)):
            pass
    """
    def dependency(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = user.get("role")
        
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        
        return user
    
    return Depends(dependency)


# ==================== REQUEST CONTEXT ====================

async def get_request_context(
    request: Request,
    user: Optional[Dict] = Depends(get_optional_user)
) -> Dict[str, Any]:
    """
    Dependency to get request context information.
    
    Args:
        request: FastAPI request
        user: Optional current user
    
    Returns:
        Request context dictionary
    
    Usage:
        @router.post("/")
        async def route(context: Dict = Depends(get_request_context)):
            request_id = context["request_id"]
            user_id = context.get("user_id")
    """
    return {
        "request_id": getattr(request.state, "request_id", None),
        "user_id": user.get("user_id") if user else None,
        "role": user.get("role") if user else None,
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "path": request.url.path,
        "method": request.method
    }


# ==================== RATE LIMITING ====================

class RateLimitChecker:
    """Dependency class for rate limiting."""
    
    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        key_prefix: str = "rate_limit"
    ):
        """
        Initialize rate limit checker.
        
        Args:
            max_requests: Maximum requests in window
            window_seconds: Time window in seconds
            key_prefix: Prefix for rate limit key
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
    
    async def __call__(
        self,
        request: Request,
        user: Optional[Dict] = Depends(get_optional_user)
    ):
        """
        Check rate limit for current request.
        
        Args:
            request: FastAPI request
            user: Optional current user
        
        Raises:
            HTTPException: If rate limit exceeded
        """
        from src.utils.rate_limiter import rate_limiter
        
        # Determine rate limit key
        if user:
            key = f"{self.key_prefix}:{user['role']}:{user['user_id']}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            key = f"{self.key_prefix}:ip:{client_ip}"
        
        # Check rate limit
        try:
            await rate_limiter.enforce_rate_limit(
                key=key,
                max_requests=self.max_requests,
                window_seconds=self.window_seconds
            )
        except Exception as e:
            logger.warning(f"Rate limit exceeded for {key}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e)
            )


def rate_limit(max_requests: int, window_seconds: int, key_prefix: str = "api"):
    """
    Create rate limit dependency.
    
    Args:
        max_requests: Maximum requests in window
        window_seconds: Time window in seconds
        key_prefix: Prefix for rate limit key
    
    Returns:
        Rate limit dependency
    
    Usage:
        @router.post("/submit", dependencies=[Depends(rate_limit(5, 60))])
        async def submit():
            pass
    """
    return RateLimitChecker(max_requests, window_seconds, key_prefix)


# ==================== COMPLAINT VALIDATION & VISIBILITY ====================

async def get_complaint_with_ownership(
    complaint_id: UUID,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get complaint and validate ownership.
    
    Args:
        complaint_id: Complaint UUID
        roll_no: Student roll number
        db: Database session
    
    Returns:
        Complaint object
    
    Raises:
        HTTPException: If complaint not found or not owned by student
    
    Usage:
        @router.put("/complaints/{complaint_id}")
        async def update_complaint(
            complaint = Depends(get_complaint_with_ownership)
        ):
            # complaint is already validated
    """
    from src.repositories.complaint_repo import ComplaintRepository
    
    complaint_repo = ComplaintRepository(db)
    complaint = await complaint_repo.get(complaint_id)

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Soft-deleted complaints are invisible to students
    if getattr(complaint, 'is_deleted', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    if complaint.student_roll_no != roll_no:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this complaint"
        )

    return complaint


async def get_complaint_with_visibility(
    complaint_id: UUID,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get complaint and check visibility permissions.
    
    Args:
        complaint_id: Complaint UUID
        roll_no: Student roll number
        db: Database session
    
    Returns:
        Complaint object
    
    Raises:
        HTTPException: If complaint not found or not visible to user
    
    Usage:
        @router.get("/complaints/{complaint_id}")
        async def get_complaint(
            complaint = Depends(get_complaint_with_visibility)
        ):
            return complaint
    """
    from src.repositories.complaint_repo import ComplaintRepository
    from src.repositories.student_repo import StudentRepository
    
    complaint_repo = ComplaintRepository(db)
    student_repo = StudentRepository(db)
    
    complaint = await complaint_repo.get_with_relations(complaint_id)

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Soft-deleted complaints are invisible to students (even owners)
    if getattr(complaint, 'is_deleted', False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )

    # Get student info for visibility check
    student = await student_repo.get_with_department(roll_no)

    # Check visibility permissions
    can_view = await check_complaint_visibility(complaint, student)

    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this complaint"
        )

    return complaint


async def check_complaint_visibility(complaint, student) -> bool:
    """
    ✅ NEW: Check if student can view complaint based on visibility rules.
    
    Args:
        complaint: Complaint object
        student: Student object
    
    Returns:
        True if student can view complaint
    """
    # Owner can always view their own complaints
    if complaint.student_roll_no == student.roll_no:
        return True
    
    # Check visibility type
    visibility = complaint.visibility
    
    if visibility == "Public":
        return True
    
    elif visibility == "Department":
        # Only students from same department can view
        return complaint.student.department_id == student.department_id
    
    elif visibility == "Private":
        # Only owner can view
        return False
    
    # Default: allow access for public
    return True


async def get_authority_complaint(
    complaint_id: UUID,
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get complaint assigned to current authority.
    
    Args:
        complaint_id: Complaint UUID
        authority_id: Authority ID
        db: Database session
    
    Returns:
        Complaint object
    
    Raises:
        HTTPException: If complaint not found or not assigned to authority
    
    Usage:
        @router.put("/complaints/{complaint_id}/status")
        async def update_status(
            complaint = Depends(get_authority_complaint)
        ):
            # complaint is already validated
    """
    from src.repositories.complaint_repo import ComplaintRepository
    
    complaint_repo = ComplaintRepository(db)
    complaint = await complaint_repo.get_with_relations(complaint_id)
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    # Check if assigned to this authority (Admin can access any complaint)
    authority_repo = AuthorityRepository(db)
    authority = await authority_repo.get(authority_id)
    is_admin = authority and authority.authority_type == "Admin"

    if not is_admin and complaint.assigned_authority_id != authority_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This complaint is not assigned to you"
        )

    return complaint


# ==================== LEGACY VALIDATION (KEPT FOR BACKWARD COMPATIBILITY) ====================

async def validate_complaint_ownership(
    complaint_id: str,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    ⚠️ LEGACY: Use get_complaint_with_ownership() instead.
    
    Dependency to validate complaint ownership.
    
    Args:
        complaint_id: Complaint UUID
        roll_no: Student roll number
        db: Database session
    
    Raises:
        HTTPException: If complaint not found or not owned by student
    """
    from src.repositories.complaint_repo import ComplaintRepository
    
    complaint_repo = ComplaintRepository(db)
    complaint = await complaint_repo.get(UUID(complaint_id))
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    if complaint.student_roll_no != roll_no:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this complaint"
        )


# ==================== IMAGE ACCESS (any authenticated user) ====================

async def get_complaint_for_image(
    complaint_id: UUID,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Allow any authenticated user (student, authority, admin) to fetch a complaint image.
    No visibility check — image is accessible to anyone who knows the complaint ID and is logged in.
    """
    from src.repositories.complaint_repo import ComplaintRepository
    complaint_repo = ComplaintRepository(db)
    complaint = await complaint_repo.get(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    return complaint


# ==================== REPOSITORY DEPENDENCIES ====================

async def get_student_repo(db: AsyncSession = Depends(get_db)) -> StudentRepository:
    """Get student repository instance."""
    return StudentRepository(db)


async def get_authority_repo(db: AsyncSession = Depends(get_db)) -> AuthorityRepository:
    """Get authority repository instance."""
    return AuthorityRepository(db)


async def get_complaint_repo(db: AsyncSession = Depends(get_db)):
    """Get complaint repository instance."""
    from src.repositories.complaint_repo import ComplaintRepository
    return ComplaintRepository(db)


async def get_vote_repo(db: AsyncSession = Depends(get_db)):
    """✅ NEW: Get vote repository instance."""
    from src.repositories.vote_repo import VoteRepository
    return VoteRepository(db)


async def get_notification_repo(db: AsyncSession = Depends(get_db)):
    """✅ NEW: Get notification repository instance."""
    from src.repositories.notification_repo import NotificationRepository
    return NotificationRepository(db)


# ==================== SERVICE DEPENDENCIES ====================

async def get_complaint_service(db: AsyncSession = Depends(get_db)):
    """Get complaint service instance."""
    from src.services.complaint_service import ComplaintService
    return ComplaintService(db)


async def get_vote_service(db: AsyncSession = Depends(get_db)):
    """Get vote service instance."""
    from src.services.vote_service import VoteService
    return VoteService(db)


async def get_notification_service(db: AsyncSession = Depends(get_db)):
    """✅ NEW: Get notification service instance."""
    from src.services.notification_service import notification_service
    return notification_service


async def get_image_verification_service(db: AsyncSession = Depends(get_db)):
    """✅ NEW: Get image verification service instance."""
    from src.services.image_verification import image_verification_service
    return image_verification_service


async def get_authority_service(db: AsyncSession = Depends(get_db)):
    """✅ NEW: Get authority service instance."""
    from src.services.authority_service import authority_service
    return authority_service


async def get_authority_update_service(db: AsyncSession = Depends(get_db)):
    """✅ NEW: Get authority update service instance."""
    from src.services.authority_update_service import AuthorityUpdateService
    return AuthorityUpdateService(db)


# ==================== EXPORTS ====================

__all__ = [
    # Database
    "get_db",
    
    # Authentication
    "get_current_user",
    "get_current_student",
    "get_current_authority",
    "get_current_admin",
    "get_optional_user",
    
    # Pagination
    "PaginationParams",
    "get_pagination",
    
    # Filters
    "ComplaintFilters",
    
    # Authorization
    "require_roles",
    
    # Context
    "get_request_context",
    
    # Rate Limiting
    "rate_limit",
    "RateLimitChecker",
    
    # Complaint Validation & Visibility (NEW)
    "get_complaint_with_ownership",
    "get_complaint_with_visibility",
    "get_authority_complaint",
    "check_complaint_visibility",
    
    # Legacy Validation
    "validate_complaint_ownership",
    
    # Repositories
    "get_student_repo",
    "get_authority_repo",
    "get_complaint_repo",
    "get_vote_repo",
    "get_notification_repo",
    
    # Services
    "get_complaint_service",
    "get_vote_service",
    "get_notification_service",
    "get_image_verification_service",
    "get_authority_service",
    "get_authority_update_service",
]
