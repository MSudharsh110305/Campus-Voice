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
from datetime import datetime, timezone, timedelta
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
    get_optional_user,
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
    gps_lat: Optional[float] = Form(None, description="Live GPS latitude from browser (camera capture only)"),
    gps_lon: Optional[float] = Form(None, description="Live GPS longitude from browser (camera capture only)"),
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
            gps_lat=gps_lat,
            gps_lon=gps_lon,
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

        # Rule H4: cross-gender hostel submission → 403 Forbidden
        if error_message.startswith("HOSTEL_GENDER_MISMATCH:"):
            human_message = error_message.split("HOSTEL_GENDER_MISMATCH:", 1)[1].strip()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=human_message
            )

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

    # Count using same visibility logic as get_public_feed (mirrors all visibility rules)
    from src.database.models import ComplaintCategory
    cat_id_query = select(ComplaintCategory.id, ComplaintCategory.name)
    cat_id_result = await db.execute(cat_id_query)
    cat_name_to_id = {row[1]: row[0] for row in cat_id_result.all()}

    mens_hostel_id = cat_name_to_id.get("Men's Hostel")
    womens_hostel_id = cat_name_to_id.get("Women's Hostel")
    general_id = cat_name_to_id.get("General")
    disciplinary_id = cat_name_to_id.get("Disciplinary Committee")
    department_cat_id = cat_name_to_id.get("Department")

    count_conditions = [
        Complaint.visibility == "Public",
        Complaint.status != "Closed",
        Complaint.status != "Spam",
        Complaint.is_marked_as_spam == False,
        Complaint.merged_into_id == None,
    ]

    # DC1: Always exclude Disciplinary Committee from public feed count
    if disciplinary_id:
        count_conditions.append(Complaint.category_id != disciplinary_id)

    # H1: Day Scholars never see hostel complaints
    if student.stay_type == "Day Scholar":
        if mens_hostel_id:
            count_conditions.append(Complaint.category_id != mens_hostel_id)
        if womens_hostel_id:
            count_conditions.append(Complaint.category_id != womens_hostel_id)
    else:
        # H2: Hostel students see only their gender's hostel
        if student.gender == "Male" and womens_hostel_id:
            count_conditions.append(Complaint.category_id != womens_hostel_id)
        elif student.gender == "Female" and mens_hostel_id:
            count_conditions.append(Complaint.category_id != mens_hostel_id)

    visible_conditions = []

    # G1: General visible to all
    if general_id:
        visible_conditions.append(Complaint.category_id == general_id)

    # H3: Hostel visible to all same-gender hostel students
    if student.stay_type != "Day Scholar":
        if student.gender == "Male" and mens_hostel_id:
            visible_conditions.append(Complaint.category_id == mens_hostel_id)
        elif student.gender == "Female" and womens_hostel_id:
            visible_conditions.append(Complaint.category_id == womens_hostel_id)
        elif student.gender not in ("Male", "Female"):
            hostel_ids = [i for i in [mens_hostel_id, womens_hostel_id] if i is not None]
            if hostel_ids:
                visible_conditions.append(Complaint.category_id.in_(hostel_ids))

    # D1/D2/D4: Department complaints — target dept OR submitter's dept
    if department_cat_id:
        dept_visible = or_(
            Complaint.complaint_department_id == student.department_id,
            Complaint.complainant_department_id == student.department_id,
        )
        visible_conditions.append(
            and_(Complaint.category_id == department_cat_id, dept_visible)
        )

    # Self-visibility
    visible_conditions.append(Complaint.student_roll_no == student.roll_no)

    if visible_conditions:
        count_conditions.append(or_(*visible_conditions))
    else:
        count_conditions.append(False)

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
    summary="What's Fixed — scored rolling 7-day wins feed",
    description="Top resolved complaints from the last 7 days, scored and filtered by win_score"
)
async def get_changelog(
    current_user: Optional[dict] = Depends(get_optional_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Rolling 7-day wins feed — recently resolved public complaints scored by impact.

    win_score = (upvotes * 3) + (downvotes * -1) + priority_bonus + speed_bonus
    priority_bonus: Critical=20, High=10, Medium=5, Low=0
    speed_bonus: <=24h=15, <=72h=10, <=168h=5, else 0

    Only complaints with win_score >= 5 OR upvotes >= 2 are shown.
    Sorted by win_score DESC, top 20 returned.
    Visibility rules (hostel/department/public) are applied based on the authenticated student.
    Unauthenticated: only non-hostel Public complaints are shown.
    """
    from src.database.models import Complaint, ComplaintCategory, Student
    from sqlalchemy import select, func, and_, or_
    from sqlalchemy.orm import selectinload

    now_utc = datetime.now(timezone.utc)
    seven_days_ago = now_utc - timedelta(days=7)

    # Resolve category IDs for visibility rules
    cat_id_query = select(ComplaintCategory.id, ComplaintCategory.name)
    cat_id_result = await db.execute(cat_id_query)
    cat_name_to_id: dict = {row[1]: row[0] for row in cat_id_result.all()}

    mens_hostel_id = cat_name_to_id.get("Men's Hostel")
    womens_hostel_id = cat_name_to_id.get("Women's Hostel")
    general_id = cat_name_to_id.get("General")
    disciplinary_id = cat_name_to_id.get("Disciplinary Committee")
    department_cat_id = cat_name_to_id.get("Department")

    # Base conditions
    conditions = [
        Complaint.visibility == "Public",
        Complaint.status == "Resolved",
        Complaint.is_marked_as_spam == False,
        Complaint.is_deleted == False,
        Complaint.merged_into_id == None,
        Complaint.resolved_at >= seven_days_ago,
    ]

    # Always exclude Disciplinary Committee
    if disciplinary_id:
        conditions.append(Complaint.category_id != disciplinary_id)

    # Determine visibility context from authenticated user
    student = None
    if current_user and current_user.get("role") == "Student":
        try:
            roll_no = current_user.get("user_id")
            if roll_no:
                student_q = select(Student).where(Student.roll_no == roll_no)
                student_result = await db.execute(student_q)
                student = student_result.scalar_one_or_none()
        except Exception:
            student = None

    if student:
        stay_type = student.stay_type
        gender = student.gender
        dept_id = student.department_id
        roll_no = student.roll_no

        # H1: Day Scholars never see hostel complaints
        if stay_type == "Day Scholar":
            if mens_hostel_id:
                conditions.append(Complaint.category_id != mens_hostel_id)
            if womens_hostel_id:
                conditions.append(Complaint.category_id != womens_hostel_id)
        else:
            # H2: Hostel students see only their gender's hostel
            if gender == "Male" and womens_hostel_id:
                conditions.append(Complaint.category_id != womens_hostel_id)
            elif gender == "Female" and mens_hostel_id:
                conditions.append(Complaint.category_id != mens_hostel_id)

        visible_conditions = []
        if general_id:
            visible_conditions.append(Complaint.category_id == general_id)
        # Hostel visibility
        if stay_type != "Day Scholar":
            if gender == "Male" and mens_hostel_id:
                visible_conditions.append(Complaint.category_id == mens_hostel_id)
            elif gender == "Female" and womens_hostel_id:
                visible_conditions.append(Complaint.category_id == womens_hostel_id)
            elif gender not in ("Male", "Female"):
                hostel_ids = [i for i in [mens_hostel_id, womens_hostel_id] if i is not None]
                if hostel_ids:
                    visible_conditions.append(Complaint.category_id.in_(hostel_ids))
        # Department visibility
        if department_cat_id and dept_id:
            dept_visible = or_(
                Complaint.complaint_department_id == dept_id,
                Complaint.complainant_department_id == dept_id,
            )
            visible_conditions.append(and_(Complaint.category_id == department_cat_id, dept_visible))
        # Own complaints always visible
        visible_conditions.append(Complaint.student_roll_no == roll_no)

        if visible_conditions:
            conditions.append(or_(*visible_conditions))
        else:
            conditions.append(False)
    else:
        # Unauthenticated: only non-hostel General/Public complaints
        hostel_ids = [i for i in [mens_hostel_id, womens_hostel_id] if i is not None]
        if hostel_ids:
            conditions.append(Complaint.category_id.notin_(hostel_ids))
        # Show only General category for unauthenticated
        if general_id:
            conditions.append(Complaint.category_id == general_id)

    query = (
        select(Complaint)
        .options(selectinload(Complaint.category))
        .where(and_(*conditions))
        .limit(1000)
    )
    result = await db.execute(query)
    complaints = list(result.scalars().all())

    # Compute win_score in Python
    def _compute_win_score(c: Complaint) -> int:
        priority_bonus = {"Critical": 20, "High": 10, "Medium": 5, "Low": 0}.get(c.priority or "Low", 0)
        speed_bonus = 0
        if c.resolved_at and c.submitted_at:
            r = c.resolved_at if c.resolved_at.tzinfo else c.resolved_at.replace(tzinfo=timezone.utc)
            s = c.submitted_at if c.submitted_at.tzinfo else c.submitted_at.replace(tzinfo=timezone.utc)
            hours = (r - s).total_seconds() / 3600
            if hours <= 24:
                speed_bonus = 15
            elif hours <= 72:
                speed_bonus = 10
            elif hours <= 168:
                speed_bonus = 5
        return (c.upvotes or 0) * 3 + (c.downvotes or 0) * -1 + priority_bonus + speed_bonus

    def _resolution_hours(c: Complaint) -> Optional[float]:
        if c.resolved_at and c.submitted_at:
            r = c.resolved_at if c.resolved_at.tzinfo else c.resolved_at.replace(tzinfo=timezone.utc)
            s = c.submitted_at if c.submitted_at.tzinfo else c.submitted_at.replace(tzinfo=timezone.utc)
            return round((r - s).total_seconds() / 3600, 1)
        return None

    # Score, filter, sort
    scored = [(c, _compute_win_score(c)) for c in complaints]
    scored = [(c, score) for c, score in scored if score >= 5 or (c.upvotes or 0) >= 2]
    scored.sort(key=lambda x: x[1], reverse=True)

    total = len(scored)
    page_items = scored[skip: skip + limit]

    entries = [
        ChangelogEntry(
            id=c.id,
            rephrased_text=(c.rephrased_text or c.original_text or "")[:400],
            resolution_note=c.resolution_note,
            category_name=c.category.name if c.category else None,
            resolved_at=c.resolved_at,
            upvotes=c.upvotes or 0,
            satisfaction_avg=float(c.satisfaction_rating) if c.satisfaction_rating else None,
            win_score=score,
            resolution_hours=_resolution_hours(c),
        )
        for c, score in page_items
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


# ==================== IMAGE GRACE-PERIOD DECISION ====================

@router.post(
    "/{complaint_id}/image-decision",
    summary="Authority image decision",
    description=(
        "Authority decides to keep or delete a complaint whose image upload grace period has expired. "
        "Only the assigned authority (or Admin) can call this endpoint."
    )
)
async def authority_image_decision(
    complaint_id: UUID,
    action: str = Form(..., description="'keep' or 'delete'"),
    reason: Optional[str] = Form(None, description="Optional explanation"),
    authority: dict = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db),
):
    """
    After a student's 24-hour image upload window expires, the assigned authority
    receives a notification and calls this endpoint to either:
    - **keep**: complaint stays as-is (image_pending cleared, life goes on)
    - **delete**: complaint is soft-deleted and the student is notified
    """
    from sqlalchemy import select as _sel
    from src.database.models import Complaint as _C
    from src.services.notification_service import notification_service as _ns

    action = action.strip().lower()
    if action not in ("keep", "delete"):
        raise HTTPException(status_code=400, detail="action must be 'keep' or 'delete'")

    result = await db.execute(_sel(_C).where(_C.id == complaint_id, _C.is_deleted == False))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    authority_id = authority.get("id") or authority.get("user_id")
    authority_level = authority.get("authority_level", 0)

    # Only the assigned authority or Admin (level >= 100) may act
    is_assigned = str(complaint.assigned_authority_id) == str(authority_id)
    is_admin = authority_level >= 100
    if not is_assigned and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only the assigned authority or Admin can make this decision"
        )

    if not complaint.image_pending:
        raise HTTPException(
            status_code=400,
            detail="This complaint is not awaiting an image decision"
        )

    now = datetime.now(timezone.utc)

    if action == "keep":
        # Clear grace period flags — complaint stands without image
        complaint.image_pending = False
        complaint.image_required_deadline = None
        await db.commit()
        # Notify student
        try:
            await _ns.create_notification(
                db,
                recipient_type="Student",
                recipient_id=complaint.student_roll_no,
                complaint_id=complaint.id,
                notification_type="image_decision",
                message=(
                    "Your complaint has been kept on record by the authority even though "
                    "supporting image evidence was not uploaded. Your complaint will continue "
                    "to be reviewed normally."
                )
            )
        except Exception:
            pass
        return {"success": True, "action": "keep", "message": "Complaint retained"}

    else:  # delete
        complaint.is_deleted = True
        complaint.deleted_at = now
        complaint.image_pending = False
        await db.commit()
        # Notify student
        try:
            await _ns.create_notification(
                db,
                recipient_type="Student",
                recipient_id=complaint.student_roll_no,
                complaint_id=complaint.id,
                notification_type="image_decision",
                message=(
                    "Your complaint was removed because supporting visual evidence was not "
                    f"uploaded within the required 24-hour window. "
                    + (f"Authority note: {reason}" if reason else "")
                    + " You may re-submit the complaint with an image attached."
                )
            )
        except Exception:
            pass
        return {"success": True, "action": "delete", "message": "Complaint soft-deleted"}


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

    # Submission — only Admin sees the real student name; Authority always sees "a student"
    student_label = complaint_full.student.name if (role == "Admin" and complaint_full.student) else "a student"
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
    _now = datetime.now(timezone.utc)
    complaint.is_marked_as_spam = True
    complaint.spam_reason = reason
    complaint.spam_flagged_by = authority_id
    complaint.spam_flagged_at = _now
    complaint.status = "Spam"
    complaint.updated_at = _now
    # Set dispute_deadline only once (never overwrite if already set)
    if complaint.dispute_deadline is None:
        from datetime import timedelta
        complaint.dispute_deadline = _now + timedelta(days=7)

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
    complaint.dispute_deadline = None
    complaint.dispute_status = None
    complaint.appeal_deadline = None
    complaint.has_disputed = False
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
    summary="Dispute spam classification (legacy alias)",
    description="Student disputes their complaint being marked as spam"
)
async def appeal_spam(
    complaint_id: UUID,
    reason: Optional[str] = Query(None, max_length=200),
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """Legacy alias — delegates to the dispute endpoint logic."""
    return await _do_dispute(complaint_id, roll_no, reason, db)


@router.post(
    "/{complaint_id}/dispute",
    response_model=SuccessResponse,
    summary="Dispute spam classification",
    description="Student disputes their complaint being marked as spam within the 7-day window"
)
async def dispute_spam(
    complaint_id: UUID,
    reason: Optional[str] = Query(None, max_length=500),
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Dispute spam classification within the 7-day window.

    Conditions:
      - Complaint owner only
      - status == "Spam"
      - now() < dispute_deadline
      - has_disputed == False

    Sets has_disputed=True, dispute_status="Pending", notifies all admins.
    """
    return await _do_dispute(complaint_id, roll_no, reason, db)


async def _do_dispute(complaint_id: UUID, roll_no: str, reason: Optional[str], db: AsyncSession) -> SuccessResponse:
    """Shared logic for both dispute endpoints."""
    from src.repositories.complaint_repo import ComplaintRepository
    from src.repositories.authority_repo import AuthorityRepository
    from src.services.notification_service import notification_service
    from datetime import datetime, timezone, timedelta

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

    now = datetime.now(timezone.utc)

    # Enforce 7-day dispute window
    if complaint.dispute_deadline is not None:
        dl = complaint.dispute_deadline
        if dl.tzinfo is None:
            dl = dl.replace(tzinfo=timezone.utc)
        if now > dl:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The 7-day dispute window for this complaint has expired"
            )

    # Mark as disputed
    complaint.has_disputed = True
    complaint.dispute_status = "Pending"
    complaint.appeal_reason = (reason or "").strip() or None
    await db.commit()

    appeal_text = reason or "No reason provided"
    preview = (complaint.original_text or "")[:100]
    msg = (
        f"Spam dispute received: "
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
                notification_type="spam_dispute",
                message=msg
            )
    except Exception as e:
        logger.warning(f"Failed to notify admin of spam dispute: {e}")

    # Notify assigned authority if exists
    if complaint.assigned_authority_id:
        try:
            await notification_service.create_notification(
                db=db,
                recipient_type="Authority",
                recipient_id=str(complaint.assigned_authority_id),
                complaint_id=complaint_id,
                notification_type="spam_dispute",
                message=msg
            )
        except Exception as e:
            logger.warning(f"Failed to notify authority of spam dispute: {e}")

    logger.info(f"Spam dispute submitted for complaint {complaint_id} by {roll_no}")

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


# ==================== HYBRID DUPLICATE DETECTION ====================

# Common stop words to exclude from token matching
_STOP_WORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'in', 'on', 'at', 'of',
    'for', 'to', 'with', 'by', 'from', 'not', 'no', 'my', 'our', 'i',
    'we', 'it', 'its', 'this', 'that', 'very', 'so', 'and', 'or', 'but',
    'there', 'their', 'they', 'what', 'when', 'where', 'which', 'who',
    'how', 'all', 'also', 'just', 'get', 'got', 'still', 'please',
    'since', 'been', 'even', 'too', 'now', 'days', 'day', 'week',
    'month', 'months', 'time', 'has', 'always', 'never', 'need',
    'needs', 'want', 'due', 'said', 'told', 'every', 'each',
}

