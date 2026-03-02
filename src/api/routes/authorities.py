"""
Authority API endpoints.

Login, dashboard, complaint management, status updates, escalation.

✅ FIXED: Import from src.database.connection
✅ FIXED: Import from src.api.dependencies
✅ ADDED: Authority update posting endpoints
✅ ADDED: Escalation endpoints
✅ ADDED: Proper count queries
✅ ADDED: Notification integration
✅ FIXED: Status update with notification creation
"""

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (  # ✅ FIXED IMPORT - use dependencies.get_db for session sharing
    get_db,
    get_current_authority,
    get_authority_complaint,
)
from src.schemas.authority import (
    AuthorityLogin,
    AuthorityProfile,
    AuthorityResponse,
    AuthorityStats,
    AuthorityDashboard,
    AuthorityUpdateCreate,
    AuthorityUpdateResponse,
    NoticeCreate,
    NoticeResponse,
    NoticeListResponse,
)
from src.schemas.complaint import (
    ComplaintUpdate,
    ComplaintListResponse,
    ComplaintResponse,
)
from src.schemas.common import SuccessResponse
from src.repositories.authority_repo import AuthorityRepository
from src.repositories.complaint_repo import ComplaintRepository
from src.repositories.authority_update_repo import AuthorityUpdateRepository
from src.services.auth_service import auth_service
from src.services.complaint_service import ComplaintService
from src.services.notification_service import notification_service
from src.utils.exceptions import (
    InvalidCredentialsError,
    AuthorityNotFoundError,
    to_http_exception,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/authorities", tags=["Authorities"])


# ==================== LOGIN ====================

@router.post(
    "/login",
    response_model=AuthorityResponse,
    summary="Authority login",
    description="Login for authority/admin users"
)
async def login_authority(
    data: AuthorityLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login to authority account.
    
    - **email**: Authority email address
    - **password**: Account password
    """
    try:
        authority_repo = AuthorityRepository(db)
        
        authority = await authority_repo.get_by_email(data.email)
        
        if not authority:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not auth_service.verify_password(data.password, authority.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if account is active
        if not authority.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Generate JWT token (use "Admin" role if authority_type is Admin)
        role = "Admin" if authority.authority_type == "Admin" else "Authority"
        
        token = auth_service.create_access_token(
            subject=str(authority.id),
            role=role
        )
        
        logger.info(f"Authority logged in: {authority.email}")
        
        return AuthorityResponse(
            id=authority.id,
            name=authority.name,
            email=authority.email,
            authority_type=authority.authority_type,
            department_id=authority.department_id,
            token=token,
            token_type="Bearer",
            expires_in=auth_service.get_token_expiration_seconds()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authority login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


# ==================== PROFILE & DASHBOARD ====================

@router.get(
    "/profile",
    response_model=AuthorityProfile,
    summary="Get authority profile",
    description="Get current authority's profile"
)
async def get_authority_profile(
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """Get current authority's profile."""
    authority_repo = AuthorityRepository(db)
    
    authority = await authority_repo.get_with_department(authority_id)
    if not authority:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority not found"
        )
    
    return AuthorityProfile.model_validate(authority)


@router.get(
    "/dashboard",
    response_model=AuthorityDashboard,
    summary="Get authority dashboard",
    description="Get dashboard data with stats and recent complaints"
)
async def get_authority_dashboard(
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """Get authority dashboard with statistics and recent complaints."""
    authority_repo = AuthorityRepository(db)
    complaint_repo = ComplaintRepository(db)
    
    # Get profile
    authority = await authority_repo.get_with_department(authority_id)
    if not authority:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority not found"
        )
    
    # ✅ FIXED: Use count queries instead of fetching all
    from sqlalchemy import select, func, and_
    from src.database.models import Complaint
    
    # Total assigned
    total_query = select(func.count()).where(
        Complaint.assigned_authority_id == authority_id
    )
    total_result = await db.execute(total_query)
    total_assigned = total_result.scalar() or 0
    
    # By status
    pending_query = select(func.count()).where(
        and_(
            Complaint.assigned_authority_id == authority_id,
            Complaint.status == "Raised"
        )
    )
    pending_result = await db.execute(pending_query)
    pending = pending_result.scalar() or 0
    
    in_progress_query = select(func.count()).where(
        and_(
            Complaint.assigned_authority_id == authority_id,
            Complaint.status == "In Progress"
        )
    )
    in_progress_result = await db.execute(in_progress_query)
    in_progress = in_progress_result.scalar() or 0
    
    resolved_query = select(func.count()).where(
        and_(
            Complaint.assigned_authority_id == authority_id,
            Complaint.status == "Resolved"
        )
    )
    resolved_result = await db.execute(resolved_query)
    resolved = resolved_result.scalar() or 0
    
    closed_query = select(func.count()).where(
        and_(
            Complaint.assigned_authority_id == authority_id,
            Complaint.status == "Closed"
        )
    )
    closed_result = await db.execute(closed_query)
    closed = closed_result.scalar() or 0
    
    spam_query = select(func.count()).where(
        and_(
            Complaint.assigned_authority_id == authority_id,
            Complaint.is_marked_as_spam == True
        )
    )
    spam_result = await db.execute(spam_query)
    spam_flagged = spam_result.scalar() or 0
    
    stats = {
        "total_assigned": total_assigned,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved,
        "closed": closed,
        "spam_flagged": spam_flagged,
        "avg_resolution_time_hours": None,  # TODO: Calculate from resolved complaints
        "performance_rating": None,
    }
    
    # Get recent complaints
    recent = await complaint_repo.get_assigned_to_authority(authority_id, skip=0, limit=10)
    
    # Get urgent complaints
    urgent_query = (
        select(Complaint)
        .where(
            and_(
                Complaint.assigned_authority_id == authority_id,
                Complaint.priority.in_(["High", "Critical"]),
                Complaint.status.in_(["Raised", "In Progress"])
            )
        )
        .order_by(Complaint.priority_score.desc())
        .limit(10)
    )
    urgent_result = await db.execute(urgent_query)
    urgent = urgent_result.scalars().all()
    
    # Get unread notification count
    from src.repositories.notification_repo import NotificationRepository
    notification_repo = NotificationRepository(db)
    unread_count = await notification_repo.count_unread(
        recipient_type="Authority",
        recipient_id=str(authority_id)
    )
    
    return AuthorityDashboard(
        profile=AuthorityProfile.model_validate(authority),
        stats=AuthorityStats(**stats),
        recent_complaints=[ComplaintResponse.model_validate(c).model_dump() for c in recent],
        urgent_complaints=[ComplaintResponse.model_validate(c).model_dump() for c in urgent],
        unread_notifications=unread_count
    )


# ==================== COMPLAINT MANAGEMENT ====================

@router.get(
    "/my-complaints",
    response_model=ComplaintListResponse,
    summary="Get assigned complaints",
    description="Get all complaints assigned to current authority (with partial anonymity)"
)
async def get_assigned_complaints(
    authority_id: int = Depends(get_current_authority),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ UPDATED: Get complaints assigned to current authority with partial anonymity.

    **Partial Anonymity Rules**:
    - Non-spam complaints: Student information is hidden
    - Spam complaints: Student information is revealed to help identify repeat offenders
    """
    complaint_repo = ComplaintRepository(db)
    authority_repo = AuthorityRepository(db)

    # Check if authority is admin
    authority = await authority_repo.get(authority_id)
    is_admin = authority and authority.authority_type == "Admin"

    complaints = await complaint_repo.get_assigned_to_authority(
        authority_id,
        skip=skip,
        limit=limit,
        status=status_filter
    )

    # ✅ FIXED: Use count query
    from sqlalchemy import select, func, and_
    from src.database.models import Complaint

    conditions = [Complaint.assigned_authority_id == authority_id]
    if status_filter:
        conditions.append(Complaint.status == status_filter)

    count_query = select(func.count()).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # ✅ NEW: Apply partial anonymity to complaint list
    complaint_responses = []
    for complaint in complaints:
        response_dict = ComplaintResponse.model_validate(complaint).model_dump()

        # Apply partial anonymity
        if is_admin:
            # Admin sees all student info
            response_dict["student_roll_no"] = complaint.student_roll_no
            response_dict["student_name"] = complaint.student.name if complaint.student else None
        elif complaint.is_marked_as_spam:
            # Authority sees student info for spam complaints
            response_dict["student_roll_no"] = complaint.student_roll_no
            response_dict["student_name"] = complaint.student.name if complaint.student else None
        else:
            # Non-spam: Hide student info from authorities
            response_dict["student_roll_no"] = None
            response_dict["student_name"] = None

        complaint_responses.append(ComplaintResponse(**response_dict))

    return ComplaintListResponse(
        complaints=complaint_responses,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit
    )


@router.get(
    "/complaints/{complaint_id}",
    summary="Get complaint details",
    description="Get detailed complaint information with partial anonymity"
)
async def get_complaint_details_for_authority(
    complaint_id: UUID,
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get detailed complaint with partial anonymity enforcement.

    **Partial Anonymity Rules**:
    - Admin: Can view all student information
    - Authority (non-spam): Student information is hidden
    - Authority (spam): Student information is revealed
    """
    try:
        authority_repo = AuthorityRepository(db)
        authority = await authority_repo.get(authority_id)

        if not authority:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Authority not found"
            )

        is_admin = authority.authority_type == "Admin"

        service = ComplaintService(db)
        complaint_data = await service.get_complaint_for_authority(
            complaint_id=complaint_id,
            authority_id=authority_id,
            is_admin=is_admin
        )

        return complaint_data

    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error fetching complaint {complaint_id} for authority {authority_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch complaint details"
        )


@router.put(
    "/complaints/{complaint_id}/status",
    response_model=SuccessResponse,
    summary="Update complaint status",
    description="Update status of assigned complaint"
)
async def update_complaint_status(
    complaint_id: UUID,
    data: ComplaintUpdate,
    complaint = Depends(get_authority_complaint),  # ✅ Validates assignment
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """
    Update complaint status.

    - **status**: New status (Raised, In Progress, Resolved, Closed)
    - **reason**: Optional reason for status change

    Automatically creates notification for student.
    """
    try:
        # ✅ NEW: Validate status transition
        from src.config.constants import VALID_STATUS_TRANSITIONS

        current_status = complaint.status
        new_status = data.status

        # Check if transition is valid
        if new_status not in VALID_STATUS_TRANSITIONS.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {current_status} to {new_status}"
            )

        # ✅ NEW: Check if reason is required for certain status changes
        if new_status in ("Closed", "Spam") and (not data.reason or not data.reason.strip()):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Reason is required when changing status to {new_status}"
            )

        service = ComplaintService(db)

        # Update status
        await service.update_complaint_status(
            complaint_id=complaint_id,
            new_status=data.status,
            authority_id=authority_id,
            reason=data.reason
        )
        
        logger.info(f"Complaint {complaint_id} status updated to {data.status} by authority {authority_id}")
        
        return SuccessResponse(
            success=True,
            message=f"Complaint status updated to '{data.status}'"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status update error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== AUTHORITY UPDATES (PUBLIC FEED) ====================

@router.post(
    "/complaints/{complaint_id}/post-update",
    response_model=SuccessResponse,
    summary="Post public update",
    description="Post status update visible in public feed"
)
async def post_public_update(
    complaint_id: UUID,
    title: str = Query(..., description="Update title"),
    content: str = Query(..., description="Update content"),
    complaint = Depends(get_authority_complaint),
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Post public update about complaint progress.
    
    Updates are visible in public feed and sent as notifications.
    
    Example: "Working on fixing AC, technician assigned"
    """
    try:
        from src.database.models import StatusUpdate
        
        # Create status update entry
        status_update = StatusUpdate(
            complaint_id=complaint_id,
            updated_by=authority_id,
            old_status=complaint.status,
            new_status=complaint.status,  # Same status, just an update
            reason=f"{title}: {content}"
        )
        
        db.add(status_update)
        
        # Update complaint timestamp
        complaint.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        # ✅ Create notification for student
        await notification_service.create_notification(
            db=db,
            recipient_type="Student",
            recipient_id=complaint.student_roll_no,
            complaint_id=complaint_id,
            notification_type="complaint_update",
            message=f"Update on your complaint: {title}"
        )
        
        logger.info(f"Public update posted for complaint {complaint_id} by authority {authority_id}")
        
        return SuccessResponse(
            success=True,
            message="Update posted successfully"
        )
        
    except Exception as e:
        logger.error(f"Post update error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to post update"
        )


# ==================== ESCALATION ====================

@router.post(
    "/complaints/{complaint_id}/escalate",
    response_model=SuccessResponse,
    summary="Escalate complaint",
    description="Escalate complaint to higher authority level"
)
async def escalate_complaint(
    complaint_id: UUID,
    reason: str = Query(..., description="Reason for escalation"),
    complaint = Depends(get_authority_complaint),
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Escalate complaint to next authority level.
    
    - **reason**: Reason for escalation
    
    Finds higher-level authority and reassigns complaint.
    """
    try:
        from src.services.authority_service import authority_service
        from src.database.models import StatusUpdate
        
        # Get current authority level
        authority_repo = AuthorityRepository(db)
        current_authority = await authority_repo.get(authority_id)
        
        if not current_authority:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Authority not found"
            )
        
        # Find next level authority using actual authority type (not level-based lookup)
        next_authority = await authority_service.get_escalated_authority(
            db=db,
            current_authority_id=authority_id
        )
        
        if not next_authority:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No higher authority available for escalation"
            )
        
        # Store original authority if not already stored
        if not complaint.original_assigned_authority_id:
            complaint.original_assigned_authority_id = authority_id
        
        # Reassign complaint
        old_authority_id = complaint.assigned_authority_id
        complaint.assigned_authority_id = next_authority.id
        complaint.assigned_at = datetime.now(timezone.utc)
        complaint.updated_at = datetime.now(timezone.utc)

        # Create status update
        status_update = StatusUpdate(
            complaint_id=complaint_id,
            updated_by=authority_id,
            old_status=complaint.status,
            new_status=complaint.status,
            reason=f"Escalated to {next_authority.name}: {reason}"
        )

        # Explicitly mark complaint as dirty and flush to ensure persistence
        db.add(complaint)
        db.add(status_update)
        await db.flush()
        await db.commit()
        
        # Bug 6 fix: Notify both student and NEW authority on escalation.
        # Notify student
        await notification_service.create_notification(
            db=db,
            recipient_type="Student",
            recipient_id=complaint.student_roll_no,
            complaint_id=complaint_id,
            notification_type="complaint_escalated",
            message=f"Your complaint has been escalated to {next_authority.name}"
        )

        # Bug 6 fix: Notify NEW authority with correct type "escalation" and
        # include the previous authority's name in the message.
        await notification_service.create_notification(
            db=db,
            recipient_type="Authority",
            recipient_id=str(next_authority.id),
            complaint_id=complaint_id,
            notification_type="escalation",
            message=(
                f"Complaint escalated to you from {current_authority.name}. "
                f"Category: {complaint.category.name if complaint.category else 'Unknown'}. "
                f"Issue: {(complaint.rephrased_text or complaint.original_text)[:80]}..."
            )
        )
        
        logger.info(
            f"Complaint {complaint_id} escalated from authority {old_authority_id} "
            f"to {next_authority.id} (level {next_authority.authority_level})"
        )
        
        return SuccessResponse(
            success=True,
            message=f"Complaint escalated to {next_authority.name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Escalation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to escalate complaint"
        )


