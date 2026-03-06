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
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import get_db, get_current_admin, get_current_authority  # ✅ FIXED IMPORT
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
            "has_disputed": c.has_disputed,
            "appeal_reason": c.appeal_reason,
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
    
    # Average resolution time — EWMA (Exponential Weighted Moving Average, α=0.3)
    # Fetches resolution times ordered chronologically; recent complaints are
    # weighted more heavily, smoothing out historical outliers.
    times_query = select(
        func.extract('epoch', Complaint.resolved_at - Complaint.submitted_at) / 3600
    ).where(
        and_(
            Complaint.submitted_at >= start_date,
            Complaint.resolved_at.isnot(None)
        )
    ).order_by(Complaint.resolved_at)
    times_result = await db.execute(times_query)
    resolution_times = [float(t) for t in times_result.scalars() if t is not None]

    if not resolution_times:
        avg_resolution_hours = 0.0
    else:
        alpha = 0.3
        ewma = resolution_times[0]
        for t in resolution_times[1:]:
            ewma = alpha * t + (1 - alpha) * ewma
        avg_resolution_hours = ewma
    
    return {
        "period_days": days,
        "total_complaints": total,
        "resolved_complaints": resolved,
        "resolution_rate_percent": round(resolution_rate, 2),
        "avg_resolution_time_hours": round(avg_resolution_hours, 2),
        "daily_complaints": daily_complaints
    }


# ==================== Z-SCORE ANOMALY DETECTION ====================

