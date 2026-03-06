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
    get_current_user,
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
    SatisfactionRatingRequest,
    SatisfactionRatingResponse,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    DuplicateCandidate,
    ChangelogEntry,
    ChangelogResponse,
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
    is_anonymous: bool = Form(default=False, description="Hide your identity from other students"),
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
            image_file=image,
            is_anonymous=is_anonymous,
        )

        # Auto-merge check: if 10+ similar complaints exist, LLM merges them
        try:
            if result.get("id") and visibility == "Public":
                from src.database.models import Complaint as ComplaintModel
                complaint_obj = await db.get(ComplaintModel, result["id"])
                if complaint_obj:
                    await _check_and_merge_duplicates(db, complaint_obj)
        except Exception as merge_err:
            logger.warning(f"Auto-merge check failed (non-fatal): {merge_err}")

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
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    sort_by: Optional[str] = Query("hot", description="Sort order: hot, new, top"),
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
        student_roll_no=student.roll_no,
        skip=skip,
        limit=limit,
        category_id=category_id,
        sort_by=sort_by or "hot",
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

    # Inter-department filtering (mirrors get_public_feed logic):
    # 1. Same department, 2. Cross-dept (both sides), 3. Self, 4. General, 5. Disciplinary, 6. Hostel
    from src.database.models import Student as StudentModel
    inter_dept_conditions = [
        Complaint.complaint_department_id == student.department_id,
    ]

    # Cross-dept: show to submitter's department too
    cross_dept_sq = (
        select(Complaint.id)
        .join(StudentModel, Complaint.student_roll_no == StudentModel.roll_no)
        .where(
            and_(
                Complaint.is_cross_department == True,
                StudentModel.department_id == student.department_id
            )
        )
        .scalar_subquery()
    )
    inter_dept_conditions.append(Complaint.id.in_(cross_dept_sq))

    # Self-visibility
    inter_dept_conditions.append(Complaint.student_roll_no == student.roll_no)

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

    # Apply category filter to count as well
    if category_id is not None:
        count_conditions.append(Complaint.category_id == category_id)

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


# ==================== CHANGELOG ====================