@router.get(
    "/complaints/{complaint_id}/escalation-history",
    summary="Get escalation history",
    description="Get escalation trail for complaint"
)
async def get_escalation_history(
    complaint_id: UUID,
    complaint = Depends(get_authority_complaint),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get escalation history for complaint.
    
    Shows trail of authority assignments.
    """
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from src.database.models import Complaint, StatusUpdate
    
    # Get all status updates related to escalation
    query = (
        select(StatusUpdate)
        .options(selectinload(StatusUpdate.updated_by_authority))
        .where(StatusUpdate.complaint_id == complaint_id)
        .where(StatusUpdate.reason.like("%Escalated%"))
        .order_by(StatusUpdate.updated_at)
    )
    
    result = await db.execute(query)
    escalations = result.scalars().all()
    
    history = []
    
    # Original assignment
    if complaint.original_assigned_authority_id:
        authority_repo = AuthorityRepository(db)
        original_authority = await authority_repo.get(complaint.original_assigned_authority_id)
        if original_authority:
            history.append({
                "level": original_authority.authority_level,
                "authority_name": original_authority.name,
                "authority_type": original_authority.authority_type,
                "assigned_at": complaint.submitted_at.isoformat(),
                "is_current": False
            })
    
    # Escalations
    for escalation in escalations:
        if escalation.updated_by_authority:
            history.append({
                "level": escalation.updated_by_authority.authority_level,
                "authority_name": escalation.updated_by_authority.name,
                "authority_type": escalation.updated_by_authority.authority_type,
                "escalated_at": escalation.updated_at.isoformat(),
                "reason": escalation.reason,
                "is_current": False
            })
    
    # Current assignment
    if complaint.assigned_authority:
        history.append({
            "level": complaint.assigned_authority.authority_level,
            "authority_name": complaint.assigned_authority.name,
            "authority_type": complaint.assigned_authority.authority_type,
            "assigned_at": complaint.assigned_at.isoformat() if complaint.assigned_at else None,
            "is_current": True
        })
    
    return {
        "complaint_id": str(complaint_id),
        "escalation_count": len(escalations),
        "history": history
    }


# ==================== NOTICES / BROADCASTS ====================

# Authority-type targeting scope:
# Men's Hostel Warden/Deputy   → Male + Hostel only
# Women's Hostel Warden/Deputy → Female + Hostel only
# Senior Deputy Warden         → Hostel only (both genders)
# HOD                          → Own department only (any stay/gender)
# Admin / Admin Officer / DC   → No restrictions

def _apply_notice_scope(authority, data: NoticeCreate) -> dict:
    """
    Enforce per-authority-type targeting restrictions.
    Returns validated and clamped targeting fields.
    Raises HTTPException 403 on scope violation.
    """
    atype = authority.authority_type
    tg = list(data.target_gender) if data.target_gender else None
    ts = list(data.target_stay_types) if data.target_stay_types else None
    td = list(data.target_departments) if data.target_departments else None
    ty = list(data.target_years) if data.target_years else None

    if atype in ("Men's Hostel Warden", "Men's Hostel Deputy Warden"):
        if tg and "Female" in tg:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail="Men's Hostel authorities cannot target female students")
        if ts and "Day Scholar" in ts:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail="Men's Hostel authorities cannot target Day Scholars")
        tg = ["Male"]
        ts = ["Hostel"]

    elif atype in ("Women's Hostel Warden", "Women's Hostel Deputy Warden"):
        if tg and "Male" in tg:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail="Women's Hostel authorities cannot target male students")
        if ts and "Day Scholar" in ts:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail="Women's Hostel authorities cannot target Day Scholars")
        tg = ["Female"]
        ts = ["Hostel"]

    elif atype == "Senior Deputy Warden":
        if ts and "Day Scholar" in ts:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail="Senior Deputy Warden can only send notices to hostel students")
        ts = ["Hostel"]

    elif atype == "HOD":
        dept = authority.department.code if authority.department else None
        if not dept:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                detail="HOD account is not linked to a department")
        if td and dept not in td:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                detail=f"HOD can only send notices to their own department ({dept})")
        td = [dept]

    # Admin, Admin Officer, DC → no restrictions

    # Determine coarse visibility label from final targets
    if ts == ["Hostel"] and tg == ["Male"]:
        visibility = "Hostel"
    elif ts == ["Hostel"] and tg == ["Female"]:
        visibility = "Hostel"
    elif ts == ["Hostel"]:
        visibility = "Hostel"
    elif ts == ["Day Scholar"]:
        visibility = "Day Scholar"
    elif td:
        visibility = "Department"
    else:
        visibility = "All Students"

    return {
        "target_gender": tg,
        "target_stay_types": ts,
        "target_departments": td,
        "target_years": ty,
        "visibility": visibility,
    }


@router.post(
    "/notices",
    summary="Send a targeted notice",
    description=(
        "Authority sends a notice to targeted students. "
        "Scope is automatically restricted based on authority type: "
        "hostel wardens can only reach their hostel, HODs only their department, etc."
    )
)
async def create_notice(
    data: NoticeCreate,
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """Create and send a targeted notice to students."""
    from src.database.models import AuthorityUpdate

    authority_repo = AuthorityRepository(db)
    authority = await authority_repo.get_with_department(authority_id)
    if not authority:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Authority not found")

    scope = _apply_notice_scope(authority, data)

    notice = AuthorityUpdate(
        authority_id=authority_id,
        title=data.title,
        content=data.content,
        category=data.category.value,
        priority=data.priority.value,
        visibility=scope["visibility"],
        target_departments=scope["target_departments"],
        target_years=scope["target_years"],
        target_stay_types=scope["target_stay_types"],
        target_gender=scope["target_gender"],
        is_active=True,
        expires_at=data.expires_at,
    )

    db.add(notice)
    await db.commit()
    await db.refresh(notice)

    logger.info(
        f"Notice created by authority {authority_id} ({authority.authority_type}): "
        f"id={notice.id}, targets={scope}"
    )

    return {
        "success": True,
        "message": "Notice sent successfully",
        "id": notice.id,
        "target_gender": scope["target_gender"],
        "target_stay_types": scope["target_stay_types"],
        "target_departments": scope["target_departments"],
        "target_years": scope["target_years"],
        "visibility": scope["visibility"],
    }


@router.get(
    "/my-notices",
    summary="Get notices sent by current authority",
    description="Paginated list of notices posted by the current authority"
)
async def get_my_notices(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """List notices created by the current authority."""
    from src.database.models import AuthorityUpdate, Authority
    from sqlalchemy import select, func, and_

    conditions = [AuthorityUpdate.authority_id == authority_id]
    if active_only:
        now = datetime.now(timezone.utc)
        conditions.append(AuthorityUpdate.is_active == True)
        conditions.append(
            (AuthorityUpdate.expires_at == None) | (AuthorityUpdate.expires_at > now)
        )

    total_q = select(func.count()).where(and_(*conditions))
    total_r = await db.execute(total_q)
    total = total_r.scalar() or 0

    notices_q = (
        select(AuthorityUpdate)
        .where(and_(*conditions))
        .order_by(AuthorityUpdate.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    notices_r = await db.execute(notices_q)
    notices = notices_r.scalars().all()

    authority_repo = AuthorityRepository(db)
    authority = await authority_repo.get(authority_id)
    auth_name = authority.name if authority else None
    auth_type = authority.authority_type if authority else None

    items = []
    for n in notices:
        items.append(NoticeResponse(
            id=n.id,
            authority_id=n.authority_id,
            authority_name=auth_name,
            authority_type=auth_type,
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
        ))

    return NoticeListResponse(
        notices=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit if total else 0,
    )


@router.delete(
    "/notices/{notice_id}",
    summary="Deactivate a notice",
    description="Authority deactivates (soft-deletes) one of their own notices"
)
async def deactivate_notice(
    notice_id: int,
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a notice (only the creator or Admin can do this)."""
    from src.database.models import AuthorityUpdate
    from sqlalchemy import select

    result = await db.execute(
        select(AuthorityUpdate).where(AuthorityUpdate.id == notice_id)
    )
    notice = result.scalar_one_or_none()

    if not notice:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notice not found")

    # Only the creator or Admin can deactivate
    authority_repo = AuthorityRepository(db)
    authority = await authority_repo.get(authority_id)
    is_admin = authority and authority.authority_type == "Admin"

    if not is_admin and notice.authority_id != authority_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="You can only deactivate your own notices")

    notice.is_active = False
    await db.commit()

    logger.info(f"Notice {notice_id} deactivated by authority {authority_id}")
    return {"success": True, "message": "Notice deactivated"}