@router.get(
    "/anomalies",
    summary="Detect anomalies in complaint patterns",
    description="Z-Score anomaly detection on daily complaint volumes (admin only)"
)
async def detect_anomalies(
    current_authority_id: int = Depends(get_current_admin),
    days: int = Query(30, ge=7, le=180),
    db: AsyncSession = Depends(get_db),
):
    """
    Z-Score anomaly detection on daily complaint volumes.
    Flags days where complaint count is > 2 standard deviations from mean.
    """
    import math
    from sqlalchemy import text, and_

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get daily complaint counts
    daily_q = text("""
        SELECT DATE(submitted_at AT TIME ZONE 'UTC') as day, COUNT(*) as count
        FROM complaints
        WHERE submitted_at >= :cutoff
        GROUP BY DATE(submitted_at AT TIME ZONE 'UTC')
        ORDER BY day
    """)
    result = await db.execute(daily_q, {"cutoff": cutoff})
    daily_rows = result.fetchall()

    if len(daily_rows) < 3:
        return {"anomalies": [], "mean": 0, "std_dev": 0, "period_days": days, "message": "Not enough data"}

    counts = [row[1] for row in daily_rows]
    mean = sum(counts) / len(counts)
    variance = sum((c - mean) ** 2 for c in counts) / len(counts)
    std_dev = math.sqrt(variance) if variance > 0 else 0.01

    anomalies = []
    for row in daily_rows:
        day_str = str(row[0])
        count = row[1]
        z_score = (count - mean) / std_dev if std_dev > 0 else 0
        if abs(z_score) >= 2.0:
            anomalies.append({
                "date": day_str,
                "count": count,
                "z_score": round(z_score, 2),
                "type": "spike" if z_score > 0 else "drop",
                "severity": "high" if abs(z_score) >= 3.0 else "moderate",
            })

    return {
        "anomalies": anomalies,
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "period_days": days,
        "total_days_analyzed": len(daily_rows),
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


@router.put(
    "/complaints/{complaint_id}/reassign",
    response_model=SuccessResponse,
    summary="Reassign complaint to different authority",
    description="Change which authority handles a complaint (admin only)"
)
async def reassign_complaint(
    complaint_id: str,
    authority_id: int = Query(..., description="ID of the new authority to assign"),
    current_authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Reassign a complaint to a different authority."""
    from uuid import UUID
    from src.database.models import Complaint, Authority

    try:
        complaint_uuid = UUID(complaint_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid complaint ID")

    result = await db.execute(select(Complaint).where(Complaint.id == complaint_uuid))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    auth_result = await db.execute(select(Authority).where(Authority.id == authority_id))
    authority = auth_result.scalar_one_or_none()
    if not authority:
        raise HTTPException(status_code=404, detail="Authority not found")

    old_authority_id = complaint.assigned_authority_id
    complaint.assigned_authority_id = authority_id
    complaint.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(
        f"Complaint {complaint_id} reassigned from authority {old_authority_id} "
        f"to {authority_id} by admin {current_authority_id}"
    )
    return SuccessResponse(success=True, message=f"Complaint reassigned to {authority.name}")


@router.delete(
    "/complaints/{complaint_id}",
    response_model=SuccessResponse,
    summary="Delete complaint",
    description="Permanently delete a complaint (admin only)"
)
async def admin_delete_complaint(
    complaint_id: str,
    current_authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Permanently delete a complaint and all related data."""
    from uuid import UUID
    from src.database.models import Complaint, Vote, StatusUpdate

    try:
        complaint_uuid = UUID(complaint_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid complaint ID")

    result = await db.execute(select(Complaint).where(Complaint.id == complaint_uuid))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Delete associated votes and status updates first (FK constraints)
    await db.execute(delete(Vote).where(Vote.complaint_id == complaint_uuid))
    await db.execute(delete(StatusUpdate).where(StatusUpdate.complaint_id == complaint_uuid))
    await db.delete(complaint)
    await db.commit()

    logger.info(f"Complaint {complaint_id} permanently deleted by admin {current_authority_id}")
    return SuccessResponse(success=True, message="Complaint deleted")


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
            "has_disputed": c.has_disputed,
            "appeal_reason": c.appeal_reason,
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


# ==================== STUDENT REPRESENTATIVES ====================


class AppointRepBody(BaseModel):
    student_roll_no: str = Field(..., min_length=3, max_length=20)
    scope: str = Field(default="Department")  # "Department" or "Hostel"


MAX_REPS_PER_DEPT_YEAR = 3  # 3 reps per department per year


async def _get_rep_authority_context(authority_id: int, db: AsyncSession) -> dict:
    """Load authority info and compute permissions for representative management."""
    from src.database.models import Authority
    result = await db.execute(select(Authority).where(Authority.id == authority_id))
    authority = result.scalar_one_or_none()
    if not authority:
        raise HTTPException(status_code=403, detail="Authority not found")

    auth_type = (authority.authority_type or "").lower()
    is_admin = authority.authority_level >= 100
    is_hod = "hod" in auth_type
    is_mens_warden = "men" in auth_type and "warden" in auth_type
    is_womens_warden = "women" in auth_type and "warden" in auth_type
    is_warden = "warden" in auth_type

    if not (is_admin or is_hod or is_warden):
        raise HTTPException(
            status_code=403,
            detail="Only Admin, HOD, or Warden can manage representatives"
        )

    return {
        "authority": authority,
        "is_admin": is_admin,
        "is_hod": is_hod,
        "is_warden": is_warden,
        "is_mens_warden": is_mens_warden,
        "is_womens_warden": is_womens_warden,
    }


@router.get(
    "/representatives",
    summary="List student representatives",
    description="List student representatives. Admin sees all; HOD sees their dept; Warden sees hostel reps."
)
async def list_representatives(
    department_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    scope: Optional[str] = Query(None),
    active_only: bool = Query(True),
    current_authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db),
):
    """List student representatives. Admin sees all; HOD sees their dept; Warden sees hostel reps."""
    from sqlalchemy import and_
    from src.database.models import StudentRepresentative, Student, Department, Authority

    ctx = await _get_rep_authority_context(current_authority_id, db)

    conditions = []
    if active_only:
        conditions.append(StudentRepresentative.is_active == True)
    if department_id is not None:
        conditions.append(StudentRepresentative.department_id == department_id)
    if year is not None:
        conditions.append(StudentRepresentative.year == year)
    if scope:
        conditions.append(StudentRepresentative.scope == scope)

    # Non-admin scoping
    if not ctx["is_admin"]:
        if ctx["is_hod"]:
            conditions.append(StudentRepresentative.department_id == ctx["authority"].department_id)
            conditions.append(StudentRepresentative.scope == "Department")
        elif ctx["is_warden"]:
            conditions.append(StudentRepresentative.scope == "Hostel")

    q = (
        select(StudentRepresentative)
        .options(
            selectinload(StudentRepresentative.student),
            selectinload(StudentRepresentative.department),
            selectinload(StudentRepresentative.appointed_by),
        )
    )
    if conditions:
        q = q.where(and_(*conditions))
    q = q.order_by(StudentRepresentative.department_id, StudentRepresentative.year)

    result = await db.execute(q)
    reps = result.scalars().all()

    items = []
    for r in reps:
        items.append({
            "id": r.id,
            "student_roll_no": r.student_roll_no,
            "student_name": r.student.name if r.student else None,
            "department_id": r.department_id,
            "department_name": r.department.name if r.department else None,
            "department_code": r.department.code if r.department else None,
            "year": r.year,
            "scope": r.scope,
            "is_active": r.is_active,
            "appointed_by_name": r.appointed_by.name if r.appointed_by else None,
            "appointed_at": r.appointed_at.isoformat() if r.appointed_at else None,
            "removed_at": r.removed_at.isoformat() if r.removed_at else None,
        })

    return {"representatives": items, "total": len(items)}


@router.post(
    "/representatives",
    status_code=status.HTTP_201_CREATED,
    summary="Appoint student representative",
)
async def appoint_representative(
    body: AppointRepBody,
    current_authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db),
):
    """Appoint a student as a representative. HOD → Department scope only (their dept).
    Warden → Hostel scope only (gender-specific). Admin → any scope.
    """
    from sqlalchemy import and_
    from src.database.models import StudentRepresentative, Student

    if body.scope not in ("Department", "Hostel"):
        raise HTTPException(status_code=400, detail="Scope must be 'Department' or 'Hostel'")

    ctx = await _get_rep_authority_context(current_authority_id, db)

    # Load student
    student_q = select(Student).where(Student.roll_no == body.student_roll_no)
    student_result = await db.execute(student_q)
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {body.student_roll_no} not found")
    if not student.is_active:
        raise HTTPException(status_code=400, detail="Student account is deactivated")

    # Permission checks for non-admin authorities
    if not ctx["is_admin"]:
        if ctx["is_hod"]:
            if body.scope != "Department":
                raise HTTPException(status_code=403, detail="HOD can only appoint Department representatives")
            if student.department_id != ctx["authority"].department_id:
                raise HTTPException(status_code=403, detail="HOD can only appoint representatives from their own department")
        elif ctx["is_warden"]:
            if body.scope != "Hostel":
                raise HTTPException(status_code=403, detail="Warden can only appoint Hostel representatives")
            if student.stay_type != "Hostel":
                raise HTTPException(status_code=400, detail="Only hostel students can be appointed as Hostel representatives")
            # Gender-specific warden restriction
            if ctx["is_mens_warden"] and student.gender not in (None, "Male"):
                raise HTTPException(status_code=403, detail="Men's Hostel Warden can only appoint male students")
            if ctx["is_womens_warden"] and student.gender not in (None, "Female"):
                raise HTTPException(status_code=403, detail="Women's Hostel Warden can only appoint female students")

    # Check if already a rep for this scope
    existing_q = select(StudentRepresentative).where(
        and_(
            StudentRepresentative.student_roll_no == body.student_roll_no,
            StudentRepresentative.scope == body.scope,
            StudentRepresentative.is_active == True,
        )
    )
    existing_result = await db.execute(existing_q)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Student is already an active {body.scope} representative")

    # Hostel scope: must be hostel student (general check for admin)
    if body.scope == "Hostel" and student.stay_type != "Hostel":
        raise HTTPException(status_code=400, detail="Only hostel students can be appointed as Hostel representatives")

    # Check capacity: max 3 per dept per year for Department scope
    if body.scope == "Department":
        count_q = select(func.count()).select_from(StudentRepresentative).where(
            and_(
                StudentRepresentative.department_id == student.department_id,
                StudentRepresentative.year == student.year,
                StudentRepresentative.scope == "Department",
                StudentRepresentative.is_active == True,
            )
        )
        current_count = (await db.execute(count_q)).scalar() or 0
        if current_count >= MAX_REPS_PER_DEPT_YEAR:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {MAX_REPS_PER_DEPT_YEAR} Department representatives per year already appointed for this department"
            )

    rep = StudentRepresentative(
        student_roll_no=body.student_roll_no,
        department_id=student.department_id,
        year=student.year,
        scope=body.scope,
        appointed_by_id=current_authority_id,
        is_active=True,
    )
    db.add(rep)

    # Notify the student
    from src.database.models import Notification
    db.add(Notification(
        recipient_type="Student",
        recipient_id=body.student_roll_no,
        complaint_id=None,
        notification_type="representative_appointed",
        message=(
            f"You have been appointed as a {body.scope} Student Representative! "
            f"You can now create petitions on behalf of your peers (1 per week)."
        ),
    ))

    await db.commit()

    logger.info(f"Student {body.student_roll_no} appointed as {body.scope} representative by authority {current_authority_id}")
    return {
        "success": True,
        "id": rep.id,
        "student_roll_no": rep.student_roll_no,
        "department_id": rep.department_id,
        "year": rep.year,
        "scope": rep.scope,
    }


