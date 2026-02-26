"""
Admin API endpoints.

System administration, user management, analytics, bulk operations.

✅ FIXED: Import from src.database.connection
✅ FIXED: Import from src.api.dependencies
✅ ADDED: Comprehensive system analytics
✅ ADDED: Bulk operations for complaints
✅ ADDED: Authority management (activate/deactivate)
✅ ADDED: Student management endpoints
✅ ADDED: Image moderation endpoints
✅ ADDED: System health metrics
"""

import logging
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_current_admin  # ✅ FIXED IMPORT
from src.schemas.authority import (
    AuthorityCreate,
    AuthorityProfile,
    AuthorityListResponse,
)
from src.schemas.student import StudentProfile, StudentListResponse
from src.schemas.complaint import ComplaintListResponse, ComplaintResponse
from src.schemas.common import SuccessResponse
from src.repositories.authority_repo import AuthorityRepository
from src.repositories.student_repo import StudentRepository
from src.repositories.complaint_repo import ComplaintRepository
from src.services.auth_service import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ==================== AUTHORITY MANAGEMENT ====================

@router.post(
    "/authorities",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create authority",
    description="Create new authority account (admin only)"
)
async def create_authority(
    data: AuthorityCreate,
    current_authority_id: int = Depends(get_current_admin),  # ✅ FIXED
    db: AsyncSession = Depends(get_db)
):
    """
    Create new authority account.
    
    Requires admin privileges.
    """
    authority_repo = AuthorityRepository(db)

    # Validate email domain
    if not str(data.email).endswith('@srec.ac.in'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authority email must be a valid @srec.ac.in address"
        )

    # Check if email already exists
    existing = await authority_repo.get_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Hash password
    password_hash = auth_service.hash_password(data.password)
    
    # Create authority
    await authority_repo.create(
        name=data.name,
        email=data.email,
        password_hash=password_hash,
        phone=data.phone,
        authority_type=data.authority_type,
        department_id=data.department_id,
        designation=data.designation,
        authority_level=data.authority_level
    )
    
    logger.info(f"Authority created: {data.email} by admin {current_authority_id}")
    
    return SuccessResponse(
        success=True,
        message="Authority created successfully"
    )


@router.get(
    "/authorities",
    response_model=AuthorityListResponse,
    summary="List authorities",
    description="Get list of all authorities (admin only)"
)
async def list_authorities(
    current_authority_id: int = Depends(get_current_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db)
):
    """List all authorities with optional filtering."""
    authority_repo = AuthorityRepository(db)
    
    # ✅ FIXED: Use proper count query
    from sqlalchemy import select, func, and_
    from src.database.models import Authority
    
    # Build conditions
    conditions = []
    if is_active is not None:
        conditions.append(Authority.is_active == is_active)
    
    # Get authorities
    query = select(Authority).order_by(Authority.created_at.desc())
    if conditions:
        query = query.where(and_(*conditions))
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    authorities = result.scalars().all()
    
    # Count
    count_query = select(func.count())
    if conditions:
        count_query = count_query.where(and_(*conditions))
    count_result = await db.execute(count_query.select_from(Authority))
    total = count_result.scalar() or 0
    
    return AuthorityListResponse(
        authorities=[AuthorityProfile.model_validate(a) for a in authorities],
        total=total
    )