@router.post(
    "/notices/{notice_id}/attachment",
    summary="Upload file attachment to a notice",
)
async def upload_notice_attachment(
    notice_id: int,
    file: UploadFile = File(...),
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """Upload/replace a file attachment on an existing notice (only creator or Admin)."""
    from src.database.models import AuthorityUpdate
    from sqlalchemy import select

    result = await db.execute(select(AuthorityUpdate).where(AuthorityUpdate.id == notice_id))
    notice = result.scalar_one_or_none()
    if not notice:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notice not found")

    authority_repo = AuthorityRepository(db)
    authority = await authority_repo.get(authority_id)
    is_admin = authority and authority.authority_type == "Admin"
    if not is_admin and notice.authority_id != authority_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="You can only attach files to your own notices")

    # Validate file size (max 10 MB) and type
    MAX_SIZE = 10 * 1024 * 1024
    ALLOWED_TYPES = {
        "application/pdf", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "image/jpeg", "image/png", "image/webp",
    }
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="File must be under 10 MB")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")

    notice.attachment_data = data
    notice.attachment_filename = file.filename
    notice.attachment_mimetype = file.content_type
    await db.commit()

    logger.info(f"Attachment '{file.filename}' uploaded to notice {notice_id} by authority {authority_id}")
    return {"success": True, "message": "Attachment uploaded", "filename": file.filename}