@router.delete(
    "/representatives/{rep_id}",
    summary="Remove student representative",
)
async def remove_representative(
    rep_id: int,
    current_authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a representative. Admin can deactivate any. HOD can deactivate Dept reps in their dept. Warden can deactivate Hostel reps."""
    from src.database.models import StudentRepresentative, Notification

    ctx = await _get_rep_authority_context(current_authority_id, db)

    q = select(StudentRepresentative).where(StudentRepresentative.id == rep_id)
    result = await db.execute(q)
    rep = result.scalar_one_or_none()
    if not rep:
        raise HTTPException(status_code=404, detail="Representative not found")
    if not rep.is_active:
        return {"success": True, "message": "Representative was already deactivated"}

    # Permission check for non-admin
    if not ctx["is_admin"]:
        if ctx["is_hod"]:
            if rep.scope != "Department" or rep.department_id != ctx["authority"].department_id:
                raise HTTPException(status_code=403, detail="HOD can only remove Department representatives from their department")
        elif ctx["is_warden"]:
            if rep.scope != "Hostel":
                raise HTTPException(status_code=403, detail="Warden can only remove Hostel representatives")

    rep.is_active = False
    rep.removed_at = datetime.now(timezone.utc)

    # Notify the student
    db.add(Notification(
        recipient_type="Student",
        recipient_id=rep.student_roll_no,
        complaint_id=None,
        notification_type="representative_removed",
        message=(
            f"Your {rep.scope} Student Representative role has been revoked. "
            f"You can no longer create new petitions."
        ),
    ))

    await db.commit()
    logger.info(f"Representative {rep_id} (student {rep.student_roll_no}) removed by authority {current_authority_id}")
    return {"success": True, "message": "Representative deactivated"}


@router.get(
    "/representatives/capacity",
    summary="Show representative slots per department per year",
)
async def get_representative_capacity(
    current_authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db),
):
    """Show how many representative slots are used/available per department per year."""
    from sqlalchemy import and_
    from src.database.models import StudentRepresentative, Department

    # Get all departments
    dept_q = select(Department).where(Department.is_active == True).order_by(Department.code)
    dept_result = await db.execute(dept_q)
    departments = dept_result.scalars().all()

    # Get active rep counts grouped by dept + year + scope
    count_q = (
        select(
            StudentRepresentative.department_id,
            StudentRepresentative.year,
            StudentRepresentative.scope,
            func.count().label("count"),
        )
        .where(StudentRepresentative.is_active == True)
        .group_by(StudentRepresentative.department_id, StudentRepresentative.year, StudentRepresentative.scope)
    )
    count_result = await db.execute(count_q)
    counts = {}
    for row in count_result.fetchall():
        key = (row[0], row[1], row[2])  # dept_id, year, scope
        counts[key] = row[3]

    capacity = []
    for dept in departments:
        # Determine max years (5 for CSE M.Tech, 4 for others)
        max_years = 5 if dept.code == "CSE" else 4
        dept_data = {
            "department_id": dept.id,
            "department_code": dept.code,
            "department_name": dept.name,
            "max_years": max_years,
            "years": [],
        }
        for year in range(1, max_years + 1):
            dept_used = counts.get((dept.id, year, "Department"), 0)
            hostel_used = counts.get((dept.id, year, "Hostel"), 0)
            dept_data["years"].append({
                "year": year,
                "department_reps": {"used": dept_used, "max": MAX_REPS_PER_DEPT_YEAR},
                "hostel_reps": {"used": hostel_used, "max": MAX_REPS_PER_DEPT_YEAR},
            })
        capacity.append(dept_data)

    return {"capacity": capacity}


# ==================== SYSTEM SETTINGS ====================


class UpdateSettingBody(BaseModel):
    value: str = Field(..., min_length=1, max_length=500, description="New value for the setting")


# Known settings with their validation rules and descriptions
_KNOWN_SETTINGS = {
    "petition_cooldown_days": {
        "description": "Minimum days between petition creations per representative (0 = no limit)",
        "type": "int",
        "min": 0,
        "max": 365,
    },
}


@router.get(
    "/settings",
    summary="Get system settings",
    description="Returns all configurable system settings. Admin only.",
)
async def get_system_settings(
    authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Return all system settings with metadata."""
    from src.database.models import SystemSetting
    result = await db.execute(select(SystemSetting))
    settings = result.scalars().all()
    items = []
    for s in settings:
        meta = _KNOWN_SETTINGS.get(s.key, {})
        items.append({
            "key": s.key,
            "value": s.value,
            "description": s.description or meta.get("description", ""),
            "type": meta.get("type", "string"),
            "min": meta.get("min"),
            "max": meta.get("max"),
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        })
    return {"settings": items}


@router.put(
    "/settings/{key}",
    summary="Update a system setting",
    description="Update a system setting value. Admin only.",
)
async def update_system_setting(
    key: str,
    body: UpdateSettingBody,
    authority_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update or create a system setting."""
    from src.database.models import SystemSetting

    if key not in _KNOWN_SETTINGS:
        raise HTTPException(status_code=400, detail=f"Unknown setting key: {key}. Known keys: {list(_KNOWN_SETTINGS.keys())}")

    meta = _KNOWN_SETTINGS[key]

    # Type validation
    if meta.get("type") == "int":
        try:
            int_val = int(body.value)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Setting '{key}' must be an integer")
        if "min" in meta and int_val < meta["min"]:
            raise HTTPException(status_code=400, detail=f"Setting '{key}' must be >= {meta['min']}")
        if "max" in meta and int_val > meta["max"]:
            raise HTTPException(status_code=400, detail=f"Setting '{key}' must be <= {meta['max']}")
        value = str(int_val)
    else:
        value = body.value.strip()

    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = value
        setting.updated_by_id = authority_id
        setting.updated_at = datetime.now(timezone.utc)
    else:
        description = meta.get("description", "")
        db.add(SystemSetting(key=key, value=value, description=description, updated_by_id=authority_id))

    await db.commit()
    logger.info(f"Admin {authority_id} updated system setting '{key}' = '{value}'")
    return {"success": True, "key": key, "value": value}


# ==================== ADMIN NOTIFICATIONS ====================


@router.get(
    "/notifications/unread-count",
    summary="Get unread notification count for the current admin",
)
async def get_admin_notifications_unread_count(
    current_admin_id: int = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Returns the number of unread notifications for the authenticated admin."""
    from src.repositories.notification_repo import NotificationRepository
    notification_repo = NotificationRepository(db)
    unread_count = await notification_repo.count_unread(
        recipient_id=str(current_admin_id),
        recipient_type="Authority"
    )
    return {"unread_count": unread_count}


__all__ = ["router"]