@router.get(
    "/changelog",
    response_model=ChangelogResponse,
    summary="What's Fixed — public resolved complaints",
    description="Paginated list of publicly resolved complaints with resolution notes"
)
async def get_changelog(
    _: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Public 'What's Fixed' / 'Wins' feed — popular resolved complaints only.

    Popularity score = upvotes*4 + satisfaction_rating*8 + min(view_count//5, 30).
    Only complaints with score >= 5 OR upvotes >= 2 are shown.
    Ordered by popularity score descending, then resolved_at.
    """
    from src.database.models import Complaint, ComplaintCategory
    from sqlalchemy import select, func, and_, or_, case
    from sqlalchemy.orm import selectinload

    # Popularity score expression
    score_expr = (
        func.coalesce(Complaint.upvotes, 0) * 4
        + func.coalesce(Complaint.satisfaction_rating, 0) * 8
        + func.least(func.coalesce(Complaint.view_count, 0) / 5, 30)
    )

    base_conditions = [
        Complaint.visibility == "Public",
        Complaint.status.in_(["Resolved", "Closed"]),
        Complaint.is_marked_as_spam == False,
        # Only popular complaints: score >= 5 OR at least 2 upvotes
        or_(
            score_expr >= 5,
            func.coalesce(Complaint.upvotes, 0) >= 2,
        ),
    ]

    # Total count
    count_query = select(func.count()).select_from(Complaint).where(and_(*base_conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    query = (
        select(Complaint)
        .options(selectinload(Complaint.category))
        .where(and_(*base_conditions))
        .order_by(score_expr.desc(), Complaint.resolved_at.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    complaints = result.scalars().all()

    entries = [
        ChangelogEntry(
            id=c.id,
            rephrased_text=(c.rephrased_text or c.original_text or "")[:400],
            resolution_note=c.resolution_note,
            category_name=c.category.name if c.category else None,
            resolved_at=c.resolved_at,
            upvotes=c.upvotes or 0,
            satisfaction_avg=float(c.satisfaction_rating) if c.satisfaction_rating else None,
        )
        for c in complaints
    ]

    return ChangelogResponse(
        entries=entries,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
    )


@router.get(
    "/{complaint_id}",
    response_model=ComplaintDetailResponse,
    summary="Get complaint details",
    description="Get detailed information about a specific complaint"
)
async def get_complaint(
    complaint = Depends(get_complaint_with_visibility),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    ✅ FIXED: Get detailed complaint information with visibility check.

    Visibility is automatically checked by the dependency.
    """
    # Increment view_count for student viewers (fire-and-forget, never blocks response)
    if current_user.get("role") == "student":
        try:
            from sqlalchemy import update as sa_update
            from src.database.models import Complaint as ComplaintModel
            await db.execute(
                sa_update(ComplaintModel)
                .where(ComplaintModel.id == complaint.id)
                .values(view_count=ComplaintModel.view_count + 1)
            )
            await db.commit()
        except Exception:
            pass  # Never fail the request due to view tracking

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

        # When the user toggled off their vote, action="removed" and vote_type=None
        resolved_user_vote = None if result.get("action") == "removed" else data.vote_type
        return VoteResponse(
            complaint_id=complaint_id,
            upvotes=result["upvotes"],
            downvotes=result["downvotes"],
            priority_score=result["priority_score"],
            priority=result["priority"],
            user_vote=resolved_user_vote
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
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get status change history for complaint.
    Accessible by both students (with visibility check) and authority/admin users.
    """
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from src.database.models import Complaint, StatusUpdate

    query = (
        select(Complaint)
        .options(
            selectinload(Complaint.status_updates).selectinload(StatusUpdate.updated_by_authority),
            selectinload(Complaint.student),
        )
        .where(Complaint.id == complaint_id)
    )
    result = await db.execute(query)
    complaint_with_updates = result.scalar_one_or_none()

    if not complaint_with_updates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    # Authorities and admins can view any complaint's history
    role = user.get("role", "")
    if role not in ("Authority", "Admin"):
        # Student visibility check — owner can always see their own complaint history
        from src.repositories.student_repo import StudentRepository
        from src.api.dependencies import check_complaint_visibility
        student_repo = StudentRepository(db)
        roll_no = user.get("user_id")
        student = await student_repo.get_with_department(roll_no) if roll_no else None
        if not student or not await check_complaint_visibility(complaint_with_updates, student):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Build status history — separate true status changes from post-update notes
    status_updates = []
    for update in sorted(complaint_with_updates.status_updates, key=lambda x: x.updated_at):
        is_post_update = update.old_status == update.new_status
        status_updates.append({
            "old_status": update.old_status,
            "new_status": update.new_status,
            "reason": update.reason,
            "is_post_update": is_post_update,
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
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete complaint timeline.
    Accessible by both students (with visibility check) and authority/admin users.
    Includes: Submission, status changes, authority post-updates, resolution.
    """
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from src.database.models import Complaint, StatusUpdate

    query = (
        select(Complaint)
        .options(
            selectinload(Complaint.status_updates).selectinload(StatusUpdate.updated_by_authority),
            selectinload(Complaint.student),
            selectinload(Complaint.assigned_authority),
        )
        .where(Complaint.id == complaint_id)
    )
    result = await db.execute(query)
    complaint_full = result.scalar_one_or_none()

    if not complaint_full:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    # Authorities and admins can view any complaint's timeline
    role = user.get("role", "")
    if role not in ("Authority", "Admin"):
        from src.repositories.student_repo import StudentRepository
        from src.api.dependencies import check_complaint_visibility
        student_repo = StudentRepository(db)
        roll_no = user.get("user_id")
        student = await student_repo.get_with_department(roll_no) if roll_no else None
        if not student or not await check_complaint_visibility(complaint_full, student):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    is_authority = role in ("Authority", "Admin")

    # Build timeline
    timeline = []

    # Submission — mask student name for non-authorities
    student_label = complaint_full.student.name if (is_authority and complaint_full.student) else "a student"
    timeline.append({
        "event": "Complaint Submitted",
        "timestamp": complaint_full.submitted_at.isoformat(),
        "description": f"Complaint raised by {student_label}",
        "updated_by": student_label,
    })

    # Status changes and authority post-updates
    for update in sorted(complaint_full.status_updates, key=lambda x: x.updated_at):
        by_name = update.updated_by_authority.name if update.updated_by_authority else "System"
        is_post_update = update.old_status == update.new_status
        if is_post_update:
            # Authority posted a note/update without changing status
            timeline.append({
                "event": "Authority Update",
                "timestamp": update.updated_at.isoformat(),
                "description": update.reason or "Update posted",
                "updated_by": by_name,
            })
        else:
            timeline.append({
                "event": "Status Changed",
                "timestamp": update.updated_at.isoformat(),
                "description": f"Status changed from {update.old_status} to {update.new_status}",
                "reason": update.reason,
                "updated_by": by_name,
            })

    # Resolution marker (only if not already captured by a status-change entry)
    if complaint_full.resolved_at:
        timeline.append({
            "event": "Complaint Resolved",
            "timestamp": complaint_full.resolved_at.isoformat(),
            "description": "Complaint marked as resolved",
        })

    # Sort by timestamp ascending
    timeline.sort(key=lambda x: x["timestamp"])

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

    if complaint.has_disputed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already disputed this complaint")

    # Mark as disputed so the student can't dispute again, store appeal reason
    complaint.has_disputed = True
    complaint.appeal_reason = (reason or "").strip() or None
    await db.commit()

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


# ==================== SATISFACTION RATING ====================

@router.post(
    "/{complaint_id}/rate",
    response_model=SatisfactionRatingResponse,
    summary="Rate complaint resolution",
    description="Submit satisfaction rating (1-5) after complaint is Resolved or Closed"
)
async def rate_complaint(
    complaint_id: UUID,
    body: SatisfactionRatingRequest,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit satisfaction rating after a complaint is resolved.

    - Only the complaint owner can rate
    - Complaint must be Resolved or Closed
    - Can only be rated once
    """
    from src.repositories.complaint_repo import ComplaintRepository
    from datetime import datetime, timezone

    complaint_repo = ComplaintRepository(db)
    complaint = await complaint_repo.get(complaint_id)

    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    if complaint.student_roll_no != roll_no:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the complaint owner can rate it")

    if complaint.status not in ("Resolved", "Closed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complaint must be Resolved or Closed before rating"
        )

    if complaint.satisfaction_rating is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complaint has already been rated"
        )

    complaint.satisfaction_rating = body.rating
    complaint.satisfaction_feedback = body.feedback
    complaint.rated_at = datetime.now(timezone.utc)
    authority_id_for_notify = complaint.assigned_authority_id
    complaint_text_for_notify = (complaint.rephrased_text or complaint.original_text or "")
    await db.commit()

    logger.info(f"Complaint {complaint_id} rated {body.rating}/5 by {roll_no}")

    # Notify the assigned authority about the rating
    if authority_id_for_notify:
        try:
            from src.services.notification_service import notification_service
            stars = body.rating * "★" + (5 - body.rating) * "☆"
            await notification_service.create_notification(
                db,
                recipient_type="Authority",
                recipient_id=str(authority_id_for_notify),
                complaint_id=complaint_id,
                notification_type="rating_received",
                message=(
                    f"A student rated their complaint {body.rating}/5 ({stars}). "
                    f'Complaint: "{complaint_text_for_notify[:80]}..."'
                )
            )
        except Exception as _notif_err:
            logger.warning(f"Failed to send rating notification: {_notif_err}")

    return SatisfactionRatingResponse(
        complaint_id=complaint_id,
        rating=body.rating,
        feedback=body.feedback,
        message="Thank you for your feedback!"
    )


# ==================== IMPROVED DUPLICATE DETECTION ====================

# Common stop words to exclude from token matching
_STOP_WORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'in', 'on', 'at', 'of',
    'for', 'to', 'with', 'by', 'from', 'not', 'no', 'my', 'our', 'i',
    'we', 'it', 'its', 'this', 'that', 'very', 'so', 'and', 'or', 'but',
    'there', 'their', 'they', 'what', 'when', 'where', 'which', 'who',
    'how', 'all', 'also', 'just', 'get', 'got', 'still', 'please',
}

# Expand common abbreviations and synonyms before comparison
_SYNONYMS = [
    (r'\bac\b', 'air conditioner'),
    (r'\ba\.c\b', 'air conditioner'),
    (r'\bwifi\b', 'wireless internet'),
    (r'\bwi-fi\b', 'wireless internet'),
    (r'\bwashroom\b', 'toilet bathroom'),
    (r'\bwc\b', 'toilet bathroom'),
    (r'\brest room\b', 'toilet bathroom'),
    (r'\bcanteen\b', 'cafeteria food'),
    (r'\bmess\b', 'cafeteria food'),
    (r'\blight\b', 'electricity power'),
    (r'\bpower\b', 'electricity power'),
    (r'\belectricity\b', 'electricity power'),
    (r'\bprofessor\b', 'faculty teacher'),
    (r'\bprof\b', 'faculty teacher'),
    (r'\bfaculty\b', 'faculty teacher'),
    (r'\blab\b', 'laboratory'),
]


def _preprocess(text: str) -> str:
    """Lowercase, expand synonyms, remove punctuation."""
    import re
    t = (text or "").lower().strip()
    for pattern, replacement in _SYNONYMS:
        t = re.sub(pattern, replacement, t)
    t = re.sub(r"[^\w\s]", " ", t)
    return t


def _word_tokens(text: str) -> set:
    """Meaningful word tokens after stop word removal."""
    return {w for w in _preprocess(text).split() if len(w) > 2 and w not in _STOP_WORDS}


def _char_ngrams(text: str, n: int = 4) -> set:
    """Character n-grams on condensed text — catches 'AC'↔'air conditioner' via bigrams."""
    normalized = "".join(_preprocess(text).split())
    return {normalized[i:i+n] for i in range(len(normalized) - n + 1)} if len(normalized) >= n else set()


def _jaccard(a: str, b: str) -> float:
    """
    Combined similarity: 60% word-level Jaccard + 40% char-4gram Jaccard.
    Handles synonyms, abbreviations, and partial word matches better than plain word sets.
    """
    wa, wb = _word_tokens(a), _word_tokens(b)
    ca, cb = _char_ngrams(a), _char_ngrams(b)

    word_score = len(wa & wb) / len(wa | wb) if (wa | wb) else 0.0
    char_score = len(ca & cb) / len(ca | cb) if (ca | cb) else 0.0

    return 0.6 * word_score + 0.4 * char_score


@router.post(
    "/check-duplicate",
    response_model=DuplicateCheckResponse,
    summary="Check for duplicate complaints",
    description="Before submitting, detect similar recent complaints"
)
async def check_duplicate(
    body: DuplicateCheckRequest,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if a complaint text is likely a duplicate of existing public complaints.
    Uses Jaccard token similarity for fast, accurate matching. Returns top similar
    complaints for the student to review before submitting.
    """
    from src.database.models import Complaint
    from sqlalchemy import select, and_
    from sqlalchemy.orm import selectinload
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    query = (
        select(Complaint)
        .options(selectinload(Complaint.category))
        .where(
            and_(
                Complaint.visibility == "Public",
                Complaint.status != "Spam",
                Complaint.is_marked_as_spam == False,
                Complaint.submitted_at >= cutoff,
                Complaint.merged_into_id == None,  # Exclude merged-away complaints
            )
        )
        .order_by(Complaint.submitted_at.desc())
        .limit(300)
    )
    result = await db.execute(query)
    candidates = result.scalars().all()

    THRESHOLD = 0.10          # Lowered: catch more potential duplicates
    LIKELY_DUP_THRESHOLD = 0.18  # Lowered: flag as likely dup sooner
    query_text = (body.text or "").strip()

    # Compute improved similarity against each candidate
    scored = []
    for c in candidates:
        text = c.rephrased_text or c.original_text or ""
        score = _jaccard(query_text, text)
        if score >= THRESHOLD:
            scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)

    duplicates = [
        DuplicateCandidate(
            id=c.id,
            rephrased_text=(c.rephrased_text or c.original_text or "")[:300],
            status=c.status,
            upvotes=c.upvotes or 0,
            submitted_at=c.submitted_at,
            similarity_score=round(score, 3),
            is_own=(c.student_roll_no == roll_no),  # hide upvote on own complaints
        )
        for score, c in scored[:5]
    ]

    is_likely_dup = bool(duplicates) and duplicates[0].similarity_score >= LIKELY_DUP_THRESHOLD

    return DuplicateCheckResponse(
        is_likely_duplicate=is_likely_dup,
        duplicates=duplicates,
        message=(
            "Similar complaints found — consider upvoting instead of re-submitting."
            if is_likely_dup
            else "No significant duplicates found."
        )
    )


# ==================== LLM AUTO-MERGE FOR DUPLICATE CLUSTERS ====================

MERGE_THRESHOLD_COUNT = 10     # Minimum duplicates to trigger merge
MERGE_SIMILARITY_MIN = 0.20   # Minimum Jaccard similarity to count as cluster member


async def _check_and_merge_duplicates(db: AsyncSession, new_complaint):
    """
    After a new complaint is submitted, check if there are 10+ similar complaints
    in the public feed. If so, LLM merges them into a single canonical complaint.
    """
    from src.database.models import Complaint, Notification, Authority
    from sqlalchemy import select, and_
    from datetime import datetime, timedelta, timezone
    import json

    try:
        new_text = new_complaint.rephrased_text or new_complaint.original_text or ""
        if len(new_text.strip()) < 10:
            return

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        # Get recent public complaints (excluding already-merged ones)
        q = (
            select(Complaint)
            .where(
                and_(
                    Complaint.visibility == "Public",
                    Complaint.status.notin_(["Spam", "Closed"]),
                    Complaint.is_marked_as_spam == False,
                    Complaint.submitted_at >= cutoff,
                    Complaint.merged_into_id == None,
                    Complaint.id != new_complaint.id,
                )
            )
            .order_by(Complaint.submitted_at.desc())
            .limit(300)
        )
        result = await db.execute(q)
        candidates = list(result.scalars().all())

        if len(candidates) < MERGE_THRESHOLD_COUNT:
            return

        # Compute Jaccard similarities
        cluster = [(new_complaint, 1.0)]  # Include the new complaint itself
        for c in candidates:
            text = c.rephrased_text or c.original_text or ""
            score = _jaccard(new_text, text)
            if score >= MERGE_SIMILARITY_MIN:
                cluster.append((c, score))

        if len(cluster) < MERGE_THRESHOLD_COUNT:
            # Not enough duplicates — but notify if >= 5
            if len(cluster) >= 5:
                await _notify_trend_detected(db, cluster, new_text, new_complaint.assigned_authority_id)
            return

        # 10+ duplicates found — call LLM to create merged summary
        logger.info(f"Duplicate cluster of {len(cluster)} found — triggering LLM merge")

        complaint_texts = []
        for c, _ in cluster[:15]:  # Cap at 15 for LLM context
            text = c.rephrased_text or c.original_text or ""
            complaint_texts.append(text[:200])

        merged_summary = await _llm_merge_complaints(complaint_texts)
        if not merged_summary:
            return

        # Deduplicate votes across the cluster:
        # A student who voted on multiple duplicate complaints counts only once
        from src.database.models import Vote
        cluster_ids = [c.id for c, _ in cluster]
        vote_q = select(Vote).where(Vote.complaint_id.in_(cluster_ids))
        vote_result = await db.execute(vote_q)
        all_votes = vote_result.scalars().all()

        # Keep only the most recent vote per student (upvote wins over downvote if mixed)
        voter_map: dict = {}  # student_roll_no → latest vote_type
        for v in sorted(all_votes, key=lambda x: x.created_at or datetime.min):
            voter_map[v.student_roll_no] = v.vote_type

        unique_upvotes = sum(1 for vt in voter_map.values() if vt == "upvote")
        unique_downvotes = sum(1 for vt in voter_map.values() if vt == "downvote")
        unique_voters = len(voter_map)

        # Create canonical complaint using deduplicated vote counts
        canonical = Complaint(
            student_roll_no=new_complaint.student_roll_no,
            category_id=new_complaint.category_id,
            original_text=f"[Auto-merged from {len(cluster)} similar complaints]",
            rephrased_text=merged_summary,
            visibility="Public",
            upvotes=unique_upvotes,
            downvotes=unique_downvotes,
            priority_score=0.0,
            priority="High",  # Merged complaints with 10+ reports are at least High
            assigned_authority_id=new_complaint.assigned_authority_id,
            status="Raised",
            is_merged_canonical=True,
            complaint_department_id=new_complaint.complaint_department_id,
        )
        db.add(canonical)
        await db.flush()

        # Point all cluster members to the canonical
        for c, _ in cluster:
            c.merged_into_id = canonical.id

        await db.flush()
        await db.commit()

        # Build notification message with unique vote info
        vote_info = (
            f"Unique voters: {unique_voters} students "
            f"({unique_upvotes} upvotes, {unique_downvotes} downvotes — deduplicated)"
        )
        merge_msg = (
            f"🔗 AUTO-MERGED: {len(cluster)} similar complaints combined into one issue.\n"
            f"Summary: \"{merged_summary[:300]}\"\n"
            f"{vote_info}"
        )

        # Notify all admins
        admin_q = select(Authority).where(
            and_(Authority.authority_type == "Admin", Authority.is_active == True)
        )
        admin_result = await db.execute(admin_q)
        admins = admin_result.scalars().all()
        for admin in admins:
            db.add(Notification(
                recipient_type="Authority",
                recipient_id=str(admin.id),
                complaint_id=canonical.id,
                notification_type="duplicate_merge",
                message=merge_msg,
            ))

        # Notify the assigned authority (HOD, Warden, etc.) if different from admin
        if new_complaint.assigned_authority_id:
            db.add(Notification(
                recipient_type="Authority",
                recipient_id=str(new_complaint.assigned_authority_id),
                complaint_id=canonical.id,
                notification_type="duplicate_merge",
                message=merge_msg,
            ))

        await db.commit()

        logger.info(f"Successfully merged {len(cluster)} complaints into canonical {canonical.id}")

    except Exception as e:
        logger.error(f"Auto-merge failed (non-fatal): {e}", exc_info=True)


async def _llm_merge_complaints(complaint_texts: list) -> str | None:
    """Use Groq LLM to create a merged summary from multiple similar complaints."""
    try:
        from src.services.llm_service import llm_service

        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(complaint_texts))
        prompt = (
            "You are summarizing multiple similar campus complaints into ONE concise complaint.\n"
            "These complaints are all about the same issue reported by different students.\n\n"
            f"Individual complaints:\n{numbered}\n\n"
            "Write a single, clear, professional complaint text (2-4 sentences) that captures:\n"
            "- The core issue all students are reporting\n"
            "- The scope/impact (mention that multiple students reported this)\n"
            "- Any specific details mentioned across complaints\n\n"
            "Output ONLY the merged complaint text, nothing else."
        )

        response = await llm_service.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"LLM merge failed: {e}")
        return None


async def _notify_trend_detected(db, cluster, query_text, assigned_authority_id=None):
    """Notify admins and assigned authority when 5+ similar complaints detected."""
    from src.database.models import Authority, Notification
    from sqlalchemy import and_

    try:
        topic = query_text[:100]
        trend_msg = (
            f"📈 TREND: {len(cluster)} students reported similar issues.\n"
            f"Topic: \"{topic}...\"\n"
            f"Consider investigating this pattern before it escalates further."
        )
        # Notify admins
        admin_q = select(Authority).where(
            and_(Authority.authority_type == "Admin", Authority.is_active == True)
        )
        admin_result = await db.execute(admin_q)
        admins = admin_result.scalars().all()
        for admin in admins:
            db.add(Notification(
                recipient_type="Authority",
                recipient_id=str(admin.id),
                complaint_id=None,
                notification_type="trend_detected",
                message=trend_msg,
            ))
        # Notify assigned authority
        if assigned_authority_id:
            db.add(Notification(
                recipient_type="Authority",
                recipient_id=str(assigned_authority_id),
                complaint_id=None,
                notification_type="trend_detected",
                message=trend_msg,
            ))
        await db.commit()
    except Exception as e:
        logger.warning(f"Trend notification failed: {e}")


# ==================== ANALYTICS (PUBLIC SUMMARY) ====================

@router.get(
    "/analytics/summary",
    summary="Public complaint analytics",
    description="Overall complaint statistics visible to all students"
)
async def get_public_analytics(
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    High-level complaint statistics for the student dashboard analytics panel.

    Returns counts by status, category, and department plus avg resolution time.
    """
    from src.database.models import Complaint, ComplaintCategory, Department
    from sqlalchemy import select, func, and_, case

    # Status counts (public, non-spam)
    base = and_(
        Complaint.visibility == "Public",
        Complaint.is_marked_as_spam == False,
    )

    status_query = (
        select(Complaint.status, func.count().label("cnt"))
        .where(base)
        .group_by(Complaint.status)
    )
    status_result = await db.execute(status_query)
    status_counts = {row.status: row.cnt for row in status_result}

    # Category breakdown
    category_query = (
        select(ComplaintCategory.name, func.count().label("cnt"))
        .join(Complaint, Complaint.category_id == ComplaintCategory.id)
        .where(base)
        .group_by(ComplaintCategory.name)
        .order_by(func.count().desc())
    )
    cat_result = await db.execute(category_query)
    category_breakdown = {row.name: row.cnt for row in cat_result}

    # Top 5 departments by complaint volume
    dept_query = (
        select(Department.name, func.count().label("cnt"))
        .join(Complaint, Complaint.complaint_department_id == Department.id)
        .where(base)
        .group_by(Department.name)
        .order_by(func.count().desc())
        .limit(5)
    )
    dept_result = await db.execute(dept_query)
    dept_breakdown = {row.name: row.cnt for row in dept_result}

    # Avg resolution time in hours (resolved complaints only)
    resolution_query = (
        select(
            func.extract("epoch",
                func.avg(Complaint.resolved_at - Complaint.submitted_at)
            ).label("avg_secs")
        )
        .where(
            and_(
                base,
                Complaint.resolved_at.isnot(None),
                Complaint.status.in_(["Resolved", "Closed"]),
            )
        )
    )
    res_result = await db.execute(resolution_query)
    avg_secs = res_result.scalar()
    avg_resolution_hours = round(float(avg_secs) / 3600, 1) if avg_secs else None

    # Satisfaction average
    sat_query = select(func.avg(Complaint.satisfaction_rating)).where(
        and_(base, Complaint.satisfaction_rating.isnot(None))
    )
    sat_result = await db.execute(sat_query)
    satisfaction_avg = sat_result.scalar()
    satisfaction_avg = round(float(satisfaction_avg), 2) if satisfaction_avg else None

    total = sum(status_counts.values())

    return {
        "total_complaints": total,
        "status_breakdown": status_counts,
        "category_breakdown": category_breakdown,
        "top_departments": dept_breakdown,
        "avg_resolution_hours": avg_resolution_hours,
        "satisfaction_avg": satisfaction_avg,
    }


# ==================== AUTHORITY FILE ATTACHMENT ====================

ALLOWED_ATTACHMENT_TYPES = {
    "application/pdf",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/{complaint_id}/authority-attachment",
    summary="Upload authority attachment",
    description="Authority uploads a file (PDF, Excel, Word, image) to attach to a complaint",
)
async def upload_authority_attachment(
    complaint_id: UUID,
    file: UploadFile = File(...),
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db),
):
    from src.database.models import Complaint
    from sqlalchemy import select

    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Validate MIME type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{content_type}' not allowed. Supported: PDF, Excel, Word, JPEG, PNG, WebP"
        )

    data = await file.read()
    if len(data) > MAX_ATTACHMENT_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit")

    complaint.authority_attachment_data = data
    complaint.authority_attachment_filename = file.filename or "attachment"
    complaint.authority_attachment_mimetype = content_type
    complaint.authority_attachment_size = len(data)
    await db.commit()

    logger.info(f"Authority {authority_id} attached '{file.filename}' ({len(data)} bytes) to complaint {complaint_id}")
    return {
        "success": True,
        "filename": complaint.authority_attachment_filename,
        "size": complaint.authority_attachment_size,
        "mimetype": complaint.authority_attachment_mimetype,
    }


@router.get(
    "/{complaint_id}/authority-attachment",
    summary="Download authority attachment",
    description="Download the file attached by authority to a complaint",
)
async def download_authority_attachment(
    complaint_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from src.database.models import Complaint
    from sqlalchemy import select

    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if not complaint.authority_attachment_data:
        raise HTTPException(status_code=404, detail="No attachment found for this complaint")

    return Response(
        content=complaint.authority_attachment_data,
        media_type=complaint.authority_attachment_mimetype or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{complaint.authority_attachment_filename or "attachment"}"',
            "Content-Length": str(complaint.authority_attachment_size or len(complaint.authority_attachment_data)),
        }
    )


__all__ = ["router"]
