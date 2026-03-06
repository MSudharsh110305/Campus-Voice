"""
Petition API endpoints.

Students create petitions for systemic issues.
Dynamic milestone goals: 50 → 100 → 250.
Custom goal + deadline (max 15 days) support.
Petition scope: General (all), Department (same dept), Hostel (hostel students only).
Representative gate: only appointed Student Representatives can create petitions.
Rate limit: 1 petition per representative per 7 days.
Authority approval: petition not visible until authority publishes it.
When a milestone is reached, relevant authority is notified.
When the custom goal is fully met, all signers + creator + authority + admins are notified.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, func, and_, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import get_db, get_current_student, get_current_authority, get_current_user


# ── Rate limit: days between petition creations (default, overridable via system_settings) ──
PETITION_COOLDOWN_DAYS = 7  # fallback if DB setting not found


async def _get_cooldown_days(db: AsyncSession) -> int:
    """Read petition cooldown from system_settings table; fall back to PETITION_COOLDOWN_DAYS."""
    try:
        from src.database.models import SystemSetting
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == "petition_cooldown_days")
        )
        setting = result.scalar_one_or_none()
        if setting:
            return max(0, int(setting.value))
    except Exception:
        pass
    return PETITION_COOLDOWN_DAYS

# ── Valid petition scopes ──────────────────────────────────────────────────────
VALID_SCOPES = {"General", "Department", "Hostel"}


class CreatePetitionBody(BaseModel):
    title: str = Field(..., min_length=10, max_length=255)
    description: str = Field(..., min_length=30, max_length=2000)
    petition_scope: str = Field(default="General")
    department_id: Optional[int] = None  # Auto-set for Department scope
    custom_goal: int = Field(default=50, ge=50, le=10000)
    duration_days: int = Field(default=7, ge=1, le=15)  # Max 15 days

    @validator("petition_scope")
    def validate_scope(cls, v):
        if v not in VALID_SCOPES:
            raise ValueError(f"petition_scope must be one of: {', '.join(VALID_SCOPES)}")
        return v


class RespondPetitionBody(BaseModel):
    response: str = Field(..., min_length=1, max_length=2000)
    status: str = Field(default="Acknowledged")


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/petitions", tags=["Petitions"])

MILESTONES = [50, 100, 250]


def _next_milestone_goal(current_count: int, already_reached: list) -> int:
    """Return the next un-reached milestone, or 250 if all reached."""
    for m in MILESTONES:
        if m not in already_reached:
            return m
    return 250


# ==================== LIST PETITIONS ====================

@router.get("/", summary="List petitions")
async def list_petitions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    include_pending: bool = Query(False),  # Admin only
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Paginated list of petitions. Scope-based visibility.
    Students: only see published petitions matching their dept/hostel.
    Authorities: see published petitions for their dept + global.
    Admins: see ALL petitions (published + pending approval).
    """
    from src.database.models import Petition, PetitionSignature, Student, Authority

    role = current_user.get("role", "")
    user_id = current_user.get("user_id")
    is_admin = role == "Admin"
    is_authority = role == "Authority"

    conditions = []
    if status_filter:
        conditions.append(Petition.status == status_filter)

    # Admin sees all; Authorities see pending+published for their scope; Students see only published
    # BUG-012 fix: authorities must also see unpublished petitions (to approve/reject them)
    if not is_admin and not is_authority:
        conditions.append(Petition.is_published == True)

    # Scope-based visibility filter
    if role == "Student" and user_id:
        try:
            student_q = select(Student).where(Student.roll_no == user_id)
            student_result = await db.execute(student_q)
            student = student_result.scalar_one_or_none()
            if student:
                scope_conditions = [Petition.petition_scope == "General"]
                if student.department_id:
                    scope_conditions.append(
                        and_(
                            Petition.petition_scope == "Department",
                            Petition.department_id == student.department_id,
                        )
                    )
                if student.stay_type == "Hostel":
                    scope_conditions.append(Petition.petition_scope == "Hostel")
                # Also show own pending petitions
                scope_conditions.append(Petition.created_by_roll_no == user_id)
                conditions.append(or_(*scope_conditions))
        except Exception as e:
            logger.warning(f"Could not apply scope filter for student: {e}")

    elif role == "Authority" and user_id:
        try:
            auth_q = select(Authority).where(Authority.id == int(user_id))
            auth_result = await db.execute(auth_q)
            auth = auth_result.scalar_one_or_none()
            if auth:
                scope_conditions = [Petition.petition_scope == "General"]
                if auth.department_id:
                    scope_conditions.append(
                        and_(
                            Petition.petition_scope == "Department",
                            Petition.department_id == auth.department_id,
                        )
                    )
                scope_conditions.append(Petition.petition_scope == "Hostel")
                conditions.append(or_(*scope_conditions))
        except Exception as e:
            logger.warning(f"Could not apply scope filter for authority: {e}")
    # Admin: no scope conditions → sees everything

    count_q = select(func.count()).select_from(Petition)
    if conditions:
        count_q = count_q.where(and_(*conditions))
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Petition)
        .options(selectinload(Petition.creator), selectinload(Petition.department))
        .order_by(Petition.submitted_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if conditions:
        q = q.where(and_(*conditions))
    result = await db.execute(q)
    petitions = result.scalars().all()

    # Batch-check which ones the caller (student) has signed
    roll_no = user_id if role == "Student" else None
    signed_ids: set = set()
    if roll_no and petitions:
        ids = [p.id for p in petitions]
        sig_q = select(PetitionSignature.petition_id).where(
            and_(
                PetitionSignature.petition_id.in_(ids),
                PetitionSignature.student_roll_no == roll_no,
            )
        )
        sig_result = await db.execute(sig_q)
        signed_ids = {row[0] for row in sig_result.fetchall()}

    items = [_petition_to_dict(p, signed=(p.id in signed_ids)) for p in petitions]
    return {"petitions": items, "total": total, "skip": skip, "limit": limit}


# ==================== CHECK REPRESENTATIVE STATUS ====================
# IMPORTANT: Must be defined BEFORE /{petition_id} to avoid UUID parse error on "me"

@router.get("/me/status", summary="Get current student's representative status")
async def get_my_rep_status(
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Returns whether the student is an appointed representative and can create petitions."""
    from src.database.models import StudentRepresentative, Petition

    # Check if student is an active representative (may have multiple roles)
    rep_q = select(StudentRepresentative).where(
        and_(
            StudentRepresentative.student_roll_no == roll_no,
            StudentRepresentative.is_active == True,
        )
    )
    rep_result = await db.execute(rep_q)
    reps = rep_result.scalars().all()

    is_representative = len(reps) > 0
    # Collect all scopes this student has (e.g. ["Department", "Hostel"])
    scopes = list({r.scope for r in reps})

    # Read configurable cooldown from DB
    cooldown_days = await _get_cooldown_days(db)

    # Check cooldown
    can_create = False
    cooldown_remaining = 0
    if is_representative:
        if cooldown_days == 0:
            # Rate limit disabled by admin
            can_create = True
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(days=cooldown_days)
            recent_q = select(func.count()).select_from(Petition).where(
                and_(
                    Petition.created_by_roll_no == roll_no,
                    Petition.submitted_at >= cutoff,
                )
            )
            recent_count = (await db.execute(recent_q)).scalar() or 0
            can_create = recent_count == 0

            if not can_create:
                # Find most recent petition to calculate remaining cooldown
                last_q = select(Petition.submitted_at).where(
                    Petition.created_by_roll_no == roll_no
                ).order_by(Petition.submitted_at.desc()).limit(1)
                last_result = await db.execute(last_q)
                last_submitted = last_result.scalar_one_or_none()
                if last_submitted:
                    if last_submitted.tzinfo is None:
                        last_submitted = last_submitted.replace(tzinfo=timezone.utc)
                    next_allowed = last_submitted + timedelta(days=cooldown_days)
                    cooldown_remaining = max(0, (next_allowed - datetime.now(timezone.utc)).days)

    # Primary scope for display: prefer Department if both, else whichever exists
    primary_scope = None
    if "Department" in scopes:
        primary_scope = "Department"
    elif scopes:
        primary_scope = scopes[0]

    return {
        "is_representative": is_representative,
        "can_create": can_create,
        "scope": primary_scope,
        "scopes": scopes,  # All scopes this student holds
        "cooldown_days": cooldown_days,
        "cooldown_remaining": cooldown_remaining,
    }


# ==================== CREATE PETITION ====================

@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create petition")
async def create_petition(
    body: CreatePetitionBody,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Create a new petition. The creator automatically signs it.

    Guards:
    - Representative gate: student must be an appointed Student Representative
    - Rate limit: 1 petition per representative per 7 days
    - Scope restriction: Department reps → Department or General; Hostel reps → Hostel or General
    - Hostel scope: only allowed for hostel students
    """
    from src.database.models import Petition, PetitionSignature, Student, StudentRepresentative

    # Load student
    student_q = select(Student).where(Student.roll_no == roll_no)
    student_result = await db.execute(student_q)
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Representative gate — student may hold multiple rep roles
    rep_q = select(StudentRepresentative).where(
        and_(
            StudentRepresentative.student_roll_no == roll_no,
            StudentRepresentative.is_active == True,
        )
    )
    rep_result = await db.execute(rep_q)
    reps = rep_result.scalars().all()
    if not reps:
        raise HTTPException(
            status_code=403,
            detail="Only appointed Student Representatives can create petitions. Contact your department authority to become a representative."
        )

    rep_scopes = {r.scope for r in reps}

    # Scope restriction: General is always allowed.
    # Department scope requires a Department rep; Hostel scope requires a Hostel rep.
    if body.petition_scope == "Hostel" and "Hostel" not in rep_scopes:
        raise HTTPException(
            status_code=400,
            detail="Department representatives cannot create Hostel-scoped petitions"
        )
    if body.petition_scope == "Department" and "Department" not in rep_scopes:
        raise HTTPException(
            status_code=400,
            detail="Hostel representatives cannot create Department-scoped petitions"
        )

    # Hostel scope: only hostel students
    if body.petition_scope == "Hostel" and student.stay_type != "Hostel":
        raise HTTPException(
            status_code=400,
            detail="Only hostel students can create a Hostel-scoped petition"
        )

    # Rate limit: no petition in last cooldown_days (configurable by admin)
    cooldown_days = await _get_cooldown_days(db)
    if cooldown_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=cooldown_days)
        recent_q = select(func.count()).select_from(Petition).where(
            and_(
                Petition.created_by_roll_no == roll_no,
                Petition.submitted_at >= cutoff,
            )
        )
        recent_count = (await db.execute(recent_q)).scalar() or 0
        if recent_count > 0:
            raise HTTPException(
                status_code=429,
                detail=f"You can only create 1 petition every {cooldown_days} days. Please wait before creating another."
            )

    # Determine department_id
    dept_id = None
    if body.petition_scope == "Department":
        dept_id = student.department_id
        if not dept_id:
            raise HTTPException(status_code=400, detail="Your account has no department set; cannot create a Department petition")

    deadline = datetime.now(timezone.utc) + timedelta(days=body.duration_days)

    petition = Petition(
        title=body.title.strip(),
        description=body.description.strip(),
        created_by_roll_no=roll_no,
        petition_scope=body.petition_scope,
        department_id=dept_id,
        category_id=None,
        signature_count=1,
        custom_goal=body.custom_goal,
        milestone_goal=body.custom_goal,
        deadline=deadline,
        goal_reached_notified=False,
        milestones_reached=[],
        is_published=False,  # Requires authority approval before visible
    )
    db.add(petition)
    await db.flush()

    sig = PetitionSignature(petition_id=petition.id, student_roll_no=roll_no)
    db.add(sig)
    await db.commit()

    # Reload with relationships to avoid greenlet_spawn error
    q = (
        select(Petition)
        .options(selectinload(Petition.creator), selectinload(Petition.department))
        .where(Petition.id == petition.id)
    )
    result = await db.execute(q)
    petition = result.scalar_one()

    # Notify relevant authority for approval
    await _notify_authority_for_approval(db, petition)
    await db.commit()

    logger.info(
        f"Petition '{body.title[:40]}' created by representative {roll_no} "
        f"(scope={body.petition_scope}, goal={body.custom_goal}, days={body.duration_days})"
    )
    return _petition_to_dict(petition, signed=True)


# ==================== GET PETITION DETAIL ====================

@router.get("/{petition_id}", summary="Get petition detail")
async def get_petition(
    petition_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from src.database.models import Petition, PetitionSignature

    q = (
        select(Petition)
        .options(selectinload(Petition.creator), selectinload(Petition.department))
        .where(Petition.id == petition_id)
    )
    result = await db.execute(q)
    petition = result.scalar_one_or_none()
    if not petition:
        raise HTTPException(status_code=404, detail="Petition not found")

    role = current_user.get("role", "")
    user_id = current_user.get("user_id")

    # Non-admin can only see published petitions
    if role != "Admin" and not petition.is_published:
        # Allow creator to see their own pending petition
        if not (role == "Student" and user_id == petition.created_by_roll_no):
            raise HTTPException(status_code=404, detail="Petition not found")

    roll_no = user_id if role == "Student" else None
    signed = False
    signed_at = None
    if roll_no:
        sig_q = select(PetitionSignature).where(
            and_(
                PetitionSignature.petition_id == petition_id,
                PetitionSignature.student_roll_no == roll_no,
            )
        )
        sig_result = await db.execute(sig_q)
        sig = sig_result.scalar_one_or_none()
        if sig:
            signed = True
            signed_at = sig.signed_at

    return {**_petition_to_dict(petition, signed=signed), "my_signed_at": signed_at}


# ==================== SIGN / UNSIGN ====================

@router.post("/{petition_id}/sign", summary="Sign or unsign a petition (toggle)")
async def sign_petition(
    petition_id: UUID,
    roll_no: str = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Toggle signature. If already signed → unsign. Otherwise → sign."""
    from src.database.models import Petition, PetitionSignature

    q = select(Petition).where(Petition.id == petition_id)
    result = await db.execute(q)
    petition = result.scalar_one_or_none()
    if not petition:
        raise HTTPException(status_code=404, detail="Petition not found")
    if not petition.is_published:
        raise HTTPException(status_code=400, detail="This petition is pending authority approval and cannot be signed yet")
    if petition.status in ("Resolved", "Closed"):
        raise HTTPException(status_code=400, detail="Cannot sign a closed petition")

    # Check deadline
    if petition.deadline and datetime.now(timezone.utc) > petition.deadline:
        raise HTTPException(status_code=400, detail="This petition has expired and can no longer be signed")

    # Creator cannot unsign their own petition
    if roll_no == petition.created_by_roll_no:
        raise HTTPException(status_code=400, detail="You are the creator — cannot unsign your own petition")

    existing_q = select(PetitionSignature).where(
        and_(
            PetitionSignature.petition_id == petition_id,
            PetitionSignature.student_roll_no == roll_no,
        )
    )
    existing_result = await db.execute(existing_q)
    existing_sig = existing_result.scalar_one_or_none()

    if existing_sig:
        # Unsign
        await db.execute(
            delete(PetitionSignature).where(PetitionSignature.id == existing_sig.id)
        )
        petition.signature_count = max(0, (petition.signature_count or 0) - 1)
        await db.commit()
        return {"signed": False, "signature_count": petition.signature_count}

    # Sign
    sig = PetitionSignature(petition_id=petition_id, student_roll_no=roll_no)
    db.add(sig)
    petition.signature_count = (petition.signature_count or 0) + 1
    new_count = petition.signature_count

    # Check milestone triggers (standard 50/100/250)
    reached = list(petition.milestones_reached or [])
    newly_triggered = [m for m in MILESTONES if m <= new_count and m not in reached]

    for milestone in newly_triggered:
        reached.append(milestone)
        petition.milestones_reached = reached
        petition.milestone_goal = _next_milestone_goal(new_count, reached)
        await _notify_milestone(db, petition, milestone, roll_no)

    # Check custom goal reached
    custom_goal = petition.custom_goal or petition.milestone_goal or 50
    if new_count >= custom_goal and not petition.goal_reached_notified:
        petition.goal_reached_notified = True
        await _notify_goal_reached(db, petition, roll_no)

    await db.commit()
    return {"signed": True, "signature_count": petition.signature_count}


# ==================== AUTHORITY APPROVE / PUBLISH ====================

@router.post("/{petition_id}/approve", summary="Authority approves (publishes) a petition")
async def approve_petition(
    petition_id: UUID,
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db),
):
    """Authority publishes a pending petition, making it visible to eligible students."""
    from src.database.models import Petition, Notification

    q = (
        select(Petition)
        .options(selectinload(Petition.creator))
        .where(Petition.id == petition_id)
    )
    result = await db.execute(q)
    petition = result.scalar_one_or_none()
    if not petition:
        raise HTTPException(status_code=404, detail="Petition not found")

    if petition.is_published:
        return {"success": True, "message": "Petition is already published", "is_published": True}

    petition.is_published = True
    petition.responded_by_id = authority_id
    petition.responded_at = datetime.now(timezone.utc)

    # Notify creator that petition has been approved
    if petition.created_by_roll_no:
        db.add(Notification(
            recipient_type="Student",
            recipient_id=petition.created_by_roll_no,
            complaint_id=None,
            notification_type="petition_approved",
            message=(
                f'Your petition "{petition.title[:80]}" has been approved by an authority '
                f'and is now live! Students can start signing it.'
            ),
        ))

    await db.commit()
    logger.info(f"Petition {petition_id} approved by authority {authority_id}")

    q = (
        select(Petition)
        .options(selectinload(Petition.creator), selectinload(Petition.department))
        .where(Petition.id == petition_id)
    )
    result = await db.execute(q)
    petition = result.scalar_one()
    return {"success": True, "is_published": True, **_petition_to_dict(petition)}


# ==================== AUTHORITY REJECT ====================

@router.post("/{petition_id}/reject", summary="Authority rejects a petition")
async def reject_petition(
    petition_id: UUID,
    body: RespondPetitionBody,
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db),
):
    """Authority rejects a pending petition with a reason."""
    from src.database.models import Petition, Notification

    q = select(Petition).where(Petition.id == petition_id)
    result = await db.execute(q)
    petition = result.scalar_one_or_none()
    if not petition:
        raise HTTPException(status_code=404, detail="Petition not found")

    petition.status = "Closed"
    petition.authority_response = body.response.strip()
    petition.responded_by_id = authority_id
    petition.responded_at = datetime.now(timezone.utc)

    if petition.created_by_roll_no:
        db.add(Notification(
            recipient_type="Student",
            recipient_id=petition.created_by_roll_no,
            complaint_id=None,
            notification_type="petition_rejected",
            message=(
                f'Your petition "{petition.title[:80]}" was not approved. '
                f'Reason: {body.response[:200]}'
            ),
        ))

    await db.commit()
    logger.info(f"Petition {petition_id} rejected by authority {authority_id}")
    return {"success": True, "status": "Closed"}


# ==================== AUTHORITY RESPOND ====================

@router.post("/{petition_id}/respond", summary="Authority responds to petition")
async def respond_to_petition(
    petition_id: UUID,
    body: RespondPetitionBody,
    authority_id: int = Depends(get_current_authority),
    db: AsyncSession = Depends(get_db),
):
    """Authority posts an official response and marks the petition as Acknowledged/Resolved."""
    from src.database.models import Petition, PetitionSignature, Notification

    q = select(Petition).where(Petition.id == petition_id)
    result = await db.execute(q)
    petition = result.scalar_one_or_none()
    if not petition:
        raise HTTPException(status_code=404, detail="Petition not found")

    response_text = body.response.strip()
    new_status = body.status
    if new_status not in ("Acknowledged", "Resolved", "Closed"):
        raise HTTPException(status_code=400, detail="Invalid status")

    petition.authority_response = response_text
    petition.status = new_status
    petition.responded_by_id = authority_id
    petition.responded_at = datetime.now(timezone.utc)

    # Notify all signers
    sig_q = select(PetitionSignature.student_roll_no).where(
        PetitionSignature.petition_id == petition_id
    )
    sig_result = await db.execute(sig_q)
    signers = [row[0] for row in sig_result.fetchall()]

    for signer_roll_no in signers:
        notif = Notification(
            recipient_type="Student",
            recipient_id=signer_roll_no,
            complaint_id=None,
            notification_type="petition_response",
            message=(
                f'Your petition "{petition.title[:60]}" has received an official response '
                f'and is now {new_status}. Response: "{response_text[:120]}..."'
            ),
        )
        db.add(notif)

    await db.commit()
    logger.info(f"Petition {petition_id} responded by authority {authority_id}")
    return {"success": True, "status": new_status}


# ==================== HELPERS ====================

def _petition_to_dict(petition, *, signed: bool = False) -> dict:
    reached = petition.milestones_reached or []
    custom_goal = petition.custom_goal or petition.milestone_goal or 50
    goal = petition.milestone_goal or 50
    count = petition.signature_count or 0
    progress_pct = min(round(count / custom_goal * 100), 100) if custom_goal > 0 else 100
    creator_name = None
    if petition.creator:
        creator_name = petition.creator.name
    dept_name = None
    if petition.department:
        dept_name = petition.department.name

    # Days remaining
    days_remaining = None
    deadline = getattr(petition, "deadline", None)
    if deadline:
        now = datetime.now(timezone.utc)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        delta = (deadline - now).days
        days_remaining = max(delta, 0)

    return {
        "id": str(petition.id),
        "title": petition.title,
        "description": petition.description,
        "created_by_roll_no": petition.created_by_roll_no,
        "creator_name": creator_name,
        "department_name": dept_name,
        "petition_scope": getattr(petition, "petition_scope", "General"),
        "is_published": getattr(petition, "is_published", False),
        "signature_count": count,
        "custom_goal": custom_goal,
        "milestone_goal": goal,
        "milestones_reached": reached,
        "progress_pct": progress_pct,
        "deadline": deadline.isoformat() if deadline else None,
        "days_remaining": days_remaining,
        "goal_reached_notified": getattr(petition, "goal_reached_notified", False),
        "status": petition.status,
        "authority_response": petition.authority_response,
        "responded_at": petition.responded_at.isoformat() if petition.responded_at else None,
        "submitted_at": petition.submitted_at.isoformat() if petition.submitted_at else None,
        "signed_by_me": signed,
    }


async def _notify_authority_for_approval(db, petition):
    """Notify the relevant authority to approve/publish the petition."""
    from src.database.models import Authority, Notification

    try:
        authority_id = None
        if petition.petition_scope == "Department" and petition.department_id:
            auth_q = select(Authority).where(
                and_(
                    Authority.authority_type == "HOD",
                    Authority.department_id == petition.department_id,
                    Authority.is_active == True,
                )
            ).limit(1)
            auth_result = await db.execute(auth_q)
            auth = auth_result.scalar_one_or_none()
            if auth:
                authority_id = auth.id

        if petition.petition_scope == "Hostel":
            # Notify Senior Deputy Warden
            auth_q = select(Authority).where(
                and_(
                    Authority.authority_type.in_(["Senior Deputy Warden", "Men's Hostel Deputy Warden", "Women's Hostel Deputy Warden"]),
                    Authority.is_active == True,
                )
            ).limit(1)
            auth_result = await db.execute(auth_q)
            auth = auth_result.scalar_one_or_none()
            if auth:
                authority_id = auth.id

        if not authority_id:
            # Fall back to Admin Officer
            ao_q = select(Authority).where(
                and_(Authority.authority_type == "Admin Officer", Authority.is_active == True)
            ).limit(1)
            ao_result = await db.execute(ao_q)
            ao = ao_result.scalar_one_or_none()
            if ao:
                authority_id = ao.id

        if authority_id:
            db.add(Notification(
                recipient_type="Authority",
                recipient_id=str(authority_id),
                complaint_id=None,
                notification_type="petition_pending_approval",
                message=(
                    f'A new petition requires your approval before it goes live.\n'
                    f'Title: "{petition.title}"\n'
                    f'Scope: {getattr(petition, "petition_scope", "General")}\n'
                    f'Creator: {petition.created_by_roll_no}\n'
                    f'Description: {petition.description[:200]}'
                ),
            ))
    except Exception as e:
        logger.warning(f"Could not notify authority for petition approval: {e}")


async def _notify_milestone(db, petition, milestone: int, triggering_roll_no: str):
    """Notify relevant authority and all signers when a milestone is hit."""
    from src.database.models import Authority, PetitionSignature, Notification

    # Find authority to notify
    authority_id = None
    try:
        if petition.department_id:
            auth_q = select(Authority).where(
                and_(
                    Authority.authority_type == "HOD",
                    Authority.department_id == petition.department_id,
                    Authority.is_active == True,
                )
            ).limit(1)
            auth_result = await db.execute(auth_q)
            auth = auth_result.scalar_one_or_none()
            if auth:
                authority_id = auth.id
        if not authority_id:
            ao_q = select(Authority).where(
                and_(Authority.authority_type == "Admin Officer", Authority.is_active == True)
            ).limit(1)
            ao_result = await db.execute(ao_q)
            ao = ao_result.scalar_one_or_none()
            if ao:
                authority_id = ao.id
    except Exception as e:
        logger.warning(f"Could not find authority for milestone notification: {e}")

    if authority_id:
        db.add(Notification(
            recipient_type="Authority",
            recipient_id=str(authority_id),
            complaint_id=None,
            notification_type="petition_milestone",
            message=(
                f'Petition milestone reached: {milestone} signatures!\n'
                f'Petition: "{petition.title}"\n'
                f'Description: {petition.description[:200]}\n'
                f'Total signatures: {petition.signature_count}'
            ),
        ))

    # Notify all current signers
    try:
        sig_q = select(PetitionSignature.student_roll_no).where(
            PetitionSignature.petition_id == petition.id
        )
        sig_result = await db.execute(sig_q)
        signers = [row[0] for row in sig_result.fetchall()]
        for sroll in signers:
            db.add(Notification(
                recipient_type="Student",
                recipient_id=sroll,
                complaint_id=None,
                notification_type="petition_milestone",
                message=(
                    f'Your petition "{petition.title[:60]}" just hit {milestone} signatures! '
                    f'The relevant authority has been formally notified.'
                ),
            ))
    except Exception as e:
        logger.warning(f"Could not notify signers for milestone: {e}")


async def _notify_goal_reached(db, petition, triggering_roll_no: str):
    """Notify everyone when the custom goal is fully met."""
    from src.database.models import Authority, PetitionSignature, Notification

    custom_goal = petition.custom_goal or petition.milestone_goal or 50

    # Notify all signers
    try:
        sig_q = select(PetitionSignature.student_roll_no).where(
            PetitionSignature.petition_id == petition.id
        )
        sig_result = await db.execute(sig_q)
        signers = [row[0] for row in sig_result.fetchall()]
        for sroll in signers:
            db.add(Notification(
                recipient_type="Student",
                recipient_id=sroll,
                complaint_id=None,
                notification_type="petition_goal_reached",
                message=(
                    f'Goal reached! The petition "{petition.title[:60]}" has collected '
                    f'{petition.signature_count} signatures — the target of {custom_goal} has been met! '
                    f'The authorities have been formally notified.'
                ),
            ))
    except Exception as e:
        logger.warning(f"Goal-reached: could not notify signers: {e}")

    # Notify the creator (separately in case they didn't sign)
    if petition.created_by_roll_no and petition.created_by_roll_no != triggering_roll_no:
        db.add(Notification(
            recipient_type="Student",
            recipient_id=petition.created_by_roll_no,
            complaint_id=None,
            notification_type="petition_goal_reached",
            message=(
                f'Your petition "{petition.title[:60]}" has reached its goal of {custom_goal} signatures! '
                f'The relevant authority and admin team have been notified.'
            ),
        ))

    # Notify relevant authority (HOD or Admin Officer)
    try:
        authority_id = None
        if petition.department_id:
            auth_q = select(Authority).where(
                and_(
                    Authority.authority_type == "HOD",
                    Authority.department_id == petition.department_id,
                    Authority.is_active == True,
                )
            ).limit(1)
            auth_result = await db.execute(auth_q)
            auth = auth_result.scalar_one_or_none()
            if auth:
                authority_id = auth.id

        if not authority_id:
            ao_q = select(Authority).where(
                and_(Authority.authority_type == "Admin Officer", Authority.is_active == True)
            ).limit(1)
            ao_result = await db.execute(ao_q)
            ao = ao_result.scalar_one_or_none()
            if ao:
                authority_id = ao.id

        if authority_id:
            db.add(Notification(
                recipient_type="Authority",
                recipient_id=str(authority_id),
                complaint_id=None,
                notification_type="petition_goal_reached",
                message=(
                    f'ACTION REQUIRED: Petition "{petition.title}" has reached its signature goal of {custom_goal}!\n'
                    f'Total signatures: {petition.signature_count}\n'
                    f'Description: {petition.description[:300]}'
                ),
            ))
    except Exception as e:
        logger.warning(f"Goal-reached: could not notify authority: {e}")

    # Notify all Admins
    try:
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
                notification_type="petition_goal_reached",
                message=(
                    f'Petition goal reached: "{petition.title}" has collected {petition.signature_count} '
                    f'signatures (target: {custom_goal}). Formal authority has been notified.'
                ),
            ))
    except Exception as e:
        logger.warning(f"Goal-reached: could not notify admins: {e}")
