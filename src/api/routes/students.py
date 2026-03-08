"""
Student API endpoints.

Registration, login, profile management, statistics, notifications.

✅ FIXED: Import from src.database.connection instead of session
✅ ADDED: Notification endpoints (GET, PUT, unread count)
✅ ADDED: Proper count queries instead of fetching all records
✅ ENHANCED: Better error handling and logging
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_current_student, get_current_user  # ✅ FIXED IMPORT
from src.schemas.student import (
    StudentRegister,
    StudentLogin,
    StudentProfile,
    StudentProfileUpdate,
    StudentResponse,
    StudentStats,
    PasswordChange,
)
from src.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
)
from src.schemas.common import SuccessResponse, ErrorResponse
from src.repositories.student_repo import StudentRepository
from src.repositories.notification_repo import NotificationRepository
from src.services.auth_service import auth_service
from src.utils.exceptions import (
    InvalidCredentialsError,
    DuplicateEntryError,
    StudentNotFoundError,
    to_http_exception,
)
from src.utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/students", tags=["Students"])


# ==================== REGISTRATION ====================

@router.post(
    "/register",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new student",
    description="Register a new student account with email verification"
)
async def register_student(
    data: StudentRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new student account.
    
    - **roll_no**: Unique roll number
    - **name**: Full name
    - **email**: College email address
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit)
    - **gender**: Male, Female, or Other
    - **stay_type**: Hostel or Day Scholar
    - **year**: 1st Year, 2nd Year, 3rd Year, 4th Year
    - **department_id**: Department ID
    """
    try:
        student_repo = StudentRepository(db)
        
        # Check if email already exists
        existing_email = await student_repo.get_by_email(data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if roll number already exists
        existing_roll = await student_repo.get_by_roll_no(data.roll_no)
        if existing_roll:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Roll number already registered"
            )
        
        # Validate department exists
        from src.database.models import Department
        from sqlalchemy import select as sa_select
        dept_check = await db.execute(sa_select(Department).where(Department.id == data.department_id))
        if not dept_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department with id {data.department_id} does not exist"
            )

        # Hash password
        password_hash = auth_service.hash_password(data.password)

        # Create student
        student = await student_repo.create(
            roll_no=data.roll_no,
            name=data.name,
            email=data.email,
            password_hash=password_hash,
            gender=data.gender,
            stay_type=data.stay_type,
            year=data.year,
            department_id=data.department_id,
        )
        
        # Generate JWT access + refresh tokens
        token = auth_service.create_access_token(
            subject=student.roll_no,
            role="Student"
        )
        refresh_token = auth_service.create_refresh_token(
            subject=student.roll_no,
            role="Student"
        )

        logger.info(f"Student registered: {student.roll_no}")

        expires_in = int(auth_service._access_token_expiry("Student").total_seconds())

        return StudentResponse(
            roll_no=student.roll_no,
            name=student.name,
            email=student.email,
            gender=student.gender,
            stay_type=student.stay_type,
            year=student.year,
            department_id=student.department_id,
            token=token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=expires_in
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


# ==================== LOGIN ====================

@router.post(
    "/login",
    response_model=StudentResponse,
    summary="Student login",
    description="Login with email/roll number and password"
)
async def login_student(
    data: StudentLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login to student account.
    
    - **email_or_roll_no**: Email address or roll number
    - **password**: Account password
    """
    try:
        student_repo = StudentRepository(db)
        
        # Check if input is email or roll number
        if "@" in data.email_or_roll_no:
            student = await student_repo.get_by_email(data.email_or_roll_no)
        else:
            student = await student_repo.get_by_roll_no(data.email_or_roll_no)
        
        # Check if student exists
        if not student:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not auth_service.verify_password(data.password, student.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if account is active
        if not student.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Generate JWT access + refresh tokens
        token = auth_service.create_access_token(
            subject=student.roll_no,
            role="Student"
        )
        refresh_token = auth_service.create_refresh_token(
            subject=student.roll_no,
            role="Student"
        )

        logger.info(f"Student logged in: {student.roll_no}")

        expires_in = int(auth_service._access_token_expiry("Student").total_seconds())

        return StudentResponse(
            roll_no=student.roll_no,
            name=student.name,
            email=student.email,
            gender=student.gender,
            stay_type=student.stay_type,
            year=student.year,
            department_id=student.department_id,
            token=token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=expires_in
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


# ==================== PROFILE ====================

@router.get(
    "/profile",
    response_model=StudentProfile,
    summary="Get student profile",
    description="Get current student's profile information"
)
async def get_profile(
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get current student's profile."""
    student_repo = StudentRepository(db)
    
    student = await student_repo.get_with_department(roll_no)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    return StudentProfile(
        roll_no=student.roll_no,
        name=student.name,
        email=student.email,
        gender=student.gender,
        stay_type=student.stay_type,
        year=student.year,
        department_id=student.department_id,
        department_name=student.department.name if student.department else None,
        department_code=student.department.code if student.department else None,
        is_active=student.is_active,
        email_verified=student.email_verified,
        created_at=student.created_at
    )


@router.put(
    "/profile",
    response_model=StudentProfile,
    summary="Update student profile",
    description="Update student profile information"
)
async def update_profile(
    data: StudentProfileUpdate,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Update current student's profile."""
    student_repo = StudentRepository(db)
    
    # Build update dict (only include provided fields)
    update_data = data.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Update student
    student = await student_repo.update(roll_no, **update_data)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    logger.info(f"Profile updated: {roll_no}")
    
    # Return updated profile
    student = await student_repo.get_with_department(roll_no)
    return StudentProfile.model_validate(student)


# ==================== PASSWORD ====================

@router.post(
    "/change-password",
    response_model=SuccessResponse,
    summary="Change password",
    description="Change student account password"
)
async def change_password(
    data: PasswordChange,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Change student password."""
    student_repo = StudentRepository(db)
    
    student = await student_repo.get(roll_no)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Verify old password
    if not auth_service.verify_password(data.old_password, student.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )
    
    # Hash new password
    new_password_hash = auth_service.hash_password(data.new_password)
    
    # Update password
    await student_repo.update_password(roll_no, new_password_hash)
    
    logger.info(f"Password changed: {roll_no}")
    
    return SuccessResponse(
        success=True,
        message="Password changed successfully"
    )


# ==================== STATISTICS ====================

@router.get(
    "/stats",
    response_model=StudentStats,
    summary="Get student statistics",
    description="Get complaint statistics for current student"
)
async def get_student_stats(
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics for current student."""
    from src.repositories.complaint_repo import ComplaintRepository
    from src.repositories.vote_repo import VoteRepository
    
    complaint_repo = ComplaintRepository(db)
    vote_repo = VoteRepository(db)
    
    # ✅ FIXED: Use proper count queries instead of fetching all
    total_complaints = await complaint_repo.count_by_student(roll_no)
    raised = await complaint_repo.count_by_student(roll_no, status="Raised")
    in_progress = await complaint_repo.count_by_student(roll_no, status="In Progress")
    resolved = await complaint_repo.count_by_student(roll_no, status="Resolved")
    closed = await complaint_repo.count_by_student(roll_no, status="Closed")
    
    # Count spam complaints
    from sqlalchemy import select, func
    from src.database.models import Complaint
    
    spam_count_query = select(func.count()).where(
        Complaint.student_roll_no == roll_no,
        Complaint.is_marked_as_spam == True
    )
    spam_result = await db.execute(spam_count_query)
    spam = spam_result.scalar() or 0
    
    # Get votes cast count
    votes_count = await vote_repo.count_votes_by_student(roll_no)
    
    return StudentStats(
        total_complaints=total_complaints,
        raised=raised,
        in_progress=in_progress,
        resolved=resolved,
        closed=closed,
        spam=spam,
        total_votes_cast=votes_count
    )


# ==================== MY COMPLAINTS ====================

@router.get(
    "/my-complaints",
    summary="Get my complaints",
    description="Get all complaints submitted by current student"
)
async def get_my_complaints(
    roll_no: str = Depends(get_current_student),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db)
):
    """Get complaints submitted by current student."""
    from src.repositories.complaint_repo import ComplaintRepository
    from src.schemas.complaint import ComplaintListResponse, ComplaintResponse
    
    complaint_repo = ComplaintRepository(db)
    
    # Get paginated complaints
    complaints = await complaint_repo.get_by_student(
        roll_no,
        skip=skip,
        limit=limit,
        status=status_filter
    )
    
    # ✅ FIXED: Use count query instead of fetching all
    total = await complaint_repo.count_by_student(roll_no, status=status_filter)
    
    return ComplaintListResponse(
        complaints=[ComplaintResponse.model_validate(c) for c in complaints],
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit
    )


# ==================== NOTIFICATIONS (NEW) ====================

@router.get(
    "/notifications",
    response_model=NotificationListResponse,
    summary="Get notifications",
    description="Get all notifications for current student"
)
async def get_notifications(
    roll_no: str = Depends(get_current_student),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False, description="Show only unread notifications"),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get notifications for current student.
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum records to return
    - **unread_only**: If true, show only unread notifications
    """
    notification_repo = NotificationRepository(db)
    
    # Get notifications
    notifications = await notification_repo.get_by_recipient(
        recipient_type="Student",
        recipient_id=roll_no,
        skip=skip,
        limit=limit,
        unread_only=unread_only
    )
    
    # Get total count
    total = await notification_repo.count_by_recipient(
        recipient_type="Student",
        recipient_id=roll_no,
        unread_only=unread_only
    )
    
    # Get unread count
    unread_count = await notification_repo.count_unread(
        recipient_type="Student",
        recipient_id=roll_no
    )

    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count
    )


@router.put(
    "/notifications/{notification_id}/read",
    response_model=SuccessResponse,
    summary="Mark notification as read",
    description="Mark a specific notification as read"
)
async def mark_notification_read(
    notification_id: int,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Mark notification as read.
    
    - **notification_id**: Notification ID to mark as read
    """
    notification_repo = NotificationRepository(db)
    
    # Get notification
    notification = await notification_repo.get(notification_id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Check if notification belongs to current student
    if notification.recipient_id != roll_no or notification.recipient_type != "Student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this notification"
        )
    
    # Mark as read
    await notification_repo.mark_as_read(notification_id)
    
    logger.info(f"Notification {notification_id} marked as read by {roll_no}")
    
    return SuccessResponse(
        success=True,
        message="Notification marked as read"
    )


@router.put(
    "/notifications/mark-all-read",
    response_model=SuccessResponse,
    summary="Mark all notifications as read",
    description="Mark all notifications as read for current student"
)
async def mark_all_notifications_read(
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Mark all notifications as read for current student.
    """
    notification_repo = NotificationRepository(db)
    
    # Mark all as read
    count = await notification_repo.mark_all_as_read(
        recipient_type="Student",
        recipient_id=roll_no
    )
    
    logger.info(f"Marked {count} notifications as read for {roll_no}")
    
    return SuccessResponse(
        success=True,
        message=f"Marked {count} notifications as read"
    )


@router.get(
    "/notifications/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
    description="Get count of unread notifications for current student"
)
async def get_unread_count(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get unread notification count.

    Uses get_current_user (JWT-only, no DB lookup) instead of get_current_student
    to avoid opening an extra DB connection on this frequently-polled endpoint.
    BUG-019 fix: prevents connection pool exhaustion under concurrent polling.
    """
    if user.get("role") != "Student":
        raise HTTPException(status_code=403, detail="Student access required")
    roll_no = user.get("user_id")
    notification_repo = NotificationRepository(db)
    count = await notification_repo.count_unread(
        recipient_type="Student",
        recipient_id=roll_no
    )
    return UnreadCountResponse(
        unread_count=count
    )


@router.delete(
    "/notifications/{notification_id}",
    response_model=SuccessResponse,
    summary="Delete notification",
    description="Delete a specific notification"
)
async def delete_notification(
    notification_id: int,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Delete a notification.
    
    - **notification_id**: Notification ID to delete
    """
    notification_repo = NotificationRepository(db)
    
    # Get notification
    notification = await notification_repo.get(notification_id)
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Check if notification belongs to current student
    if notification.recipient_id != roll_no or notification.recipient_type != "Student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this notification"
        )
    
    # Delete notification
    await notification_repo.delete(notification_id)
    
    logger.info(f"Notification {notification_id} deleted by {roll_no}")
    
    return SuccessResponse(
        success=True,
        message="Notification deleted successfully"
    )


# ==================== NOTICE FEED ====================

@router.get(
    "/notices",
    summary="Get notices for current student",
    description=(
        "Returns active notices targeted at the current student based on their "
        "gender, stay type, department, and year. Notices with no targeting filter "
        "on a dimension are visible to all students for that dimension."
    )
)
async def get_student_notices(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Get notices targeted at the current student."""
    from src.database.models import AuthorityUpdate, Authority
    from sqlalchemy import select, func, and_, or_, text as sa_text
    from datetime import datetime, timezone
    from sqlalchemy.orm import selectinload

    student_repo = StudentRepository(db)
    student = await student_repo.get_with_department(roll_no)
    if not student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found")

    dept_code = student.department.code if student.department else None
    year_str = str(student.year)
    now = datetime.now(timezone.utc)

    # Base conditions: active and not expired
    base = and_(
        AuthorityUpdate.is_active == True,
        or_(
            AuthorityUpdate.expires_at == None,
            AuthorityUpdate.expires_at > now,
        )
    )

    # Build raw WHERE clause for array targeting using PostgreSQL syntax
    # Each dimension: null/empty array = show to all; otherwise check membership
    gender_clause = sa_text(
        "(:gender = ANY(target_gender) OR target_gender IS NULL "
        "OR array_length(target_gender, 1) IS NULL)"
    ).bindparams(gender=student.gender)

    stay_clause = sa_text(
        "(:stay = ANY(target_stay_types) OR target_stay_types IS NULL "
        "OR array_length(target_stay_types, 1) IS NULL)"
    ).bindparams(stay=student.stay_type)

    dept_clause = sa_text(
        "(:dept = ANY(target_departments) OR target_departments IS NULL "
        "OR array_length(target_departments, 1) IS NULL)"
    ).bindparams(dept=dept_code or "")

    year_clause = sa_text(
        "(:yr = ANY(target_years) OR target_years IS NULL "
        "OR array_length(target_years, 1) IS NULL)"
    ).bindparams(yr=year_str)

    total_q = (
        select(func.count())
        .select_from(AuthorityUpdate)
        .where(base)
        .where(gender_clause)
        .where(stay_clause)
        .where(dept_clause)
        .where(year_clause)
    )
    total_r = await db.execute(total_q)
    total = total_r.scalar() or 0

    notices_q = (
        select(AuthorityUpdate)
        .where(base)
        .where(gender_clause)
        .where(stay_clause)
        .where(dept_clause)
        .where(year_clause)
        .order_by(AuthorityUpdate.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    notices_r = await db.execute(notices_q)
    notices = notices_r.scalars().all()

    # Fetch authority info for each unique authority_id
    auth_ids = list({n.authority_id for n in notices})
    auth_map: dict = {}
    if auth_ids:
        auth_q = select(Authority).where(Authority.id.in_(auth_ids))
        auth_r = await db.execute(auth_q)
        for a in auth_r.scalars().all():
            auth_map[a.id] = a

    from src.schemas.authority import NoticeResponse, NoticeListResponse, NoticeAttachmentItem
    items = []
    for n in notices:
        auth = auth_map.get(n.authority_id)
        att_items = [
            NoticeAttachmentItem(id=a.id, filename=a.filename, mimetype=a.mimetype, size=a.size)
            for a in (n.attachments or [])
        ]
        items.append(NoticeResponse(
            id=n.id,
            authority_id=n.authority_id,
            authority_name=auth.name if auth else None,
            authority_type=auth.authority_type if auth else None,
            title=n.title,
            content=n.content,
            category=n.category,
            priority=n.priority,
            target_gender=n.target_gender,
            target_stay_types=n.target_stay_types,
            target_departments=n.target_departments,
            target_years=n.target_years,
            is_active=n.is_active,
            created_at=n.created_at,
            expires_at=n.expires_at,
            attachment_filename=n.attachment_filename,
            attachment_mimetype=n.attachment_mimetype if hasattr(n, 'attachment_mimetype') else None,
            attachments=att_items,
        ))

    return NoticeListResponse(
        notices=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit if total else 0,
    )


__all__ = ["router"]