@router.put(
    "/authorities/{authority_id}/toggle-active",
    response_model=SuccessResponse,
    summary="Toggle authority active status",
    description="Activate or deactivate authority account (admin only)"
)
async def toggle_authority_status(
    authority_id: int,
    activate: bool = Query(..., description="True to activate, False to deactivate"),
    current_authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Toggle authority active status.
    
    - **activate**: True to activate, False to deactivate
    """
    # Prevent self-deactivation
    if authority_id == current_authority_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own account status"
        )
    
    authority_repo = AuthorityRepository(db)
    authority = await authority_repo.get(authority_id)
    
    if not authority:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority not found"
        )
    
    # Update status
    authority.is_active = activate
    authority.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    action = "activated" if activate else "deactivated"
    logger.info(f"Authority {authority_id} {action} by admin {current_authority_id}")
    
    return SuccessResponse(
        success=True,
        message=f"Authority account {action}"
    )


@router.delete(
    "/authorities/{authority_id}",
    response_model=SuccessResponse,
    summary="Delete authority",
    description="Delete authority account (admin only)"
)
async def delete_authority(
    authority_id: int,
    current_authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Delete authority account.
    
    Note: Cannot delete authority with assigned complaints.
    """
    # Prevent self-deletion
    if authority_id == current_authority_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Check for assigned complaints
    from sqlalchemy import select, func
    from src.database.models import Complaint, Authority
    
    complaint_count_query = select(func.count()).where(
        Complaint.assigned_authority_id == authority_id
    )
    complaint_count_result = await db.execute(complaint_count_query)
    complaint_count = complaint_count_result.scalar() or 0
    
    if complaint_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete authority with {complaint_count} assigned complaints"
        )
    
    # Delete authority
    authority_query = select(Authority).where(Authority.id == authority_id)
    authority_result = await db.execute(authority_query)
    authority = authority_result.scalar_one_or_none()
    
    if not authority:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority not found"
        )
    
    await db.delete(authority)
    await db.commit()
    
    logger.info(f"Authority {authority_id} deleted by admin {current_authority_id}")
    
    return SuccessResponse(
        success=True,
        message="Authority deleted successfully"
    )


# ==================== STUDENT MANAGEMENT ====================

