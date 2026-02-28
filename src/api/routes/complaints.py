"""
Complaint API endpoints.

CRUD operations, voting, filtering, image upload, verification, tracking.

✅ FIXED: Uses Complaint.status_updates relationship instead of non-existent StatusUpdateRepository
✅ FIXED: Binary image upload using ComplaintService
✅ ADDED: Image retrieval, verification endpoints
✅ ADDED: Vote status, status history, timeline endpoints
✅ ADDED: Spam flagging, complaint updates endpoints
✅ FIXED: Visibility checking with proper permissions
✅ FIXED: Count queries instead of fetching all records
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_db,
    get_current_student,
    get_current_authority,
    get_complaint_with_ownership,
    get_complaint_with_visibility,
    ComplaintFilters,
)
from src.schemas.complaint import (
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintResponse,
    ComplaintDetailResponse,
    ComplaintSubmitResponse,
    ComplaintListResponse,
    ComplaintFilter,
    SpamFlag,
    ImageUploadResponse,
)
from src.schemas.vote import VoteCreate, VoteResponse
from src.schemas.common import SuccessResponse
from src.services.complaint_service import ComplaintService
from src.services.vote_service import VoteService
from src.services.image_verification import image_verification_service
from src.utils.exceptions import ComplaintNotFoundError, to_http_exception, InvalidFileTypeError, FileTooLargeError, FileUploadError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/complaints", tags=["Complaints"])


# ==================== CREATE COMPLAINT ====================

@router.post(
    "/submit",
    response_model=ComplaintSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit complaint (fully AI-driven)",
    description="Submit a new complaint - category and department are automatically determined by AI"
)
async def create_complaint(
    original_text: str = Form(..., min_length=10, max_length=2000, description="Complaint text"),
    visibility: str = Form(default="Public", description="Visibility level (Public or Private)"),
    image: Optional[UploadFile] = File(None, description="Optional complaint image"),
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ FULLY AI-DRIVEN: Submit a new complaint without selecting category.

    The system automatically:
    - Analyzes complaint text using AI to determine category
    - Detects target department from complaint content
    - Routes cross-department complaints correctly
    - Checks for spam/abusive content (rejected if spam)
    - Determines if image is REQUIRED based on complaint type
    - Rephrases text for professionalism
    - Routes to appropriate authority
    - Prioritizes based on content
    - Verifies image if provided

    **Important**:
    - NO category selection required - AI determines it
    - Spam/abusive complaints are rejected outright (HTTP 400)
    - Some complaints require images based on AI analysis
    - If image is required but not provided, complaint is rejected (HTTP 400)
    - Visibility options: "Public" or "Private" only

    **Multipart form data required if image is uploaded**
    """
    try:
        # Validate visibility before any processing
        if visibility not in ("Public", "Private"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid visibility '{visibility}'. Must be 'Public' or 'Private'."
            )

        service = ComplaintService(db)

        # ✅ UPDATED: No category_id parameter - fully AI-driven
        result = await service.create_complaint(
            student_roll_no=roll_no,
            original_text=original_text,
            visibility=visibility,
            image_file=image
        )

        return ComplaintSubmitResponse(**result)

    except ValueError as e:
        # ValueError at this point means a hard block (image required but missing, or blacklisted)
        error_message = str(e)
        logger.warning(f"Complaint rejected for {roll_no}: {error_message}")

        is_missing_image = "image" in error_message.lower() and "required" in error_message.lower()

        if is_missing_image:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": "Image required",
                    "reason": error_message,
                    "image_required": True
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

    except Exception as e:
        logger.error(f"Complaint creation error: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create complaint: {str(e)}"
        )


# ==================== GET COMPLAINTS ====================