@router.get(
    "/notices/{notice_id}/attachment",
    summary="Download notice attachment",
)
async def download_notice_attachment(
    notice_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Download the file attachment from a notice (public)."""
    from src.database.models import AuthorityUpdate
    from fastapi.responses import Response
    from sqlalchemy import select

    result = await db.execute(select(AuthorityUpdate).where(AuthorityUpdate.id == notice_id))
    notice = result.scalar_one_or_none()
    if not notice or not notice.attachment_data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    # Use inline disposition so browser opens images/PDFs directly instead of downloading
    return Response(
        content=notice.attachment_data,
        media_type=notice.attachment_mimetype or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{notice.attachment_filename or "attachment"}"'},
    )


# ==================== STATISTICS ====================

@router.get(
    "/stats",
    response_model=AuthorityStats,
    summary="Get authority statistics",
    description="Get performance statistics for current authority"
)
async def get_authority_stats(
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics for current authority."""
    # ✅ FIXED: Use count queries
    from sqlalchemy import select, func, and_
    from src.database.models import Complaint
    
    # Total assigned
    total_query = select(func.count()).where(
        Complaint.assigned_authority_id == authority_id
    )
    total_result = await db.execute(total_query)
    total_assigned = total_result.scalar() or 0
    
    # By status
    pending_query = select(func.count()).where(
        and_(
            Complaint.assigned_authority_id == authority_id,
            Complaint.status == "Raised"
        )
    )
    pending_result = await db.execute(pending_query)
    pending = pending_result.scalar() or 0
    
    in_progress_query = select(func.count()).where(
        and_(
            Complaint.assigned_authority_id == authority_id,
            Complaint.status == "In Progress"
        )
    )
    in_progress_result = await db.execute(in_progress_query)
    in_progress = in_progress_result.scalar() or 0
    
    resolved_query = select(func.count()).where(
        and_(
            Complaint.assigned_authority_id == authority_id,
            Complaint.status == "Resolved"
        )
    )
    resolved_result = await db.execute(resolved_query)
    resolved = resolved_result.scalar() or 0
    
    closed_query = select(func.count()).where(
        and_(
            Complaint.assigned_authority_id == authority_id,
            Complaint.status == "Closed"
        )
    )
    closed_result = await db.execute(closed_query)
    closed = closed_result.scalar() or 0
    
    spam_query = select(func.count()).where(
        and_(
            Complaint.assigned_authority_id == authority_id,
            Complaint.is_marked_as_spam == True
        )
    )
    spam_result = await db.execute(spam_query)
    spam_flagged = spam_result.scalar() or 0
    
    stats = {
        "total_assigned": total_assigned,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved,
        "closed": closed,
        "spam_flagged": spam_flagged,
        "avg_resolution_time_hours": None,
        "performance_rating": None,
    }
    
    return AuthorityStats(**stats)


@router.get(
    "/stats/detailed",
    summary="Get detailed authority statistics for executive dashboard",
    description="Returns category breakdown, priority breakdown, resolution rate, and weekly trend"
)
async def get_authority_stats_detailed(
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select, func, and_, case
    from datetime import datetime, timezone, timedelta
    from src.database.models import Complaint, ComplaintCategory

    base = Complaint.assigned_authority_id == authority_id

    # --- Category breakdown ---
    cat_q = (
        select(ComplaintCategory.name, func.count(Complaint.id).label("count"))
        .join(ComplaintCategory, Complaint.category_id == ComplaintCategory.id)
        .where(base)
        .group_by(ComplaintCategory.name)
    )
    cat_res = await db.execute(cat_q)
    by_category = {row.name: row.count for row in cat_res.all()}

    # --- Priority breakdown ---
    pri_q = (
        select(Complaint.priority, func.count(Complaint.id).label("count"))
        .where(base)
        .group_by(Complaint.priority)
    )
    pri_res = await db.execute(pri_q)
    by_priority = {row.priority: row.count for row in pri_res.all()}

    # --- Status breakdown ---
    stat_q = (
        select(Complaint.status, func.count(Complaint.id).label("count"))
        .where(base)
        .group_by(Complaint.status)
    )
    stat_res = await db.execute(stat_q)
    by_status = {row.status: row.count for row in stat_res.all()}

    total = sum(by_status.values())
    resolved = by_status.get("Resolved", 0) + by_status.get("Closed", 0)
    resolution_rate = round((resolved / total * 100), 1) if total > 0 else 0.0

    # --- Avg resolution time (hours) — EWMA (α=0.3), ordered chronologically ---
    times_q = select(
        func.extract("epoch", Complaint.resolved_at - Complaint.submitted_at) / 3600
    ).where(and_(
        base,
        Complaint.resolved_at.isnot(None),
        Complaint.status.in_(["Resolved", "Closed"])
    )).order_by(Complaint.resolved_at)
    times_res = await db.execute(times_q)
    resolution_times = [float(t) for t in times_res.scalars() if t is not None]

    if not resolution_times:
        avg_hours = None
    else:
        alpha = 0.3
        ewma = resolution_times[0]
        for t in resolution_times[1:]:
            ewma = alpha * t + (1 - alpha) * ewma
        avg_hours = round(ewma, 1)

    # --- Weekly trend (last 4 weeks, complaints submitted) ---
    now = datetime.now(timezone.utc)
    weeks = []
    for i in range(3, -1, -1):
        week_start = now - timedelta(weeks=i + 1)
        week_end = now - timedelta(weeks=i)
        wq = select(func.count()).where(and_(
            base,
            Complaint.submitted_at >= week_start,
            Complaint.submitted_at < week_end,
        ))
        wr = await db.execute(wq)
        weeks.append({
            "label": f"W-{i}" if i > 0 else "This week",
            "count": wr.scalar() or 0
        })

    return {
        "total": total,
        "by_category": by_category,
        "by_priority": by_priority,
        "by_status": by_status,
        "resolution_rate": resolution_rate,
        "avg_resolution_hours": avg_hours,
        "weekly_trend": weeks,
    }


# ==================== NOTIFICATIONS (Authority/Admin) ====================

@router.get(
    "/notifications",
    summary="Get authority notifications",
    description="Get all notifications for the current authority or admin"
)
async def get_authority_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_authority=Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    from src.repositories.notification_repo import NotificationRepository
    notification_repo = NotificationRepository(db)
    authority_id = str(current_authority.id)

    notifications = await notification_repo.get_by_recipient(
        recipient_id=authority_id,
        recipient_type="Authority",
        skip=skip,
        limit=limit,
        unread_only=unread_only
    )
    total = await notification_repo.count_by_recipient(
        recipient_id=authority_id,
        recipient_type="Authority"
    )
    unread_count = await notification_repo.count_unread(
        recipient_id=authority_id,
        recipient_type="Authority"
    )
    from src.schemas.notification import NotificationResponse
    return {
        "notifications": [NotificationResponse.model_validate(n) for n in notifications],
        "total": total,
        "unread_count": unread_count,
        "skip": skip,
        "limit": limit
    }


@router.put(
    "/notifications/{notification_id}/read",
    summary="Mark authority notification as read"
)
async def mark_authority_notification_read(
    notification_id: int,
    current_authority=Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    from src.repositories.notification_repo import NotificationRepository
    notification_repo = NotificationRepository(db)
    authority_id = str(current_authority.id)

    notification = await notification_repo.get(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.recipient_id != authority_id or notification.recipient_type != "Authority":
        raise HTTPException(status_code=403, detail="Access denied")

    await notification_repo.mark_as_read(notification_id)
    return {"success": True, "message": "Notification marked as read"}


@router.put(
    "/notifications/mark-all-read",
    summary="Mark all authority notifications as read"
)
async def mark_all_authority_notifications_read(
    current_authority=Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    from src.repositories.notification_repo import NotificationRepository
    notification_repo = NotificationRepository(db)
    authority_id = str(current_authority.id)

    count = await notification_repo.mark_all_as_read(
        recipient_id=authority_id,
        recipient_type="Authority"
    )
    return {"success": True, "message": f"Marked {count} notifications as read"}


@router.delete(
    "/notifications/{notification_id}",
    summary="Delete authority notification"
)
async def delete_authority_notification(
    notification_id: int,
    current_authority=Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    from src.repositories.notification_repo import NotificationRepository
    notification_repo = NotificationRepository(db)
    authority_id = str(current_authority.id)

    notification = await notification_repo.get(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.recipient_id != authority_id or notification.recipient_type != "Authority":
        raise HTTPException(status_code=403, detail="Access denied")

    await notification_repo.delete(notification_id)
    return {"success": True, "message": "Notification deleted"}


__all__ = ["router"]