@router.get(
    "/students",
    response_model=StudentListResponse,
    summary="List students",
    description="Get list of all students (admin only)"
)
async def list_students(
    current_authority_id: int = Depends(get_current_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    department_code: Optional[str] = Query(None, description="Filter by department code (e.g. CSE)"),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: List all students with optional filtering.
    """
    from sqlalchemy import select, func, and_
    from sqlalchemy.orm import selectinload
    from src.database.models import Student, Department

    # Build conditions
    conditions = []
    if is_active is not None:
        conditions.append(Student.is_active == is_active)
    if department_id is not None:
        conditions.append(Student.department_id == department_id)
    if department_code:
        # Resolve code to ID via subquery
        dept_id_subq = select(Department.id).where(Department.code == department_code).scalar_subquery()
        conditions.append(Student.department_id == dept_id_subq)

    # Get students with department loaded
    query = select(Student).options(selectinload(Student.department)).order_by(Student.roll_no)
    if conditions:
        query = query.where(and_(*conditions))
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    students = result.scalars().all()

    # Count
    count_query = select(func.count())
    if conditions:
        count_query = count_query.where(and_(*conditions))
    count_result = await db.execute(count_query.select_from(Student))
    total = count_result.scalar() or 0

    # Build response with department info populated
    student_responses = []
    for s in students:
        profile = StudentProfile.model_validate(s)
        if s.department:
            profile.department_code = s.department.code
            profile.department_name = s.department.name
        student_responses.append(profile)

    return StudentListResponse(
        students=student_responses,
        total=total
    )


@router.put(
    "/students/{roll_no}/toggle-active",
    response_model=SuccessResponse,
    summary="Toggle student active status",
    description="Activate or deactivate student account (admin only)"
)
async def toggle_student_status(
    roll_no: str,
    activate: bool = Query(..., description="True to activate, False to deactivate"),
    current_authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Toggle student active status.
    
    - **activate**: True to activate, False to deactivate
    """
    student_repo = StudentRepository(db)
    student = await student_repo.get(roll_no)
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Update status
    student.is_active = activate
    student.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    action = "activated" if activate else "deactivated"
    logger.info(f"Student {roll_no} {action} by admin {current_authority_id}")
    
    return SuccessResponse(
        success=True,
        message=f"Student account {action}"
    )


# ==================== COMPLAINT MANAGEMENT ====================

@router.get(
    "/complaints",
    response_model=ComplaintListResponse,
    summary="Admin: list all complaints",
    description="List all complaints system-wide with optional filters (admin only)"
)
async def admin_list_complaints(
    status_filter: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    category_name: Optional[str] = Query(None),
    department_code: Optional[str] = Query(None, description="Filter by department code (e.g. CSE)"),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all complaints with optional status, priority, category, department, date range, and search filters."""
    from sqlalchemy import select, func, and_, or_
    from sqlalchemy.orm import selectinload
    from src.database.models import Complaint, ComplaintCategory, Department

    conditions = []
    if status_filter:
        conditions.append(Complaint.status == status_filter)
    if priority:
        conditions.append(Complaint.priority == priority)
    if category_id:
        conditions.append(Complaint.category_id == category_id)
    if category_name:
        cat_subq = select(ComplaintCategory.id).where(
            ComplaintCategory.name.ilike(f"%{category_name}%")
        ).scalar_subquery()
        conditions.append(Complaint.category_id.in_(cat_subq))
    if department_code:
        dept_id_subq = select(Department.id).where(Department.code == department_code).scalar_subquery()
        conditions.append(Complaint.complaint_department_id == dept_id_subq)
    if search:
        conditions.append(or_(
            Complaint.rephrased_text.ilike(f"%{search}%"),
            Complaint.original_text.ilike(f"%{search}%"),
        ))
    if date_from:
        try:
            df = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            conditions.append(Complaint.submitted_at >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
            conditions.append(Complaint.submitted_at < dt)
        except ValueError:
            pass

    where_clause = and_(*conditions) if conditions else True

    query = (
        select(Complaint)
        .options(
            selectinload(Complaint.category),
            selectinload(Complaint.student),
            selectinload(Complaint.assigned_authority),
        )
        .where(where_clause)
        .order_by(Complaint.submitted_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    complaints = result.scalars().all()

    count_result = await db.execute(select(func.count()).select_from(Complaint).where(where_clause))
    total = count_result.scalar() or 0

    complaint_responses = []
    for c in complaints:
        data = {
            "id": c.id,
            "category_id": c.category_id,
            "category_name": c.category.name if c.category else None,
            "original_text": c.original_text,
            "rephrased_text": c.rephrased_text,
            "visibility": c.visibility,
            "upvotes": c.upvotes,
            "downvotes": c.downvotes,
            "priority": c.priority,
            "priority_score": c.priority_score,
            "status": c.status,
            "assigned_authority_name": c.assigned_authority.name if c.assigned_authority else None,
            "is_marked_as_spam": c.is_marked_as_spam,
            "has_image": c.has_image,
            "image_verified": c.image_verified,
            "image_verification_status": c.image_verification_status,
            "submitted_at": c.submitted_at,
            "updated_at": c.updated_at,
            "resolved_at": c.resolved_at,
            "student_roll_no": c.student_roll_no,
            "student_name": c.student.name if c.student else None,
        }
        complaint_responses.append(ComplaintResponse.model_validate(data))

    return ComplaintListResponse(
        complaints=complaint_responses,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit
    )


# ==================== SYSTEM STATISTICS ====================

@router.get(
    "/stats/overview",
    summary="System overview statistics",
    description="Get overall system statistics (admin only)"
)
async def get_system_stats(
    current_authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive system-wide statistics."""
    from sqlalchemy import select, func
    from src.database.models import Student, Authority, Complaint
    
    # ✅ FIXED: Use count queries
    # Total counts
    student_count_query = select(func.count()).select_from(Student)
    student_count_result = await db.execute(student_count_query)
    total_students = student_count_result.scalar() or 0
    
    authority_count_query = select(func.count()).select_from(Authority)
    authority_count_result = await db.execute(authority_count_query)
    total_authorities = authority_count_result.scalar() or 0
    
    complaint_count_query = select(func.count()).select_from(Complaint)
    complaint_count_result = await db.execute(complaint_count_query)
    total_complaints = complaint_count_result.scalar() or 0
    
    # Get complaint stats
    complaint_repo = ComplaintRepository(db)
    status_counts = await complaint_repo.count_by_status()
    priority_counts = await complaint_repo.count_by_priority()
    category_counts = await complaint_repo.count_by_category()
    image_counts = await complaint_repo.count_images()
    
    # Recent activity (last 7 days)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_complaints_query = select(func.count()).where(
        Complaint.submitted_at >= seven_days_ago
    )
    recent_result = await db.execute(recent_complaints_query)
    recent_complaints = recent_result.scalar() or 0

    # Complaints per department (by dept code)
    from src.database.models import Department as DeptModel
    dept_complaints_query = (
        select(DeptModel.code, func.count(Complaint.id))
        .join(Complaint, Complaint.complaint_department_id == DeptModel.id, isouter=True)
        .group_by(DeptModel.code)
    )
    dept_complaints_result = await db.execute(dept_complaints_query)
    complaints_by_department = {row[0]: row[1] for row in dept_complaints_result.fetchall()}

    # Students per department (by dept code)
    from src.database.models import Student as StudentModel
    dept_students_query = (
        select(DeptModel.code, func.count(StudentModel.roll_no))
        .join(StudentModel, StudentModel.department_id == DeptModel.id, isouter=True)
        .group_by(DeptModel.code)
    )
    dept_students_result = await db.execute(dept_students_query)
    students_by_department = {row[0]: row[1] for row in dept_students_result.fetchall()}

    return {
        "total_students": total_students,
        "total_authorities": total_authorities,
        "total_complaints": total_complaints,
        "recent_complaints_7d": recent_complaints,
        "complaints_by_status": status_counts,
        "complaints_by_priority": priority_counts,
        "complaints_by_category": category_counts,
        "image_statistics": image_counts,
        "complaints_by_department": complaints_by_department,
        "students_by_department": students_by_department,
    }


@router.get(
    "/stats/analytics",
    summary="Advanced analytics",
    description="Get detailed analytics and trends (admin only)"
)
async def get_analytics(
    current_authority_id: int = Depends(get_current_admin),
    days: int = Query(30, ge=1, le=365, description="Number of days for trend analysis"),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get advanced analytics and trends.
    
    Includes:
    - Complaint trends over time
    - Resolution rates
    - Average response times
    - Department performance
    """
    from sqlalchemy import select, func, and_, case
    from src.database.models import Complaint
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Complaints over time
    daily_complaints_query = (
        select(
            func.date(Complaint.submitted_at).label('date'),
            func.count(Complaint.id).label('count')
        )
        .where(Complaint.submitted_at >= start_date)
        .group_by(func.date(Complaint.submitted_at))
        .order_by(func.date(Complaint.submitted_at))
    )
    daily_result = await db.execute(daily_complaints_query)
    daily_complaints = [
        {"date": str(row.date), "count": row.count}
        for row in daily_result
    ]
    
    # Resolution rate
    total_query = select(func.count()).where(
        Complaint.submitted_at >= start_date
    )
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0
    
    resolved_query = select(func.count()).where(
        and_(
            Complaint.submitted_at >= start_date,
            Complaint.status.in_(["Resolved", "Closed"])
        )
    )
    resolved_result = await db.execute(resolved_query)
    resolved = resolved_result.scalar() or 0
    
    resolution_rate = (resolved / total * 100) if total > 0 else 0
    
    # Average resolution time (for resolved complaints)
    avg_time_query = select(
        func.avg(
            func.extract('epoch', Complaint.resolved_at - Complaint.submitted_at) / 3600
        )
    ).where(
        and_(
            Complaint.submitted_at >= start_date,
            Complaint.resolved_at.isnot(None)
        )
    )
    avg_time_result = await db.execute(avg_time_query)
    avg_resolution_hours = avg_time_result.scalar() or 0
    
    return {
        "period_days": days,
        "total_complaints": total,
        "resolved_complaints": resolved,
        "resolution_rate_percent": round(resolution_rate, 2),
        "avg_resolution_time_hours": round(avg_resolution_hours, 2),
        "daily_complaints": daily_complaints
    }


# ==================== BULK OPERATIONS ====================

@router.post(
    "/complaints/bulk-status-update",
    response_model=SuccessResponse,
    summary="Bulk update complaint status",
    description="Update status for multiple complaints (admin only)"
)
async def bulk_update_status(
    complaint_ids: list[str] = Query(..., description="List of complaint UUIDs"),
    new_status: str = Query(..., description="New status to apply"),
    reason: str = Query(..., description="Reason for bulk update"),
    current_authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Bulk update complaint status.
    
    Useful for mass operations like closing old complaints.
    """
    from uuid import UUID
    from src.database.models import Complaint, StatusUpdate
    
    # Validate status
    valid_statuses = ["Raised", "In Progress", "Resolved", "Closed", "Spam"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Convert to UUIDs
    try:
        uuids = [UUID(cid) for cid in complaint_ids]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid complaint ID format"
        )
    
    # Get complaints
    from sqlalchemy import select
    query = select(Complaint).where(Complaint.id.in_(uuids))
    result = await db.execute(query)
    complaints = result.scalars().all()
    
    if not complaints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No complaints found with provided IDs"
        )
    
    # Update each complaint
    updated_count = 0
    for complaint in complaints:
        old_status = complaint.status
        
        # Create status update record
        status_update = StatusUpdate(
            complaint_id=complaint.id,
            updated_by=current_authority_id,
            old_status=old_status,
            new_status=new_status,
            reason=f"Bulk update: {reason}"
        )
        db.add(status_update)
        
        # Update complaint
        complaint.status = new_status
        complaint.updated_at = datetime.now(timezone.utc)
        
        if new_status in ["Resolved", "Closed"] and not complaint.resolved_at:
            complaint.resolved_at = datetime.now(timezone.utc)
        
        updated_count += 1
    
    await db.commit()
    
    logger.info(f"Bulk status update: {updated_count} complaints updated to {new_status} by admin {current_authority_id}")
    
    return SuccessResponse(
        success=True,
        message=f"{updated_count} complaints updated to '{new_status}'"
    )


# ==================== IMAGE MODERATION ====================

@router.get(
    "/images/pending-verification",
    summary="Get images pending verification",
    description="Get list of complaint images needing verification (admin only)"
)
async def get_pending_images(
    current_authority_id: int = Depends(get_current_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get complaints with images pending verification.
    
    For manual moderation of uploaded images.
    """
    complaint_repo = ComplaintRepository(db)
    
    # Get pending verifications
    complaints = await complaint_repo.get_pending_image_verification(limit=limit)
    
    # Format response
    pending_images = []
    for complaint in complaints:
        pending_images.append({
            "complaint_id": str(complaint.id),
            "student_roll_no": complaint.student_roll_no,
            "category": complaint.category.name if complaint.category else None,
            "complaint_text": complaint.rephrased_text[:100] + "..." if len(complaint.rephrased_text) > 100 else complaint.rephrased_text,
            "image_filename": complaint.image_filename,
            "image_size_kb": complaint.image_size // 1024 if complaint.image_size else 0,
            "submitted_at": complaint.submitted_at.isoformat()
        })
    
    return {
        "total": len(pending_images),
        "pending_images": pending_images
    }


@router.post(
    "/images/{complaint_id}/moderate",
    response_model=SuccessResponse,
    summary="Moderate complaint image",
    description="Approve or reject complaint image (admin only)"
)
async def moderate_image(
    complaint_id: str,
    approve: bool = Query(..., description="True to approve, False to reject"),
    reason: Optional[str] = Query(None, description="Reason for rejection"),
    current_authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Manually moderate complaint image.
    
    - **approve**: True to approve, False to reject
    - **reason**: Required if rejecting
    """
    from uuid import UUID
    
    try:
        complaint_uuid = UUID(complaint_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid complaint ID format"
        )
    
    complaint_repo = ComplaintRepository(db)
    complaint = await complaint_repo.get(complaint_uuid)
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    if not complaint.image_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image attached to this complaint"
        )
    
    # Update verification status
    if approve:
        complaint.image_verified = True
        complaint.image_verification_status = "Verified"
        message = "Image approved"
    else:
        if not reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reason required for rejection"
            )
        complaint.image_verified = False
        complaint.image_verification_status = "Rejected"
        message = f"Image rejected: {reason}"
    
    complaint.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    logger.info(f"Image moderation for complaint {complaint_id}: {'approved' if approve else 'rejected'} by admin {current_authority_id}")
    
    return SuccessResponse(
        success=True,
        message=message
    )


# ==================== ESCALATIONS ====================

@router.get(
    "/escalations",
    summary="Admin: get escalation overview",
    description="Returns escalated complaints, critical unescalated issues, and overdue complaints"
)
async def admin_get_escalations(
    current_authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select, func, and_, or_
    from sqlalchemy.orm import selectinload
    from src.database.models import Complaint
    from src.config.constants import ESCALATION_THRESHOLD_DAYS

    threshold_dt = datetime.now(timezone.utc) - timedelta(days=ESCALATION_THRESHOLD_DAYS)

    def _complaint_dict(c):
        return {
            "id": str(c.id),
            "category_name": c.category.name if c.category else None,
            "rephrased_text": c.rephrased_text,
            "original_text": c.original_text,
            "status": c.status,
            "priority": c.priority,
            "student_roll_no": c.student_roll_no,
            "student_name": c.student.name if c.student else None,
            "assigned_authority_name": c.assigned_authority.name if c.assigned_authority else None,
            "submitted_at": c.submitted_at.isoformat() if c.submitted_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "has_image": c.has_image,
            "is_marked_as_spam": c.is_marked_as_spam,
            "was_escalated": c.original_assigned_authority_id is not None,
        }

    load_opts = [
        selectinload(Complaint.category),
        selectinload(Complaint.student),
        selectinload(Complaint.assigned_authority),
    ]

    # 1. Escalated complaints (manually or auto escalated)
    escalated_q = (
        select(Complaint)
        .options(*load_opts)
        .where(
            and_(
                Complaint.original_assigned_authority_id.isnot(None),
                Complaint.status.notin_(["Resolved", "Closed", "Spam"]),
            )
        )
        .order_by(Complaint.submitted_at.asc())
        .limit(50)
    )
    escalated_res = await db.execute(escalated_q)
    escalated = escalated_res.scalars().all()

    # 2. Critical complaints that have NOT been escalated yet
    critical_q = (
        select(Complaint)
        .options(*load_opts)
        .where(
            and_(
                Complaint.priority == "Critical",
                Complaint.original_assigned_authority_id.is_(None),
                Complaint.status.notin_(["Resolved", "Closed", "Spam"]),
            )
        )
        .order_by(Complaint.submitted_at.asc())
        .limit(50)
    )
    critical_res = await db.execute(critical_q)
    critical = critical_res.scalars().all()

    # 3. Overdue complaints (older than threshold, still open, not yet escalated)
    overdue_q = (
        select(Complaint)
        .options(*load_opts)
        .where(
            and_(
                Complaint.status.in_(["Raised", "In Progress"]),
                Complaint.submitted_at < threshold_dt,
                Complaint.original_assigned_authority_id.is_(None),
                Complaint.priority != "Critical",  # critical already in section 2
            )
        )
        .order_by(Complaint.submitted_at.asc())
        .limit(50)
    )
    overdue_res = await db.execute(overdue_q)
    overdue = overdue_res.scalars().all()

    return {
        "summary": {
            "escalated_count": len(escalated),
            "critical_count": len(critical),
            "overdue_count": len(overdue),
            "escalation_threshold_days": ESCALATION_THRESHOLD_DAYS,
        },
        "escalated": [_complaint_dict(c) for c in escalated],
        "critical": [_complaint_dict(c) for c in critical],
        "overdue": [_complaint_dict(c) for c in overdue],
    }


# ==================== SYSTEM HEALTH ====================

@router.get(
    "/health/metrics",
    summary="System health metrics",
    description="Get system health and performance metrics (admin only)"
)
async def get_health_metrics(
    current_authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get system health metrics.
    
    Includes database stats and performance indicators.
    """
    from sqlalchemy import select, func, text
    from src.database.models import Complaint
    
    # Database size (PostgreSQL specific)
    try:
        db_size_query = text("SELECT pg_database_size(current_database())")
        db_size_result = await db.execute(db_size_query)
        db_size_bytes = db_size_result.scalar() or 0
        db_size_mb = db_size_bytes / (1024 * 1024)
    except:
        db_size_mb = None
    
    # Complaint processing stats
    pending_complaints_query = select(func.count()).where(
        Complaint.status == "Raised"
    )
    pending_result = await db.execute(pending_complaints_query)
    pending_complaints = pending_result.scalar() or 0
    
    # Old unresolved complaints (>7 days)
    from sqlalchemy import and_
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    old_complaints_query = select(func.count()).where(
        and_(
            Complaint.status.in_(["Raised", "In Progress"]),
            Complaint.submitted_at < seven_days_ago
        )
    )
    old_result = await db.execute(old_complaints_query)
    old_unresolved = old_result.scalar() or 0
    
    # Image storage stats
    complaint_repo = ComplaintRepository(db)
    image_counts = await complaint_repo.count_images()
    
    return {
        "database_size_mb": round(db_size_mb, 2) if db_size_mb else None,
        "pending_complaints": pending_complaints,
        "old_unresolved_7d": old_unresolved,
        "image_statistics": image_counts,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


__all__ = ["router"]