@router.get(
    "/public-feed",
    response_model=ComplaintListResponse,
    summary="Get public complaint feed",
    description="Get public complaints with visibility filtering"
)
async def get_complaints(
    roll_no: str = Depends(get_current_student),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get public complaint feed filtered by visibility rules."""
    from src.repositories.student_repo import StudentRepository
    from src.repositories.complaint_repo import ComplaintRepository
    from sqlalchemy import select, func, and_, or_
    from src.database.models import Complaint

    # Get student info for filtering
    student_repo = StudentRepository(db)
    student = await student_repo.get_with_department(roll_no)

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Get paginated complaints from repo (returns ORM objects with eager-loaded category)
    complaint_repo = ComplaintRepository(db)
    complaints = await complaint_repo.get_public_feed(
        student_stay_type=student.stay_type,
        student_department_id=student.department_id,
        student_gender=student.gender,
        skip=skip,
        limit=limit
    )

    # Count using same visibility logic (✅ UPDATED: Only Public)
    # Bug 4 fix: Exclude Spam from the count as well.
    from src.database.models import ComplaintCategory
    count_conditions = [
        Complaint.visibility == "Public",
        Complaint.status != "Closed",
        Complaint.status != "Spam",
        Complaint.is_marked_as_spam == False,
    ]

    # Get hostel category IDs for filtering
    mens_hostel_query = select(ComplaintCategory.id).where(ComplaintCategory.name == "Men's Hostel")
    womens_hostel_query = select(ComplaintCategory.id).where(ComplaintCategory.name == "Women's Hostel")
    general_query = select(ComplaintCategory.id).where(ComplaintCategory.name == "General")
    disciplinary_query = select(ComplaintCategory.id).where(ComplaintCategory.name == "Disciplinary Committee")

    mens_hostel_result = await db.execute(mens_hostel_query)
    womens_hostel_result = await db.execute(womens_hostel_query)
    general_result = await db.execute(general_query)
    disciplinary_result = await db.execute(disciplinary_query)

    mens_hostel_id = mens_hostel_result.scalar()
    womens_hostel_id = womens_hostel_result.scalar()
    general_id = general_result.scalar()
    disciplinary_id = disciplinary_result.scalar()

    # Hide hostel complaints based on stay type and gender
    if student.stay_type == "Day Scholar":
        if mens_hostel_id:
            count_conditions.append(Complaint.category_id != mens_hostel_id)
        if womens_hostel_id:
            count_conditions.append(Complaint.category_id != womens_hostel_id)
    else:
        # Hostel students: filter by gender
        if student.gender == "Male" and womens_hostel_id:
            count_conditions.append(Complaint.category_id != womens_hostel_id)
        elif student.gender == "Female" and mens_hostel_id:
            count_conditions.append(Complaint.category_id != mens_hostel_id)

    # ✅ BUG 1 FIX: Inter-department filtering.
    # General and Disciplinary visible to all students.
    # Department complaints: only same-dept students.
    # Hostel complaints: visible to ALL same-gender hostel students (NO dept restriction).
    inter_dept_conditions = [
        Complaint.complaint_department_id == student.department_id
    ]
    if general_id:
        inter_dept_conditions.append(Complaint.category_id == general_id)
    if disciplinary_id:
        inter_dept_conditions.append(Complaint.category_id == disciplinary_id)

    # Hostel students can see hostel complaints regardless of department
    if student.stay_type != "Day Scholar":
        if student.gender == "Male" and mens_hostel_id:
            inter_dept_conditions.append(Complaint.category_id == mens_hostel_id)
        elif student.gender == "Female" and womens_hostel_id:
            inter_dept_conditions.append(Complaint.category_id == womens_hostel_id)
        elif student.gender not in ("Male", "Female"):
            if mens_hostel_id:
                inter_dept_conditions.append(Complaint.category_id == mens_hostel_id)
            if womens_hostel_id:
                inter_dept_conditions.append(Complaint.category_id == womens_hostel_id)

    count_conditions.append(or_(*inter_dept_conditions))

    count_query = select(func.count()).select_from(Complaint).where(and_(*count_conditions))
    result = await db.execute(count_query)
    total = result.scalar() or 0

    return ComplaintListResponse(
        complaints=[ComplaintResponse.model_validate(c) for c in complaints],
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit
    )


@router.get(
    "/{complaint_id}",
    response_model=ComplaintDetailResponse,
    summary="Get complaint details",
    description="Get detailed information about a specific complaint"
)
async def get_complaint(
    complaint = Depends(get_complaint_with_visibility),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ FIXED: Get detailed complaint information with visibility check.

    Visibility is automatically checked by the dependency.
    """
    # Convert status_updates ORM objects to dicts before validation
    status_updates_dicts = None
    if hasattr(complaint, 'status_updates') and complaint.status_updates:
        status_updates_dicts = [
            {
                "old_status": su.old_status,
                "new_status": su.new_status,
                "reason": su.reason,
                "updated_by": su.updated_by,
                "updated_at": su.updated_at.isoformat() if su.updated_at else None,
            }
            for su in complaint.status_updates
        ]

    # Build base response from ORM, then override status_updates
    data = ComplaintResponse.model_validate(complaint).model_dump()
    data["status_updates"] = status_updates_dicts
    data["comments_count"] = len(complaint.comments) if hasattr(complaint, 'comments') and complaint.comments else 0
    data["vote_count"] = (complaint.upvotes or 0) - (complaint.downvotes or 0)
    if hasattr(complaint, 'student') and complaint.student:
        dept_id = getattr(complaint.student, 'department_id', None)
        data["student_department"] = str(dept_id) if dept_id is not None else None
        data["student_gender"] = getattr(complaint.student, 'gender', None)
        data["student_stay_type"] = getattr(complaint.student, 'stay_type', None)
        data["student_year"] = getattr(complaint.student, 'year', None)
    data["complaint_department_id"] = complaint.complaint_department_id
    data["is_cross_department"] = getattr(complaint, 'is_cross_department', False)
    data["image_filename"] = complaint.image_filename
    data["image_size"] = complaint.image_size
    data["image_mimetype"] = complaint.image_mimetype

    return ComplaintDetailResponse(**data)


# ==================== VOTING ====================

# Sentinel string used by VoteService to identify own-complaint vote attempts.
_OWN_COMPLAINT_VOTE_ERROR = "Cannot vote on your own complaint"


@router.post(
    "/{complaint_id}/vote",
    response_model=VoteResponse,
    summary="Vote on complaint",
    description="Upvote or downvote a complaint"
)
async def vote_on_complaint(
    complaint_id: UUID,
    data: VoteCreate,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Vote on a complaint.

    - **vote_type**: Upvote or Downvote

    Voting affects complaint priority and visibility.

    Bug 5 fix: Ownership check happens before any DB write inside VoteService.
    If the logged-in student owns the complaint, returns HTTP 403 with
    {"error": "You cannot vote on your own complaint"} so the frontend can
    show the message only to the complaint owner.
    """
    # Bug 5 fix: Check complaint ownership BEFORE delegating to VoteService,
    # so we can return the correct 403 with {"error": ...} without any DB write.
    from src.repositories.complaint_repo import ComplaintRepository
    complaint_repo = ComplaintRepository(db)
    complaint = await complaint_repo.get(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    if complaint.student_roll_no == roll_no:
        # Return 403 with "error" key (not "detail") so the frontend can
        # distinguish this from other 403 errors.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "You cannot vote on your own complaint"}
        )

    try:
        service = VoteService(db)

        result = await service.add_vote(
            complaint_id=complaint_id,
            student_roll_no=roll_no,
            vote_type=data.vote_type
        )

        return VoteResponse(
            complaint_id=complaint_id,
            upvotes=result["upvotes"],
            downvotes=result["downvotes"],
            priority_score=result["priority_score"],
            priority=result["priority"],
            user_vote=data.vote_type
        )

    except Exception as e:
        logger.error(f"Vote error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{complaint_id}/vote",
    response_model=VoteResponse,
    summary="Remove vote",
    description="Remove your vote from a complaint"
)
async def remove_vote(
    complaint_id: UUID,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Remove vote from complaint. Returns updated vote counts so the UI can sync."""
    try:
        service = VoteService(db)

        result = await service.remove_vote(
            complaint_id=complaint_id,
            student_roll_no=roll_no
        )

        return VoteResponse(
            complaint_id=complaint_id,
            upvotes=result["upvotes"],
            downvotes=result["downvotes"],
            priority_score=result["priority_score"],
            priority=result["priority"],
            user_vote=None
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{complaint_id}/my-vote",
    summary="Get my vote status",
    description="Check if current user voted and their vote type"
)
async def get_my_vote(
    complaint_id: UUID,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get current user's vote status on complaint.
    
    Returns vote type if voted, null otherwise.
    """
    from src.repositories.vote_repo import VoteRepository
    
    vote_repo = VoteRepository(db)
    
    # Get vote
    from sqlalchemy import select, and_
    from src.database.models import Vote
    
    query = select(Vote).where(
        and_(
            Vote.complaint_id == complaint_id,
            Vote.student_roll_no == roll_no
        )
    )
    result = await db.execute(query)
    vote = result.scalar_one_or_none()
    
    return {
        "complaint_id": str(complaint_id),
        "has_voted": vote is not None,
        "vote_type": vote.vote_type if vote else None
    }


# ==================== IMAGE UPLOAD & VERIFICATION ====================

@router.post(
    "/{complaint_id}/upload-image",
    response_model=ImageUploadResponse,
    summary="Upload complaint image",
    description="Upload supporting image for complaint (binary storage)"
)
async def upload_complaint_image(
    complaint_id: UUID,
    file: UploadFile = File(...),
    complaint = Depends(get_complaint_with_ownership),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ FIXED: Upload image for complaint using binary storage.
    
    - **file**: Image file (JPEG, PNG, max 5MB)
    
    Image is stored in database as binary data.
    Ownership is automatically validated by dependency.
    """
    try:
        service = ComplaintService(db)
        
        # ✅ FIXED: Use service method for binary storage
        result = await service.upload_complaint_image(
            complaint_id=complaint_id,
            student_roll_no=complaint.student_roll_no,
            image_file=file
        )
        
        logger.info(f"Image uploaded for complaint {complaint_id}")
        
        return ImageUploadResponse(**result)
        
    except HTTPException:
        raise
    except (InvalidFileTypeError, FileTooLargeError, FileUploadError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Image upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image upload failed: {str(e)}"
        )


async def get_complaint_for_image(
    complaint_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Flexible visibility dependency for image access.
    Accepts student, authority, AND admin tokens — unlike get_complaint_with_visibility
    which only accepts student tokens.
    """
    from src.services.auth_service import AuthService
    from src.repositories.complaint_repo import ComplaintRepository

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    auth_svc = AuthService()
    payload = auth_svc.decode_token(auth_header[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    role = (payload.get("role") or "").lower()
    complaint_repo = ComplaintRepository(db)
    complaint = await complaint_repo.get(complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Admin and authority can see any complaint image
    if role in ("admin", "authority"):
        return complaint

    # Student: enforce visibility rules
    from src.repositories.student_repo import StudentRepository
    from src.api.dependencies import check_complaint_visibility

    roll_no = payload.get("sub", "")
    student_repo = StudentRepository(db)
    student = await student_repo.get_with_department(roll_no)
    can_view = await check_complaint_visibility(complaint, student)
    if not can_view:
        raise HTTPException(status_code=403, detail="You don't have permission to view this image")
    return complaint


@router.get(
    "/{complaint_id}/image",
    summary="Get complaint image",
    description="Retrieve complaint image (binary data)",
    responses={
        200: {
            "content": {"image/jpeg": {}, "image/png": {}},
            "description": "Returns the image file"
        }
    }
)
async def get_complaint_image(
    complaint_id: UUID,
    thumbnail: bool = Query(False, description="Return thumbnail (200x200) instead of full image"),
    complaint = Depends(get_complaint_for_image),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get complaint image as binary data.
    
    - **thumbnail**: If true, returns optimized 200x200 thumbnail
    
    Returns image with appropriate MIME type.
    """
    # Check if complaint has image
    if not complaint.image_data and not complaint.thumbnail_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No image attached to this complaint"
        )
    
    # Return thumbnail or full image
    if thumbnail and complaint.thumbnail_data:
        image_data = complaint.thumbnail_data
        mime_type = complaint.image_mimetype or "image/jpeg"
    elif complaint.image_data:
        image_data = complaint.image_data
        mime_type = complaint.image_mimetype or "image/jpeg"
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    return Response(
        content=image_data,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{complaint.image_filename or "image.jpg"}"'
        }
    )


@router.post(
    "/{complaint_id}/verify-image",
    response_model=ImageUploadResponse,
    summary="Verify complaint image",
    description="Trigger image verification using Groq Vision API"
)
async def verify_complaint_image(
    complaint_id: UUID,
    complaint = Depends(get_complaint_with_ownership),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Trigger image verification using Groq Vision API.
    
    Uses LLM to verify if image is relevant to the complaint.
    Only complaint owner can trigger verification.
    """
    # Check if complaint has image
    if not complaint.image_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image attached to this complaint"
        )
    
    # Check if already verified
    if complaint.image_verified:
        return ImageUploadResponse(
            complaint_id=str(complaint_id),
            has_image=True,
            image_verified=True,
            verification_status=complaint.image_verification_status,
            verification_message="Image already verified"
        )

    try:
        # Trigger verification using binary image data from the complaint
        result = await image_verification_service.verify_image_from_bytes(
            db=db,
            complaint_id=complaint_id,
            complaint_text=complaint.rephrased_text or complaint.original_text,
            image_bytes=complaint.image_data,
            mimetype=complaint.image_mimetype or "image/jpeg"
        )

        # Update complaint with verification results
        complaint.image_verified = result["is_relevant"]
        complaint.image_verification_status = result["status"]
        await db.commit()

        return ImageUploadResponse(
            complaint_id=str(complaint_id),
            has_image=True,
            image_verified=result["is_relevant"],
            verification_status=result["status"],
            verification_message=result.get("explanation", "Image verification complete")
        )

    except Exception as e:
        logger.error(f"Image verification error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image verification failed: {str(e)}"
        )


# ==================== STATUS TRACKING ====================

@router.get(
    "/{complaint_id}/status-history",
    summary="Get status history",
    description="Get timeline of status changes for complaint"
)
async def get_status_history(
    complaint_id: UUID,
    complaint = Depends(get_complaint_with_visibility),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get status change history for complaint.
    
    Returns timeline of all status changes with timestamps.
    Uses Complaint.status_updates relationship.
    """
    # ✅ FIXED: Use the complaint relationship instead of StatusUpdateRepository
    from src.repositories.complaint_repo import ComplaintRepository
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from src.database.models import Complaint
    
    # Reload complaint with status_updates and their authorities
    from src.database.models import StatusUpdate
    query = (
        select(Complaint)
        .options(
            selectinload(Complaint.status_updates).selectinload(StatusUpdate.updated_by_authority)
        )
        .where(Complaint.id == complaint_id)
    )
    result = await db.execute(query)
    complaint_with_updates = result.scalar_one_or_none()
    
    if not complaint_with_updates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    # Build status history
    status_updates = []
    for update in sorted(complaint_with_updates.status_updates, key=lambda x: x.updated_at):
        status_updates.append({
            "old_status": update.old_status,
            "new_status": update.new_status,
            "reason": update.reason,
            "updated_by": update.updated_by_authority.name if update.updated_by_authority else "System",
            "updated_at": update.updated_at.isoformat()
        })
    
    return {
        "complaint_id": str(complaint_id),
        "current_status": complaint_with_updates.status,
        "status_updates": status_updates
    }


@router.get(
    "/{complaint_id}/timeline",
    summary="Get complaint timeline",
    description="Get complete timeline including submission, status changes, updates, resolution"
)
async def get_complaint_timeline(
    complaint_id: UUID,
    complaint = Depends(get_complaint_with_visibility),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Get complete complaint timeline.
    
    Includes:
    - Submission
    - Status changes
    - Authority assignments
    - Resolution
    """
    # ✅ FIXED: Use complaint relationship
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from src.database.models import Complaint
    
    # Reload with relationships
    query = (
        select(Complaint)
        .options(
            selectinload(Complaint.status_updates),
            selectinload(Complaint.student),
            selectinload(Complaint.assigned_authority)
        )
        .where(Complaint.id == complaint_id)
    )
    result = await db.execute(query)
    complaint_full = result.scalar_one_or_none()
    
    if not complaint_full:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    # Build timeline
    timeline = []
    
    # Submission
    timeline.append({
        "event": "Complaint Submitted",
        "timestamp": complaint_full.submitted_at.isoformat(),
        "description": f"Complaint raised by {complaint_full.student.name}"
    })
    
    # Status changes
    for update in sorted(complaint_full.status_updates, key=lambda x: x.updated_at):
        timeline.append({
            "event": "Status Changed",
            "timestamp": update.updated_at.isoformat(),
            "description": f"Status changed from {update.old_status} to {update.new_status}",
            "reason": update.reason,
            "updated_by": update.updated_by_authority.name if update.updated_by_authority else "System"
        })
    
    # Resolution
    if complaint_full.resolved_at:
        timeline.append({
            "event": "Complaint Resolved",
            "timestamp": complaint_full.resolved_at.isoformat(),
            "description": "Complaint marked as resolved"
        })
    
    return {
        "complaint_id": str(complaint_id),
        "timeline": timeline
    }


# ==================== SPAM MANAGEMENT ====================

@router.post(
    "/{complaint_id}/flag-spam",
    response_model=SuccessResponse,
    summary="Flag as spam",
    description="Flag complaint as spam (Authority only)"
)
async def flag_as_spam(
    complaint_id: UUID,
    reason: str = Query(..., description="Reason for flagging as spam"),
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Flag complaint as spam (Authority only).
    
    - **reason**: Reason for flagging
    """
    from src.repositories.complaint_repo import ComplaintRepository
    from datetime import datetime, timezone
    
    complaint_repo = ComplaintRepository(db)
    complaint = await complaint_repo.get(complaint_id)
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    # Update complaint
    complaint.is_marked_as_spam = True
    complaint.spam_reason = reason
    complaint.spam_flagged_by = authority_id
    complaint.spam_flagged_at = datetime.now(timezone.utc)
    complaint.status = "Spam"
    complaint.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Notify the student that their complaint was flagged as spam
    try:
        from src.services.notification_service import notification_service
        await notification_service.create_notification(
            db=db,
            recipient_type="Student",
            recipient_id=complaint.student_roll_no,
            complaint_id=complaint_id,
            notification_type="complaint_spam",
            message=f"Your complaint has been reviewed and marked as spam. Reason: {reason}",
        )
    except Exception as _notif_err:
        logger.warning(f"Failed to send spam notification to student: {_notif_err}")

    logger.info(f"Complaint {complaint_id} flagged as spam by authority {authority_id}")

    return SuccessResponse(
        success=True,
        message="Complaint flagged as spam"
    )


@router.post(
    "/{complaint_id}/unflag-spam",
    response_model=SuccessResponse,
    summary="Remove spam flag",
    description="Remove spam flag from complaint (Authority only)"
)
async def unflag_spam(
    complaint_id: UUID,
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ NEW: Remove spam flag from complaint (Authority only).
    """
    from src.repositories.complaint_repo import ComplaintRepository
    from datetime import datetime, timezone
    
    complaint_repo = ComplaintRepository(db)
    complaint = await complaint_repo.get(complaint_id)
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    
    # Update complaint
    complaint.is_marked_as_spam = False
    complaint.spam_reason = None
    complaint.spam_flagged_by = None
    complaint.spam_flagged_at = None
    complaint.status = "Raised"
    complaint.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    logger.info(f"Spam flag removed from complaint {complaint_id} by authority {authority_id}")
    
    return SuccessResponse(
        success=True,
        message="Spam flag removed"
    )


# ==================== SPAM APPEAL ====================

@router.post(
    "/{complaint_id}/appeal-spam",
    response_model=SuccessResponse,
    summary="Dispute spam classification",
    description="Student disputes their complaint being marked as spam"
)
async def appeal_spam(
    complaint_id: UUID,
    reason: Optional[str] = None,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Student disputes spam classification. Notifies Admin and category authority for review.
    Only the complaint owner can appeal, and only if complaint is spam.
    """
    from src.repositories.complaint_repo import ComplaintRepository
    from src.repositories.authority_repo import AuthorityRepository
    from src.services.notification_service import notification_service

    complaint_repo = ComplaintRepository(db)
    complaint = await complaint_repo.get(complaint_id)

    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    if complaint.student_roll_no != roll_no:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your complaint")

    if not complaint.is_marked_as_spam and complaint.status != "Spam":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Complaint is not marked as spam")

    appeal_text = reason or "No reason provided"
    preview = (complaint.original_text or "")[:100]
    msg = (
        f"Spam dispute from student {roll_no}: "
        f"'{preview}{'...' if len(complaint.original_text or '') > 100 else ''}' "
        f"— Reason: {appeal_text}"
    )

    # Notify all Admin users
    try:
        authority_repo = AuthorityRepository(db)
        admins = await authority_repo.get_by_type("Admin")
        for admin in admins:
            await notification_service.create_notification(
                db=db,
                recipient_type="Authority",
                recipient_id=str(admin.id),
                complaint_id=complaint_id,
                notification_type="spam_appeal",
                message=msg
            )
    except Exception as e:
        logger.warning(f"Failed to notify admin of spam appeal: {e}")

    # Notify assigned authority if exists
    if complaint.assigned_authority_id:
        try:
            await notification_service.create_notification(
                db=db,
                recipient_type="Authority",
                recipient_id=str(complaint.assigned_authority_id),
                complaint_id=complaint_id,
                notification_type="spam_appeal",
                message=msg
            )
        except Exception as e:
            logger.warning(f"Failed to notify authority of spam appeal: {e}")

    logger.info(f"Spam appeal submitted for complaint {complaint_id} by {roll_no}")

    return SuccessResponse(
        success=True,
        message="Your dispute has been submitted. An admin will review it shortly."
    )


# ==================== FILTER & SEARCH ====================

@router.get(
    "/filter/advanced",
    response_model=ComplaintListResponse,
    summary="Advanced complaint filtering",
    description="Filter complaints by multiple criteria"
)
async def filter_complaints(
    filters: ComplaintFilters = Depends(),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ IMPROVED: Filter complaints with advanced criteria.
    
    Supports filtering by:
    - Status
    - Priority
    - Category
    - Department
    - Date range
    - Image presence
    - Verification status
    """
    from src.repositories.complaint_repo import ComplaintRepository
    from sqlalchemy import select, and_, func
    from src.database.models import Complaint
    from src.repositories.student_repo import StudentRepository
    
    complaint_repo = ComplaintRepository(db)
    student_repo = StudentRepository(db)
    service = ComplaintService(db)
    
    # Get student info
    student = await student_repo.get_with_department(roll_no)
    
    # Build filter conditions
    filter_dict = filters.to_dict()
    conditions = []
    
    # Visibility base conditions
    conditions.append(Complaint.visibility.in_(["Public", "Department"]))
    conditions.append(Complaint.status != "Closed")
    
    if student.stay_type == "Day Scholar":
        conditions.append(Complaint.category_id != 1)
    
    # Apply filters
    if filter_dict.get("status"):
        conditions.append(Complaint.status == filter_dict["status"])
    if filter_dict.get("priority"):
        conditions.append(Complaint.priority == filter_dict["priority"])
    if filter_dict.get("category_id"):
        conditions.append(Complaint.category_id == filter_dict["category_id"])
    if filter_dict.get("has_image") is not None:
        if filter_dict["has_image"]:
            conditions.append(Complaint.image_data.isnot(None))
        else:
            conditions.append(Complaint.image_data.is_(None))
    if filter_dict.get("is_verified") is not None:
        conditions.append(Complaint.image_verified == filter_dict["is_verified"])
    
    # Query
    query = (
        select(Complaint)
        .where(and_(*conditions))
        .order_by(Complaint.priority_score.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await db.execute(query)
    complaints = result.scalars().all()
    
    # Count
    count_query = select(func.count()).where(and_(*conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    return ComplaintListResponse(
        complaints=[ComplaintResponse.model_validate(c) for c in complaints],
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        total_pages=(total + limit - 1) // limit
    )


__all__ = ["router"]