# ── Synonym / normalisation table ─────────────────────────────────────────────
# Rules are applied in order, so put multi-word patterns BEFORE single-word ones.
_SYNONYMS = [
    # ── Devices & technology ──────────────────────────────────────────────────
    (r'\ba\.c\b',               'air conditioner'),
    (r'\bac\b',                 'air conditioner'),
    (r'\bwi-fi\b',              'wireless internet'),
    (r'\bwifi\b',               'wireless internet'),
    (r'\bbroadband\b',          'internet'),
    (r'\bnet\b',                'internet'),          # "net not working" → internet
    (r'\bnetwork\b',            'internet'),
    (r'\bcctv\b',               'camera security'),
    (r'\btube light\b',         'bulb electricity'),
    (r'\btubelight\b',          'bulb electricity'),
    (r'\bswitchboard\b',        'socket switch'),
    (r'\bgeyser\b',             'hot water heater'),
    (r'\binverter\b',           'power backup electricity'),
    (r'\bgenerator\b',          'power backup electricity'),
    (r'\bups\b',                'power backup electricity'),
    (r'\bro\b',                 'water purifier'),
    (r'\bwater purifier\b',     'water purifier'),
    (r'\bwater cooler\b',       'water cooler'),
    (r'\bpurifier\b',           'water purifier'),

    # ── Restroom / sanitation ─────────────────────────────────────────────────
    (r'\brest room\b',          'toilet bathroom'),
    (r'\brestroom\b',           'toilet bathroom'),
    (r'\bwashroom\b',           'toilet bathroom'),
    (r'\bwc\b',                 'toilet bathroom'),
    (r'\bloo\b',                'toilet bathroom'),
    (r'\blavatory\b',           'toilet bathroom'),
    (r'\blatrine\b',            'toilet bathroom'),
    (r'\btoilets\b',            'toilet bathroom'),
    (r'\bbathrooms\b',          'toilet bathroom'),
    (r'\bcommode\b',            'toilet bathroom'),

    # ── Food & dining ─────────────────────────────────────────────────────────
    (r'\bcanteen\b',            'cafeteria'),
    (r'\bmess\b',               'cafeteria'),
    (r'\btiffin\b',             'meal food'),
    (r'\bsnacks\b',             'snack food'),
    (r'\bvending machine\b',    'snack food machine'),

    # ── Electricity / power ───────────────────────────────────────────────────
    (r'\belectricity\b',        'electricity power'),
    (r'\belectrcity\b',         'electricity power'),  # transposed c/i typo
    (r'\bpower\b',              'electricity power'),
    (r'\blight\b',              'electricity power'),
    (r'\bblackout\b',           'electricity power outage'),
    (r'\bpower cut\b',          'electricity power outage'),
    (r'\boutage\b',             'electricity power outage'),

    # ── Faculty / staff (Indian college) ─────────────────────────────────────
    (r'\bprofessor\b',          'faculty teacher'),
    (r'\bprof\b',               'faculty teacher'),
    (r'\bfaculty\b',            'faculty teacher'),
    (r'\blecturer\b',           'faculty teacher'),
    (r'\bsir\b',                'faculty teacher'),
    (r'\bmadam\b',              'faculty teacher'),
    (r'\bmaam\b',               'faculty teacher'),
    (r'\bmam\b',                'faculty teacher'),
    (r'\bhod\b',                'head department'),
    (r'\bvice principal\b',     'admin authority'),
    (r'\bprincipal\b',          'admin authority'),
    (r'\bwarden\b',             'hostel authority'),

    # ── Placement / career ────────────────────────────────────────────────────
    (r'\btnp\b',                'placement'),
    (r'\btpo\b',                'placement officer'),
    (r'\bcampus drive\b',       'placement'),
    (r'\boff campus\b',         'placement'),

    # ── Location short forms ──────────────────────────────────────────────────
    (r'\bdorm\b',               'hostel'),
    (r'\bpg\b',                 'hostel'),
    (r'\bclass room\b',         'classroom'),
    (r'\blecture hall\b',       'classroom hall'),
    (r'\blab\b',                'laboratory'),
    (r'\blabs\b',               'laboratory'),
    (r'\bblocks\b',             'block'),

    # ── Academic ──────────────────────────────────────────────────────────────
    (r'\blectures\b',           'class lecture'),
    (r'\blecture\b',            'class lecture'),
    (r'\bclasses\b',            'class'),
    (r'\bexams\b',              'exam'),
    (r'\binternal exam\b',      'exam internal'),
    (r'\binternal\b',           'exam internal'),
    (r'\bclass test\b',         'exam test'),
    (r'\bassignments\b',        'assignment'),
    (r'\bbunking\b',            'absent class'),
    (r'\babsent\b',             'not attending'),

    # ── Word-form normalisation ───────────────────────────────────────────────
    (r'\bcleanliness\b',        'clean'),
    (r'\bcleaned\b',            'clean'),
    (r'\bcleaning\b',           'clean'),
    (r'\bunclean\b',            'dirty'),
    (r'\bfilthy\b',             'dirty'),
    (r'\bunhygienic\b',         'dirty hygiene'),
    (r'\bunhygenic\b',          'dirty hygiene'),   # missing 'i' typo
    (r'\bstinking\b',           'smell stink'),
    (r'\bsmelling\b',           'smell'),
    (r'\bsmells\b',             'smell'),
    (r'\bfoul\b',               'smell dirty'),
    (r'\bmaintenance\b',        'maintain'),
    (r'\bmaintained\b',         'maintain'),
    (r'\brepairing\b',          'repair fix'),
    (r'\brepaired\b',           'repair fix'),
    (r'\brepair\b',             'fix'),
    (r'\bfixed\b',              'fix'),
    (r'\bfixing\b',             'fix'),
    (r'\bnot working\b',        'break'),
    (r'\bworking\b',            'work'),
    (r'\bworks\b',              'work'),
    (r'\bbroken\b',             'break'),
    (r'\bbreaking\b',           'break'),
    (r'\bdamaged\b',            'damage'),
    (r'\bdamaging\b',           'damage'),
    (r'\bleaking\b',            'leak'),
    (r'\bleaky\b',              'leak'),
    (r'\bflooded\b',            'flood water'),
    (r'\bsupplied\b',           'supply'),
    (r'\bteaching\b',           'teach'),
    (r'\bdisturbing\b',         'disturb'),
    (r'\bharrassing\b',         'harass'),     # common misspelling
    (r'\bharassing\b',          'harass'),
    (r'\bbullying\b',           'bully'),
    (r'\bragging\b',            'ragging'),    # dropped first 'g'
    (r'\battending\b',          'attend'),
    (r'\bthrown\b',             'throw garbage'),
    (r'\blittering\b',          'garbage dirty'),
    (r'\boverflowing\b',        'overflow'),
    (r'\bblocked\b',            'block'),
    (r'\bclogged\b',            'block drain'),
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


def _char_ngrams(text: str, n: int = 3) -> set:
    """
    Character n-grams on condensed text.
    n=3 (trigrams) chosen over 4-grams: better typo coverage since a 1-char
    insertion/deletion only destroys 3 adjacent trigrams vs 4 quadgrams,
    leaving more shared grams to drive the similarity score.
    """
    normalized = "".join(_preprocess(text).split())
    return {normalized[i:i+n] for i in range(len(normalized) - n + 1)} if len(normalized) >= n else set()


# ── Topic clusters ────────────────────────────────────────────────────────────
# Each cluster maps a semantic topic to its distinctive keywords.
# Two complaints in DIFFERENT clusters cannot be duplicates even if they
# share location words like "food court", "hostel block", "canteen", etc.
_COMPLAINT_TOPICS: dict[str, set[str]] = {
    "hygiene_sanitation": {
        "dirty", "clean", "hygiene", "sanitation", "garbage", "waste",
        "smell", "stink", "filthy", "sewage", "drain", "trash",
        "cockroach", "pest", "rat", "mice", "insect", "mold", "mould",
        "toilet", "bathroom", "latrine", "commode", "litter",
        "sweep", "swept", "mop", "mopped", "scrub",
    },
    "food_quality": {
        # "food" and "cafeteria" intentionally excluded — both appear as
        # location tokens ("food court", canteen→"cafeteria meal") and cause
        # false positives with hygiene complaints about the same venue.
        "meal", "menu", "taste", "tasty", "tasteless",
        "cook", "cooked", "serve", "serving", "veg", "nonveg",
        "breakfast", "lunch", "dinner", "rice", "roti", "curry",
        "stale", "expired", "quantity", "portion", "snack",
        "edible", "variety", "dish", "item", "tiffin", "sambar",
        "chapati", "quality",
    },
    "infrastructure": {
        "break", "damage", "fix", "leak", "crack",
        "door", "window", "roof", "wall", "ceiling",
        "table", "chair", "bench", "furniture", "paint",
        "peeling", "collapse", "maintain", "repair", "crumble",
    },
    "internet_connectivity": {
        "internet", "wireless", "connectivity",
        "connection", "bandwidth", "speed", "slow", "disconnect",
        "signal", "router", "lan", "hotspot",
    },
    "electricity_hvac": {
        "electricity", "fan", "cooling", "heating",
        "voltage", "socket", "switch", "bulb", "tube",
        "wiring", "circuit", "tripped", "outage",
        "conditioner",  # 'ac' → 'air conditioner' → token 'conditioner'
    },
    "water_supply": {
        "water", "supply", "shortage", "drinking", "tap", "pipe",
        "pressure", "borewell", "tank", "overflow", "muddy", "purifier",
        "cooler", "flood",
    },
    "academic_faculty": {
        "faculty", "teacher", "class", "lecture",
        "attendance", "marks", "grade", "exam", "assignment",
        "syllabus", "course", "subject", "teach",
        "notes", "material", "practical", "curriculum",
        "attend", "absent", "internal", "test",
    },
    "discipline_harassment": {
        "ragging", "harassment", "harass", "bully", "threat", "abuse",
        "violence", "misbehave", "misconduct", "tease", "intimidate",
        "inappropriate", "verbal", "physical", "eve",
    },
    "placement_career": {
        "placement", "internship", "job", "company", "recruit",
        "interview", "offer", "career", "opportunity",
        "resume", "training", "drive",
    },
    "transport": {
        "bus", "transport", "vehicle", "auto", "cab", "route", "driver",
        "timing", "schedule", "commute", "fuel", "breakdown",
    },
    "security": {
        "security", "guard", "camera", "theft", "stolen",
        "lock", "entry", "access", "badge", "safe",
    },
    "library": {
        "book", "library", "journal", "reading", "reference",
        "return", "resource", "catalog",
    },
    "financial": {
        "scholarship", "stipend", "fee", "refund", "dues",
        "payment", "challan", "fine", "penalty",
    },
    "hostel_admin": {
        # "night" removed — too ambiguous, fires on "every night" in unrelated complaints
        "curfew", "permission", "outing", "leave",
        "visitor", "warden", "authority", "rule", "regulation",
    },
}

# Location / venue words that appear in many complaint types.
# Complaints sharing ONLY these words should not be penalised less by cluster logic —
# that is already handled because location words don't belong to topic clusters.
_LOCATION_WORDS = {
    "hostel", "block", "floor", "building", "classroom", "laboratory",
    "department", "college", "campus", "ground", "field", "corridor",
    "hall", "gate", "parking", "workshop", "gym", "quarter",
    "court",  # as in 'food court' — location, not topic
}


def _get_topic_clusters(text: str) -> frozenset:
    """Return the set of topic cluster names matched in the text."""
    tokens = set(_preprocess(text).split())
    matched = set()
    for cluster_name, keywords in _COMPLAINT_TOPICS.items():
        if tokens & keywords:
            matched.add(cluster_name)
    return frozenset(matched)


def _cluster_weight(ca: frozenset, cb: frozenset) -> float:
    """
    Multiplier that boosts same-topic pairs and penalises different-topic pairs.

    - No cluster detected in either text → 1.0  (neutral, can't tell)
    - Clusters overlap (same topic)         → 1.3  (boost)
    - Clusters are completely disjoint      → 0.30 (heavy penalty)
    """
    if not ca or not cb:
        return 1.0
    if ca & cb:
        return 1.3
    return 0.30


def _topic_tokens(text: str) -> set:
    """Word tokens after removing stop words AND location words."""
    return _word_tokens(text) - _LOCATION_WORDS


def _bigram_jaccard(tokens_a: set, tokens_b: set) -> float:
    """Jaccard over all token-pair combinations — captures (air, conditioner) regardless
    of alphabetical position of intervening tokens."""
    from itertools import combinations
    if len(tokens_a) < 2 or len(tokens_b) < 2:
        return 0.0
    ba = set(combinations(sorted(tokens_a), 2))
    bb = set(combinations(sorted(tokens_b), 2))
    return len(ba & bb) / len(ba | bb) if (ba | bb) else 0.0


def _levenshtein(s1: str, s2: str) -> int:
    """
    Space-optimised Levenshtein edit distance.
    Early-exits when the length gap alone exceeds the useful threshold (3),
    keeping the average cost negligible for short complaint tokens.
    """
    if s1 == s2:
        return 0
    m, n = len(s1), len(s2)
    if abs(m - n) > 3:          # can't be within threshold — skip
        return abs(m - n)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if s1[i - 1] == s2[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def _fuzzy_token_score(tokens_a: set, tokens_b: set) -> float:
    """
    Fuzzy token match ratio using Levenshtein distance.

    For each token of length >= 4 in set A, check if ANY token in B is within
    edit distance:  1 for tokens of length 4-6,  2 for length 7+.
    Score = symmetric average of (matched_in_A / |A|) and (matched_in_B / |B|).

    Handles typos like:  maintanence↔maintenance,  unhygenic↔unhygienic,
                         recieve↔receive,  cleanliness↔cleanlyness.
    Ignores short tokens (< 4 chars) to avoid false matches like fan↔can.
    """
    eligible_a = [t for t in tokens_a if len(t) >= 4]
    eligible_b = [t for t in tokens_b if len(t) >= 4]
    if not eligible_a or not eligible_b:
        return 0.0

    def _count_matched(src, tgt):
        matched = 0
        for t in src:
            thresh = 1 if len(t) <= 6 else 2
            for u in tgt:
                if abs(len(t) - len(u)) > thresh:
                    continue
                if _levenshtein(t, u) <= thresh:
                    matched += 1
                    break
        return matched

    score_a = _count_matched(eligible_a, eligible_b) / len(eligible_a)
    score_b = _count_matched(eligible_b, eligible_a) / len(eligible_b)
    return (score_a + score_b) / 2


def _hybrid_similarity(a: str, b: str) -> float:
    """
    Five-signal hybrid similarity with cluster-weight gating.

    Signals
    -------
    1. Word Jaccard       (0.30) — exact token overlap after synonym expansion
    2. Topic Jaccard      (0.20) — overlap on topic-only tokens (location words removed)
    3. Bigram Jaccard     (0.10) — co-occurrence pairs; catches "air conditioner" even
                                   when split by alphabetically-between tokens
    4. Char-4gram Jaccard (0.15) — sub-word overlap; handles abbreviations & partials
    5. Fuzzy token score  (0.25) — Levenshtein matching; handles typos like
                                   maintanence, unhygenic, recieve

    Cluster gate
    ------------
    Complaints mapped to DIFFERENT semantic clusters (hygiene vs food_quality)
    receive a 0.30× multiplier, collapsing the score well below any threshold
    even when they share location words like "food court" or "hostel block".
    Same-cluster pairs receive a 1.30× boost.
    """
    wa, wb = _word_tokens(a), _word_tokens(b)
    word_score = len(wa & wb) / len(wa | wb) if (wa | wb) else 0.0

    ta, tb = _topic_tokens(a), _topic_tokens(b)
    if ta and tb:
        topic_score = len(ta & tb) / len(ta | tb)
        bigram_score = _bigram_jaccard(ta, tb)
        fuzzy_score = _fuzzy_token_score(ta, tb)
    else:
        topic_score = word_score
        bigram_score = 0.0
        fuzzy_score = _fuzzy_token_score(wa, wb)

    ca, cb = _char_ngrams(a), _char_ngrams(b)
    char_score = len(ca & cb) / len(ca | cb) if (ca | cb) else 0.0

    raw = (
        0.30 * word_score
        + 0.20 * topic_score
        + 0.10 * bigram_score
        + 0.15 * char_score
        + 0.25 * fuzzy_score
    )

    clusters_a = _get_topic_clusters(a)
    clusters_b = _get_topic_clusters(b)
    weight = _cluster_weight(clusters_a, clusters_b)

    return min(1.0, raw * weight)


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

    THRESHOLD = 0.12          # Minimum score to surface as a candidate
    LIKELY_DUP_THRESHOLD = 0.25  # Score above which we warn the student
    query_text = (body.text or "").strip()

    # Compute improved similarity against each candidate
    scored = []
    for c in candidates:
        text = c.rephrased_text or c.original_text or ""
        score = _hybrid_similarity(query_text, text)
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
MERGE_SIMILARITY_MIN = 0.22   # Minimum hybrid similarity to count as cluster member


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
            score = _hybrid_similarity(new_text, text)
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


@router.delete(
    "/{complaint_id}/self-delete",
    summary="Student deletes own complaint",
    description=(
        "Soft-deletes a complaint. Only the submitting student may call this. "
        "The complaint record is preserved in the DB (is_deleted=True) so "
        "authorities and admins retain the audit trail."
    )
)
async def student_delete_complaint(
    complaint_id: UUID,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select as _sel
    from src.database.models import Complaint as _C
    from src.services.notification_service import notification_service as _ns

    result = await db.execute(_sel(_C).where(_C.id == complaint_id, _C.is_deleted == False))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if complaint.student_roll_no != roll_no:
        raise HTTPException(status_code=403, detail="You can only delete your own complaints")

    if complaint.status in ("Resolved", "Closed"):
        raise HTTPException(status_code=400, detail="Cannot delete a resolved or closed complaint")

    complaint.is_deleted = True
    complaint.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    # Notify authority that the complaint was withdrawn by the student
    if complaint.assigned_authority_id:
        try:
            preview = (complaint.rephrased_text or complaint.original_text or "")[:80]
            await _ns.create_notification(
                db,
                recipient_type="Authority",
                recipient_id=str(complaint.assigned_authority_id),
                complaint_id=complaint_id,
                notification_type="complaint_withdrawn",
                message=f"A student withdrew their complaint: \"{preview}…\""
            )
        except Exception as _e:
            logger.warning(f"Failed to notify authority of withdrawn complaint: {_e}")

    logger.info(f"Complaint {complaint_id} soft-deleted by student {roll_no}")
    return {"success": True, "message": "Complaint deleted successfully"}


__all__ = ["router"]
