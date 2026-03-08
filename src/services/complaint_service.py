"""
Complaint service with main business logic.

✅ UPDATED: Binary image storage support
✅ UPDATED: Image verification integration
✅ UPDATED: No image_url field usage
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import UploadFile

from src.database.models import Complaint, Student, ComplaintCategory, StatusUpdate
from src.repositories.complaint_repo import ComplaintRepository
from src.repositories.student_repo import StudentRepository
from src.services.llm_service import llm_service
from src.services.authority_service import authority_service
from src.services.notification_service import notification_service
from src.services.spam_detection import spam_detection_service
from src.services.image_verification import image_verification_service
from src.utils.file_upload import file_upload_handler
from src.utils.exceptions import InvalidFileTypeError, FileTooLargeError, FileUploadError
from src.config.constants import PRIORITY_SCORES  # kept for external callers

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Deterministic category override layer
# Called AFTER LLM categorization to catch known LLM mistakes using keyword rules.
# Pure Python — no LLM call, no DB call.
# ---------------------------------------------------------------------------

# Keywords that unconditionally force "Disciplinary Committee" regardless of LLM output.
# ONLY for clear student-on-student physical/criminal misconduct.
# Teacher/faculty misconduct goes to Department HOD, NOT DC.
_STUDENT_DISCIPLINARY_KEYWORDS = [
    "ragging", "rag ", " rag,", "rags",
    "bully", "bullying",
    "assault",
    "molest",
    "rape",
    "hate speech",
    "eve teasing",
    "physical fight", "physical violence",
]

# These are context-dependent: trigger Disciplinary ONLY when NO authority figure
# (warden/HOD/faculty) is mentioned as the subject.
_AUTHORITY_MISCONDUCT_KEYWORDS = [
    "bribery", "bribe", "corrupt", "corruption", "extortion",
    "demanding money", "demand money", "taking money",
    "abuse", "abusing",
    "threat", "threaten",
    # "harass" moved here — context-dependent:
    # student-on-student harassment → DC; faculty/teacher harassment → Department
    "harass", "harassment", "harassing",
    # Discrimination is also context-dependent (faculty discrimination in marks → Dept)
    "discrimination",
    "fight", "fighting",
]

# Authority figures — if ANY of these appear as the subject of the complaint,
# skip the Disciplinary override and let bypass routing handle it instead.
_HOSTEL_AUTHORITY_SUBJECT_KEYWORDS = [
    "warden", "deputy warden", "senior deputy warden", "sdw",
]
_DEPT_AUTHORITY_SUBJECT_KEYWORDS = [
    "hod", "head of department", "head of dept",
    "professor", "faculty", "lecturer",
    "teacher", "instructor",
    # "staff" handled separately via _is_staff_in_academic_context()
]

# Academic context words — used to detect "staff" in an academic/dept context
_ACADEMIC_CONTEXT_KEYWORDS = [
    "lab", "class", "exam", "lecture", "department", "dept", "course",
    "subject", "marks", "grade", "assignment", "practical", "seminar",
    "timetable", "curriculum", "syllabus", "internal", "external",
    "classrooms", "classroom",
]


def _is_staff_in_academic_context(text_lower: str) -> bool:
    """Return True if 'staff'/'staffs' appears alongside academic/dept keywords."""
    if "staff" not in text_lower:
        return False
    return any(kw in text_lower for kw in _ACADEMIC_CONTEXT_KEYWORDS)


# ---------------------------------------------------------------------------
# Shortform normalization
# Called BEFORE LLM categorization so the LLM sees full English words.
# ---------------------------------------------------------------------------

import re as _re

# (regex_pattern, replacement) pairs — applied in order (longer patterns first)
_SHORTFORM_SUBS = [
    # Locations / facilities
    (r'\bfc\b',       'food court'),
    (r'\bwc\b',       'washroom'),
    (r'\blib\b',      'library'),
    (r'\bcant\b',     'canteen'),
    # Roles / titles
    (r'\bhod\b',      'head of department'),
    (r'\bsdw\b',      'senior deputy warden'),
    # Common terms
    (r'\bdept\b',     'department'),
    (r'\bwifi\b',     'wi-fi internet connection'),
    (r'\bnet\b',      'internet'),
]


def _normalize_complaint_text(text: str) -> str:
    """
    Expand common campus shortforms so the LLM categorizes correctly.
    Uses word-boundary matching and preserves original capitalisation of
    unmatched words. Context-dependent shortforms (ac) are handled separately.
    """
    result = text
    for pattern, replacement in _SHORTFORM_SUBS:
        result = _re.sub(pattern, replacement, result, flags=_re.IGNORECASE)

    # 'ac' = air conditioner by default; but keep as-is if 'coordinator' or
    # 'academic' is in the surrounding 40-char window (academic coordinator).
    def _replace_ac(m: _re.Match) -> str:
        start = max(0, m.start() - 40)
        end = min(len(result), m.end() + 40)
        window = result[start:end].lower()
        if 'coordinator' in window or 'academic coordinator' in window:
            return 'academic coordinator'
        return 'air conditioner'

    result = _re.sub(r'\bac\b', _replace_ac, result, flags=_re.IGNORECASE)
    return result


# ---------------------------------------------------------------------------
# Unethical academic manipulation — pre-LLM spam keywords
# These requests are not valid complaints; they are bribe-like grade requests.
# ---------------------------------------------------------------------------
_UNETHICAL_ACADEMIC_PATTERNS = [
    r'\bincrease\b.{0,30}\bmarks?\b',
    r'\bgive\b.{0,20}\bmarks?\b',
    r'\badd\b.{0,20}\bmarks?\b',
    r'\bchange\b.{0,20}\bmarks?\b',
    r'\bincrease\b.{0,30}\bgrades?\b',
    r'\bgive\b.{0,20}\bgrades?\b',
    r'\bplease pass\b',
    r'\bkindly pass\b',
    r'\bmake us pass\b',
    r'\bmake me pass\b',
    r'\bpass us\b',
    r'\bgive passing\b',
    r'\bincrease internal\b',
    r'\bincrease external\b',
]


def _is_unethical_academic_request(text: str) -> bool:
    """Return True if the complaint is a grade-manipulation bribe attempt."""
    text_lower = text.lower()
    for pattern in _UNETHICAL_ACADEMIC_PATTERNS:
        if _re.search(pattern, text_lower):
            return True
    return False

# Keywords that indicate physical infrastructure / hygiene — these complaints belong
# to General (Admin Officer), never to Department (HOD).
_INFRA_GENERAL_KEYWORDS = [
    "bathroom", "toilet", "restroom", "washroom", "urinal", "lavatory",
    "lights", "light bulb", "bulb", "tube light", "fluorescent",
    "electricity", "power cut", "no power", "no electricity",
    "water supply", "drinking water", "tap water", "water pipe", "plumbing",
    "wifi", "wi-fi", "internet connection", "network connection",
]

# Non-hostel location phrases — if the complaint text mentions these it is almost
# certainly NOT a hostel complaint even if the LLM thinks so.
_NON_HOSTEL_LOCATION_KEYWORDS = [
    "cse block", "ece block", "mech block", "it block", "eee block",
    "eie block", "bio block", "aero block", "civil block", "raa block",
    "mba block", "aids block",
    "department block", "academic block", "main block",
    "classroom", "lecture hall", "seminar hall", "lab block",
    "canteen", "food court", "library", "reading room",
]

# Strong hostel location phrases — if any of these appear the complaint IS hostel
_HOSTEL_LOCATION_KEYWORDS = [
    "hostel", "hostel room", "hostel mess", "hostel block",
    "hostel corridor", "hostel gate", "hostel bathroom",
    "hostel water", "hostel electricity", "hostel wifi",
    "mess food", "mess hall", "dorm", "dormitory", "boarding",
    "hostel warden", "warden room",
]


def _override_category(text: str, llm_category: str, student_gender: str) -> str:
    """
    Deterministic post-processing layer applied after LLM categorization.

    Catches known LLM mistakes using keyword rules without any LLM or DB calls.
    Logs every override with the reason.

    Args:
        text: Original complaint text (pre-shortform-expansion)
        llm_category: Category returned by the LLM (or fallback)
        student_gender: Student's gender ("Male", "Female", "Other", or "")

    Returns:
        Final category string (may be the same as llm_category or an override)
    """
    text_lower = text.lower()

    # ------------------------------------------------------------------ #
    # Pre-compute authority subject flags (used in OVERRIDE 0 and 1)      #
    # ------------------------------------------------------------------ #
    _is_about_hostel_authority = any(kw in text_lower for kw in _HOSTEL_AUTHORITY_SUBJECT_KEYWORDS)
    _is_about_dept_authority = (
        any(kw in text_lower for kw in _DEPT_AUTHORITY_SUBJECT_KEYWORDS)
        or _is_staff_in_academic_context(text_lower)
    )
    _is_about_any_authority = _is_about_hostel_authority or _is_about_dept_authority

    # ------------------------------------------------------------------ #
    # OVERRIDE 0: Un-DC complaints that LLM wrongly sent to DC            #
    # If LLM returned "Disciplinary Committee" but the complaint is       #
    # ABOUT a named authority (warden/HOD/faculty/staff in dept context), #
    # DC is wrong. DC is only for student-on-student misconduct.          #
    # Authority misconduct stays in its category and uses bypass routing. #
    # ------------------------------------------------------------------ #
    if llm_category == "Disciplinary Committee":
        if _is_about_hostel_authority:
            corrected = "Women's Hostel" if student_gender == "Female" else "Men's Hostel"
            logger.warning(
                f"Category override: Disciplinary Committee -> {corrected} "
                f"| reason: LLM wrongly assigned DC for hostel authority complaint | text: {text[:80]}"
            )
            return corrected
        elif _is_about_dept_authority:
            logger.warning(
                f"Category override: Disciplinary Committee -> Department "
                f"| reason: LLM wrongly assigned DC for dept/teacher/staff complaint | text: {text[:80]}"
            )
            return "Department"

    # ------------------------------------------------------------------ #
    # OVERRIDE 1: Disciplinary Committee                                   #
    # ONLY for student-on-student misconduct (ragging, assault, etc.).    #
    # Complaints about authorities (warden/HOD/faculty) stay in their     #
    # category and use authority bypass routing instead.                  #
    # ------------------------------------------------------------------ #

    # Step 1a: Always-Disciplinary keywords (physical student misconduct, no exceptions)
    for kw in _STUDENT_DISCIPLINARY_KEYWORDS:
        if kw in text_lower:
            if llm_category != "Disciplinary Committee":
                logger.warning(
                    f"Category override: {llm_category} -> Disciplinary Committee "
                    f"| reason: student-misconduct keyword '{kw}' | text: {text[:80]}"
                )
            return "Disciplinary Committee"

    # Step 1b: Context-dependent misconduct keywords — only trigger DC when
    # the complaint is NOT about a named authority (warden/HOD/faculty/staff).
    # If an authority is the subject, bypass routing handles it.
    if not _is_about_any_authority:
        for kw in _AUTHORITY_MISCONDUCT_KEYWORDS:
            if kw in text_lower:
                if llm_category != "Disciplinary Committee":
                    logger.warning(
                        f"Category override: {llm_category} -> Disciplinary Committee "
                        f"| reason: misconduct keyword '{kw}' (no authority named) | text: {text[:80]}"
                    )
                return "Disciplinary Committee"
    else:
        # Log that we're skipping Disciplinary override because complaint is about an authority
        for kw in _AUTHORITY_MISCONDUCT_KEYWORDS:
            if kw in text_lower:
                logger.info(
                    f"Skipping Disciplinary override for '{kw}' — complaint is about an authority "
                    f"(hostel_auth={_is_about_hostel_authority}, dept_auth={_is_about_dept_authority}) "
                    f"| will use bypass routing | text: {text[:80]}"
                )
                break

    # ------------------------------------------------------------------ #
    # OVERRIDE 2: Department -> General                                    #
    # If LLM says Department but text is about physical infra/hygiene.    #
    # ------------------------------------------------------------------ #
    if llm_category == "Department":
        for kw in _INFRA_GENERAL_KEYWORDS:
            if kw in text_lower:
                logger.warning(
                    f"Category override: Department -> General "
                    f"| reason: infra/hygiene keyword '{kw}' | text: {text[:80]}"
                )
                return "General"

    # ------------------------------------------------------------------ #
    # OVERRIDE 3: Hostel -> General                                        #
    # If LLM says hostel but text clearly places the issue OUTSIDE hostel. #
    # Only override when text has a non-hostel location keyword AND no     #
    # strong hostel location keyword is present.                           #
    # ------------------------------------------------------------------ #
    if llm_category in ("Men's Hostel", "Women's Hostel"):
        has_hostel_location = any(kw in text_lower for kw in _HOSTEL_LOCATION_KEYWORDS)
        if not has_hostel_location:
            for kw in _NON_HOSTEL_LOCATION_KEYWORDS:
                if kw in text_lower:
                    logger.warning(
                        f"Category override: {llm_category} -> General "
                        f"| reason: non-hostel location keyword '{kw}' | text: {text[:80]}"
                    )
                    return "General"

    return llm_category


async def check_expired_image_deadlines(db: AsyncSession) -> int:
    """
    Find complaints whose 24-hour image upload grace period has expired
    and notify the assigned authority to keep or delete the complaint.

    Returns the number of complaints processed.
    Run this periodically (e.g. every hour via background task).
    """
    from src.database.models import Complaint as _C, Authority as _Auth
    from src.services.notification_service import notification_service as _ns

    now = datetime.now(timezone.utc)
    # Fetch expired, un-notified, image-pending complaints that are still active
    q = (
        select(_C)
        .where(
            _C.image_pending == True,
            _C.image_authority_notified == False,
            _C.image_required_deadline <= now,
            _C.is_deleted == False,
        )
    )
    result = await db.execute(q)
    expired = result.scalars().all()

    processed = 0
    for complaint in expired:
        try:
            if complaint.assigned_authority_id:
                await _ns.create_notification(
                    db,
                    recipient_type="Authority",
                    recipient_id=str(complaint.assigned_authority_id),
                    complaint_id=complaint.id,
                    notification_type="image_decision_required",
                    message=(
                        f"A complaint (ID: {str(complaint.id)[:8]}…) required visual evidence "
                        f"but the student did not upload an image within 24 hours. "
                        f"Text: \"{(complaint.rephrased_text or complaint.original_text)[:100]}…\" "
                        f"Please decide: keep the complaint as-is, or delete it via the "
                        f"complaint detail page → 'Image Decision' action."
                    )
                )
            complaint.image_authority_notified = True
            processed += 1
        except Exception as _e:
            logger.warning(f"Failed to notify authority for expired image deadline on {complaint.id}: {_e}")

    if processed:
        await db.commit()
        logger.info(f"Image deadline checker: notified authority for {processed} expired complaints")

    return processed


class ComplaintService:
    """Service for complaint operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.complaint_repo = ComplaintRepository(db)
        self.student_repo = StudentRepository(db)
    
    async def create_complaint(
        self,
        student_roll_no: str,
        original_text: str,
        visibility: str = "Public",
        image_file: Optional[UploadFile] = None,  # ✅ Accept UploadFile
        is_anonymous: bool = False,               # v2: hide submitter identity from peers
    ) -> Dict[str, Any]:
        """
        Create a new complaint with FULL AI-DRIVEN processing (no category_id required).

        ✅ UPDATED: category_id is NO LONGER a parameter - determined by LLM
        ✅ UPDATED: target_department_id is determined by LLM analysis
        ✅ UPDATED: Implements spam rejection (doesn't create complaint if spam)
        ✅ UPDATED: Enforces image requirement via LLM

        Args:
            student_roll_no: Student roll number
            original_text: Original complaint text
            visibility: Visibility level (Public or Private)
            image_file: Optional uploaded image file

        Returns:
            Dictionary with complaint details, AI analysis results, and image verification

        Raises:
            ValueError: If spam detected or required image missing
        """
        # Get student with department
        student = await self.student_repo.get_with_department(student_roll_no)
        if not student:
            raise ValueError("Student not found")

        if not student.is_active:
            raise ValueError("Student account is inactive")

        # ✅ FIXED: Check spam blacklist
        blacklist_check = await spam_detection_service.check_spam_blacklist(
            self.db, student_roll_no
        )
        if blacklist_check["is_blacklisted"]:
            error_msg = f"Account suspended: {blacklist_check['reason']}."
            if blacklist_check.get('is_permanent'):
                error_msg += " This is a permanent ban."
            elif blacklist_check.get('expires_at'):
                error_msg += f" Ban expires on {blacklist_check['expires_at']}."

            logger.warning(f"Blacklisted user {student_roll_no} attempted to create complaint")
            raise ValueError(error_msg)

        # ✅ REMOVED: Category validation - now done by LLM
        # Category and department are determined via AI analysis below

        # ✅ FIX: Pre-check for cross-gender hostel complaints BEFORE LLM call.
        # The LLM re-categorizes based on student gender, so a Female student's
        # complaint about "men's hostel" would silently become a Women's Hostel
        # complaint. We must reject these explicitly.
        original_lower = original_text.lower()
        if student.stay_type == "Day Scholar":
            # Day scholars cannot report hostel complaints at all
            mens_kw = ["men's hostel", "mens hostel", "boys hostel", "male hostel",
                       "women's hostel", "womens hostel", "girls hostel", "female hostel"]
            if any(kw in original_lower for kw in mens_kw):
                # Hostel-related text for a day scholar - let LLM categorize; validation will reject
                pass  # handled by post-LLM validation
        elif student.gender == "Female":
            # Female hostel student should not report about men's hostel.
            # Strip out "women's hostel" mentions first to avoid false substring matches
            # ("women's hostel" contains "men's hostel" as a substring).
            check_text = original_lower.replace("women's hostel", "__womens__").replace("womens hostel", "__womens__")
            mens_hostel_kw = ["men's hostel", "mens hostel", "boys hostel", "male hostel", "men hostel"]
            if any(kw in check_text for kw in mens_hostel_kw):
                raise ValueError(
                    "Female students cannot submit complaints about men's hostel facilities"
                )
        elif student.gender == "Male":
            # Male hostel student should not report about women's hostel.
            # Strip out "men's hostel" mentions first to avoid false matches.
            check_text = original_lower.replace("men's hostel", "__mens__").replace("mens hostel", "__mens__")
            womens_hostel_kw = ["women's hostel", "womens hostel", "girls hostel", "female hostel", "ladies hostel"]
            if any(kw in check_text for kw in womens_hostel_kw):
                raise ValueError(
                    "Male students cannot submit complaints about women's hostel facilities"
                )

        # Build context for LLM
        context = {
            "department": student.department.code if (student.department and hasattr(student.department, 'code')) else "Unknown",
            "gender": student.gender or "",
            "stay_type": student.stay_type or "",
        }

        logger.info(f"Processing complaint for {student_roll_no}")

        is_spam_complaint = False
        spam_complaint_reason = None
        llm_failed = False
        image_required_flag = False       # LLM wants an image but none provided
        image_required_reason = None      # LLM explanation stored for notification

        # ── Pre-LLM deterministic spam checks ────────────────────────────────
        if _is_unethical_academic_request(original_text):
            is_spam_complaint = True
            spam_complaint_reason = (
                "Request for grade/mark manipulation is not a valid complaint. "
                "If your marks were incorrectly totalled or you believe there was "
                "an evaluation error, please request a re-evaluation through your department."
            )
            logger.warning(
                f"Pre-LLM spam rejection: unethical academic request from {student_roll_no} "
                f"| text: {original_text[:80]}"
            )

        # Normalize shortforms using comprehensive SREC aliases
        from src.constants.aliases import normalize_complaint_text as _normalize_aliases
        normalized_text = _normalize_aliases(original_text)
        if normalized_text != original_text.lower():
            logger.info(
                f"Alias normalization applied | "
                f"original: {original_text[:60]!r} → normalized: {normalized_text[:60]!r}"
            )

        try:
            if not is_spam_complaint:
                # ── SINGLE COMBINED LLM CALL ──────────────────────────────────
                # Replaces 4 separate calls: spam + categorize + rephrase + image_req
                categorization = await llm_service.process_complaint(normalized_text, context)

                # Extract spam result from combined response
                if categorization.get("is_spam"):
                    is_spam_complaint = True
                    spam_complaint_reason = categorization.get("spam_reason", "Content flagged as spam")
                    logger.warning(f"Spam detected by combined LLM for {student_roll_no}: {spam_complaint_reason}")

            if not is_spam_complaint:
                # Apply deterministic overrides (catches LLM mistakes)
                ai_category = categorization.get("category")
                final_category = _override_category(
                    original_text, ai_category, student.gender or ""
                )
                if final_category != ai_category:
                    categorization["category"] = final_category
                ai_category = categorization.get("category")

                # Validate hostel category against student profile
                if ai_category in ("Men's Hostel", "Women's Hostel"):
                    if student.stay_type == "Day Scholar":
                        raise ValueError("Day scholars cannot submit hostel complaints")
                    if ai_category == "Men's Hostel" and student.gender != "Male":
                        raise ValueError(
                            "HOSTEL_GENDER_MISMATCH: You cannot submit a complaint for the opposite hostel"
                        )
                    if ai_category == "Women's Hostel" and student.gender != "Female":
                        raise ValueError(
                            "HOSTEL_GENDER_MISMATCH: You cannot submit a complaint for the opposite hostel"
                        )

                # Extract rephrased text from combined response
                rephrased_text = categorization.get("rephrased", original_text)
                if not rephrased_text or len(rephrased_text) < 10:
                    rephrased_text = original_text

                # Check image requirement from combined response.
                # Instead of blocking submission, grant a 24-hour grace period.
                # The complaint is posted with an "image_pending" tag so the student
                # can upload evidence later. After 24 h the assigned authority decides.
                if categorization.get("image_required") and not image_file:
                    reason = categorization.get("image_reasoning", "Visual evidence required")
                    image_required_flag = True
                    image_required_reason = reason
                    logger.info(
                        f"Image required but not provided for {student_roll_no} — "
                        f"granting 24-hour grace period. Reason: {reason}"
                    )
            else:
                # Spam detected — skip LLM, use safe defaults
                logger.info(f"Skipping LLM pipeline for spam complaint from {student_roll_no}")
                categorization = {
                    "category": "General",
                    "target_department": context.get("department", "CSE"),
                    "priority": "Low",
                    "confidence": 1.0,
                    "is_against_authority": False,
                }
                rephrased_text = original_text

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"LLM processing error: {e}")
            categorization = {
                "category": "General",
                "target_department": context.get("department", "CSE"),
                "priority": "Medium",
                "confidence": 0.5,
                "is_against_authority": False
            }
            rephrased_text = original_text
            llm_failed = True

        # When LLM failed, apply keyword-based overrides
        if llm_failed:
            _corrected_cat = _override_category(original_text, categorization.get("category", "General"), student.gender or "")
            if _corrected_cat != categorization.get("category"):
                logger.info(f"LLM-fallback override: General -> {_corrected_cat} for '{original_text[:60]}'")
                categorization["category"] = _corrected_cat

        # ✅ UPDATED: Map category name to ID
        category_id = None
        if "category" in categorization:
            category_query = select(ComplaintCategory.id).where(
                ComplaintCategory.name == categorization['category']
            )
            category_result = await self.db.execute(category_query)
            category_row = category_result.first()
            if category_row:
                category_id = category_row[0]
            else:
                # Fallback to General category
                logger.warning(f"Category '{categorization['category']}' not found, using General")
                general_query = select(ComplaintCategory.id).where(
                    ComplaintCategory.name == "General"
                )
                general_result = await self.db.execute(general_query)
                general_row = general_result.first()
                category_id = general_row[0] if general_row else 3  # Fallback to ID 3

        # ✅ NEW: Map department code to department ID
        from src.database.models import Department
        target_department_code = categorization.get("target_department", context.get("department", "CSE"))
        dept_query = select(Department.id).where(
            Department.code == target_department_code
        )
        dept_result = await self.db.execute(dept_query)
        dept_row = dept_result.first()
        target_department_id = dept_row[0] if dept_row else student.department_id  # Fallback to student's department

        # Flag cross-department complaints (student filing against a different dept)
        is_cross_department = (
            target_department_id is not None
            and student.department_id is not None
            and target_department_id != student.department_id
        )
        if is_cross_department:
            logger.info(
                f"Cross-department complaint: student dept={student.department_id} → target dept={target_department_id}"
            )

        # Calculate initial priority via hybrid multi-signal system
        from src.services.priority_service import calculate_initial_priority
        _priority_result = await calculate_initial_priority(
            text=original_text,
            category_name=categorization.get("category", "General"),
            groq_client=llm_service.groq_client,
        )
        priority = _priority_result["priority"]
        logger.info(
            f"Priority signals for {student_roll_no}: {_priority_result['signals']} "
            f"| llm_adj={_priority_result['llm_adjustment']} ({_priority_result['llm_reason']}) "
            f"| final={priority} (score={_priority_result['score']})"
        )
        # Use raw numeric score from priority_service (0-100 scale)
        # This serves as the base for vote-based blended recalculation
        priority_score = float(_priority_result["score"])

        # Status: Spam if flagged, otherwise Raised
        initial_status = "Spam" if is_spam_complaint else "Raised"

        # ✅ FIXED: Use timezone-aware datetime
        current_time = datetime.now(timezone.utc)
        
        # ✅ NEW: Process image if provided
        image_bytes = None
        image_mimetype = None
        image_size = None
        image_filename = None
        image_verified = False
        image_verification_status = "Pending"
        image_verification_message = None
        
        if image_file:
            try:
                # Read image bytes
                image_bytes, image_mimetype, image_size, image_filename = await file_upload_handler.read_image_bytes(
                    image_file, validate=True
                )
                
                # Optimize image
                image_bytes, image_size = await file_upload_handler.optimize_image_bytes(
                    image_bytes, image_mimetype
                )
                
                logger.info(f"Image uploaded: {image_filename} ({image_size} bytes)")
                
            except Exception as e:
                logger.error(f"Image upload error: {e}")
                # Continue without image
                image_bytes = None
        
        # DC1: Disciplinary Committee complaints are ALWAYS Private.
        # They must never appear in the public feed.
        final_category_name = categorization.get("category", "General")
        if final_category_name == "Disciplinary Committee":
            visibility = "Private"
            logger.info(
                f"Forcing visibility=Private for Disciplinary Committee complaint from {student_roll_no}"
            )

        # ✅ UPDATED: Create complaint with AI-determined category and target department
        # Spam complaints are saved with is_marked_as_spam=True, status="Spam"
        complaint = await self.complaint_repo.create(
            student_roll_no=student_roll_no,
            category_id=category_id,
            original_text=original_text,
            rephrased_text=rephrased_text,
            visibility=visibility,
            priority=priority,
            priority_score=priority_score,
            status=initial_status,
            is_marked_as_spam=is_spam_complaint,
            spam_reason=spam_complaint_reason if is_spam_complaint else None,
            complaint_department_id=target_department_id,
            complainant_department_id=student.department_id,  # Rule D2: track submitter's dept
            is_cross_department=is_cross_department,
            is_anonymous=is_anonymous,
            # ✅ NEW: Binary image fields
            image_data=image_bytes,
            image_mimetype=image_mimetype,
            image_size=image_size,
            image_filename=image_filename,
            image_verified=False,
            image_verification_status="Pending" if image_bytes else None
        )
        
        # ── Calculate reach: how many students can see this complaint ─────────────
        try:
            from sqlalchemy import func as sqlfunc
            category_name = categorization.get("category", "General")
            reach_conditions = [Student.is_active == True]

            if category_name == "Men's Hostel":
                reach_conditions += [Student.stay_type == "Hostel", Student.gender == "Male"]
            elif category_name == "Women's Hostel":
                reach_conditions += [Student.stay_type == "Hostel", Student.gender == "Female"]
            elif category_name == "Department":
                # Department complaints visible to students in target_department_id
                if target_department_id:
                    reach_conditions.append(Student.department_id == target_department_id)
            # General / Disciplinary → all active students (no extra filter)

            reach_query = select(sqlfunc.count()).select_from(Student).where(*reach_conditions)
            reach_result = await self.db.execute(reach_query)
            complaint.reach = reach_result.scalar() or 0
            await self.db.commit()
        except Exception as _reach_err:
            logger.warning(f"Could not calculate reach for {complaint.id}: {_reach_err}")

        # ── Image grace period: flag complaint if LLM wants image but none uploaded ─
        if image_required_flag:
            complaint.image_required = True
            complaint.image_pending = True
            complaint.image_required_deadline = current_time + timedelta(hours=24)
            await self.db.commit()
            logger.info(
                f"Complaint {complaint.id} flagged as image_pending — "
                f"deadline: {complaint.image_required_deadline.isoformat()}"
            )

        # ✅ NEW: Verify image if provided
        if image_bytes:
            try:
                verification_result = await image_verification_service.verify_image_from_bytes(
                    db=self.db,
                    complaint_id=complaint.id,
                    complaint_text=rephrased_text,
                    image_bytes=image_bytes,
                    mimetype=image_mimetype
                )
                
                # Update complaint with verification results
                complaint.image_verified = verification_result["is_relevant"]
                complaint.image_verification_status = verification_result["status"]

                # BUG-006 fix: mark complaint as spam if image is clearly irrelevant
                # BUG-029 fix: liberal threshold — only reject truly unrelated images
                # With liberal prompt, relevant images score 0.5+; only reject < 0.3
                img_is_relevant = verification_result.get("is_relevant", True)
                img_confidence = verification_result.get("confidence_score", 1.0)
                if not img_is_relevant and img_confidence < 0.3:
                    complaint.is_marked_as_spam = True
                    complaint.status = "Spam"
                    complaint.spam_reason = (
                        f"Image failed verification: "
                        f"relevant={img_is_relevant}, confidence={img_confidence:.2f}"
                    )
                    is_spam_complaint = True
                    spam_complaint_reason = complaint.spam_reason
                    logger.warning(
                        f"Complaint {complaint.id} marked as spam due to image verification failure "
                        f"(relevant={img_is_relevant}, confidence={img_confidence:.2f})"
                    )

                await self.db.commit()

                image_verified = verification_result["is_relevant"]
                image_verification_status = verification_result["status"]
                image_verification_message = verification_result["explanation"]

                logger.info(
                    f"Image verification for {complaint.id}: "
                    f"Verified={image_verified}, Status={image_verification_status}"
                )
                
            except Exception as e:
                logger.error(f"Image verification error: {e}")
                image_verification_message = f"Verification error: {str(e)}"
        
        # Notify student about image grace period (if applicable)
        if image_required_flag:
            try:
                deadline_str = (current_time + timedelta(hours=24)).strftime("%d %b %Y, %I:%M %p UTC")
                await notification_service.create_notification(
                    self.db,
                    recipient_type="Student",
                    recipient_id=student_roll_no,
                    complaint_id=complaint.id,
                    notification_type="image_required",
                    message=(
                        f"Your complaint was submitted successfully. However, it appears to require "
                        f"supporting visual evidence ({image_required_reason}). "
                        f"Please upload a photo before {deadline_str}. "
                        f"If no image is uploaded by then, the assigned authority will decide whether "
                        f"to keep or remove your complaint."
                    )
                )
            except Exception as _img_notif_err:
                logger.warning(f"Failed to send image-required notification: {_img_notif_err}")

        # ✅ Route to appropriate authority (skip routing for spam complaints)
        authority = None
        if is_spam_complaint:
            # Notify student that their complaint was saved but marked as spam
            try:
                await notification_service.create_notification(
                    self.db,
                    recipient_type="Student",
                    recipient_id=student_roll_no,
                    complaint_id=complaint.id,
                    notification_type="complaint_spam",
                    message=(
                        f"Your complaint was received but flagged as potential spam. "
                        f"Reason: {spam_complaint_reason}. "
                        f"You can dispute this by contacting admin if this is a genuine complaint."
                    )
                )
            except Exception as _notif_err:
                logger.warning(f"Failed to send spam notification: {_notif_err}")

            # Also notify admin about the spam submission
            try:
                from src.repositories.authority_repo import AuthorityRepository
                authority_repo = AuthorityRepository(self.db)
                admins = await authority_repo.get_by_type("Admin")
                for admin in admins:
                    await notification_service.create_notification(
                        self.db,
                        recipient_type="Authority",
                        recipient_id=str(admin.id),
                        complaint_id=complaint.id,
                        notification_type="complaint_spam",
                        message=(
                            f"Spam complaint auto-detected from {student_roll_no}: "
                            f"{spam_complaint_reason}. Text: {original_text[:80]}..."
                        )
                    )
            except Exception as _admin_notif_err:
                logger.warning(f"Failed to notify admin of spam: {_admin_notif_err}")

        else:
            try:
                # BUG-017: Override department routing for common-subject complaints (Maths, Physics, Chemistry, English)
                _subject_dept_map = {
                    "mathematics": "MATH",
                    "maths": "MATH",
                    "math class": "MATH",
                    "physics": "PHY",
                    "chemistry": "CHEM",
                    "english": "ENG",
                }
                _category_name_for_routing = categorization.get("category", "")
                if _category_name_for_routing == "Department":
                    _text_lower_17 = original_text.lower()
                    for subject_kw, dept_code in _subject_dept_map.items():
                        if subject_kw in _text_lower_17:
                            # Re-resolve department ID from subject code
                            from src.database.models import Department as _Dept
                            _subj_dept_q = select(_Dept.id).where(_Dept.code == dept_code)
                            _subj_dept_result = await self.db.execute(_subj_dept_q)
                            _subj_dept_row = _subj_dept_result.first()
                            if _subj_dept_row and _subj_dept_row[0] != target_department_id:
                                logger.info(
                                    f"BUG-017 subject override: routing to {dept_code} HOD "
                                    f"instead of dept {target_department_id} (keyword: '{subject_kw}')"
                                )
                                target_department_id = _subj_dept_row[0]
                            break

                # Authority bypass routing for hostel complaints:
                # If a student complains ABOUT a specific hostel authority, that authority
                # is skipped and the complaint goes directly to the next authority up the chain.
                #
                # Chain (Men's or Women's Hostel):
                #   Warden (lvl 5) → Deputy Warden (lvl 10) → Senior Deputy Warden (lvl 15) → Admin (lvl 100)
                #
                # "complaint about warden"        → assign to Deputy Warden (min level: 10)
                # "complaint about deputy warden" → assign to Senior Deputy Warden (min level: 15)
                # "complaint about SDW"           → assign to Admin (min level: 100)
                _text_lower = original_text.lower()
                _hostel_bypass_min_level = None  # if set, skip to this authority level or above

                _hostel_chain = [
                    ("senior deputy warden", 100),  # complained about SDW → Admin
                    ("sdw",                  100),  # SDW abbreviation → Admin
                    ("deputy warden",         15),  # complained about Deputy → SDW
                    ("warden",                10),  # complained about Warden → Deputy Warden
                ]
                _category_name_for_routing = categorization.get("category", "")
                if _category_name_for_routing in ("Men's Hostel", "Women's Hostel"):
                    for kw, min_level in _hostel_chain:
                        if kw in _text_lower:
                            _hostel_bypass_min_level = min_level
                            logger.info(
                                f"Hostel authority bypass: '{kw}' in complaint → "
                                f"assigning to authority with level >= {min_level}"
                            )
                            break

                if _hostel_bypass_min_level is not None:
                    # Direct DB query: find lowest-level active authority at or above the bypass level
                    from src.repositories.authority_repo import AuthorityRepository as _AR
                    from src.database.models import Authority as _Auth
                    _ar = _AR(self.db)
                    _bypass_result = await self.db.execute(
                        select(_Auth)
                        .where(
                            _Auth.is_active == True,
                            _Auth.authority_level >= _hostel_bypass_min_level,
                        )
                        .order_by(_Auth.authority_level.asc())
                        .limit(1)
                    )
                    authority = _bypass_result.scalar_one_or_none()
                    if authority:
                        logger.info(
                            f"Bypass assignment: {authority.name} (level={authority.authority_level})"
                        )
                    else:
                        logger.warning(
                            f"No authority found at level >= {_hostel_bypass_min_level}, falling back to normal routing"
                        )
                        authority = await authority_service.route_complaint(
                            self.db, category_id, target_department_id,
                            is_against_authority=False,
                        )
                else:
                    authority = await authority_service.route_complaint(
                        self.db,
                        category_id,
                        target_department_id,
                        categorization.get("is_against_authority", False),
                    )

                if authority:
                    complaint.assigned_authority_id = authority.id
                    complaint.assigned_at = current_time
                    await self.db.commit()

                    # Notify the assigned authority
                    _category_name = categorization.get("category", "Unknown")
                    await notification_service.create_notification(
                        self.db,
                        recipient_type="Authority",
                        recipient_id=str(authority.id),
                        complaint_id=complaint.id,
                        notification_type="complaint_assigned",
                        message=(
                            f"New complaint assigned to you: {_category_name} complaint. "
                            f"Issue: {rephrased_text[:100]}"
                        )
                    )

                    logger.info(f"Complaint {complaint.id} assigned to {authority.name}")
                else:
                    logger.warning(f"No authority found for complaint {complaint.id}")

                # Notify admin for High/Critical priority complaints
                if priority in ("High", "Critical"):
                    try:
                        from src.repositories.authority_repo import AuthorityRepository
                        authority_repo = AuthorityRepository(self.db)
                        admins = await authority_repo.get_by_type("Admin")
                        for admin in admins:
                            await notification_service.create_notification(
                                self.db,
                                recipient_type="Authority",
                                recipient_id=str(admin.id),
                                complaint_id=complaint.id,
                                notification_type="high_priority_complaint",
                                message=(
                                    f"⚠️ {priority} priority complaint raised by {student_roll_no}: "
                                    f"\"{rephrased_text[:100]}...\""
                                )
                            )
                    except Exception as _notif_err:
                        logger.warning(f"Failed to notify admin of high-priority complaint: {_notif_err}")

            except Exception as e:
                logger.error(f"Authority routing error: {e}")
                # Continue without authority assignment

        logger.info(
            f"Complaint {complaint.id} created successfully - "
            f"Status: {initial_status}, Priority: {priority}, "
            f"Category: {categorization.get('category')}, "
            f"Target Dept: {target_department_code}, "
            f"Has Image: {image_bytes is not None}, "
            f"Image Required: {categorization.get('image_required', False)}, "
            f"LLM Failed: {llm_failed}"
        )

        return {
            "id": str(complaint.id),
            "status": "Submitted" if not is_spam_complaint else "Spam",
            "rephrased_text": rephrased_text,
            "original_text": original_text,
            "priority": priority,
            "priority_score": priority_score,
            "assigned_authority": authority.name if authority else None,
            "assigned_authority_id": authority.id if authority else None,
            "created_at": current_time.isoformat(),
            "is_spam": is_spam_complaint,
            "spam_reason": spam_complaint_reason if is_spam_complaint else None,
            "message": (
                "Your complaint was received but flagged as potential spam. You may dispute this if it is genuine."
                if is_spam_complaint
                else (
                    "Complaint submitted. Please upload supporting image evidence within 24 hours."
                    if image_required_flag
                    else "Complaint submitted successfully"
                )
            ),
            # ✅ NEW: AI-driven categorization information
            "category": categorization.get("category"),
            "target_department_id": target_department_id,
            "target_department_code": target_department_code,
            "cross_department": target_department_id != student.department_id,
            "llm_failed": llm_failed,
            "confidence_score": categorization.get("confidence", 0.8),
            # ✅ Image information
            "has_image": image_bytes is not None,
            "image_verified": image_verified,
            "image_verification_status": image_verification_status,
            "image_verification_message": image_verification_message,
            "image_filename": image_filename,
            "image_size": image_size,
            # ✅ Image requirement information
            "image_was_required": categorization.get("image_required", False),
            "image_requirement_reasoning": categorization.get("image_reasoning"),
            # Grace period fields
            "image_pending": image_required_flag,
            "image_required_deadline": (
                (current_time + timedelta(hours=24)).isoformat() if image_required_flag else None
            ),
        }
    
    async def upload_complaint_image(
        self,
        complaint_id: UUID,
        student_roll_no: str,
        image_file: UploadFile
    ) -> Dict[str, Any]:
        """
        ✅ NEW: Upload/update image for existing complaint.
        
        Args:
            complaint_id: Complaint UUID
            student_roll_no: Student roll number (for permission check)
            image_file: Uploaded image file
        
        Returns:
            Image upload and verification results
        """
        # Get complaint and verify ownership
        complaint = await self.complaint_repo.get(complaint_id)
        if not complaint:
            raise ValueError("Complaint not found")
        
        if complaint.student_roll_no != student_roll_no:
            raise PermissionError("Not authorized to upload image for this complaint")
        
        try:
            # Read and optimize image
            image_bytes, image_mimetype, image_size, image_filename = await file_upload_handler.read_image_bytes(
                image_file, validate=True
            )
            
            image_bytes, image_size = await file_upload_handler.optimize_image_bytes(
                image_bytes, image_mimetype
            )
            
            # Update complaint with image (has_image is a computed property based on image_data)
            complaint.image_data = image_bytes
            complaint.image_mimetype = image_mimetype
            complaint.image_size = image_size
            complaint.image_filename = image_filename
            complaint.image_verified = False
            complaint.image_verification_status = "Pending"
            # Clear grace period flag — student fulfilled the image requirement
            if complaint.image_pending:
                complaint.image_pending = False
                complaint.image_required_deadline = None
                logger.info(f"Image grace period fulfilled for complaint {complaint_id}")
            await self.db.commit()
            
            # Verify image
            verification_result = await image_verification_service.verify_image_from_bytes(
                db=self.db,
                complaint_id=complaint.id,
                complaint_text=complaint.rephrased_text or complaint.original_text,
                image_bytes=image_bytes,
                mimetype=image_mimetype
            )
            
            # Update verification results
            complaint.image_verified = verification_result["is_relevant"]
            complaint.image_verification_status = verification_result["status"]
            await self.db.commit()
            
            logger.info(
                f"Image uploaded for complaint {complaint_id}: "
                f"Verified={verification_result['is_relevant']}, "
                f"Status={verification_result['status']}"
            )
            
            return {
                "complaint_id": str(complaint_id),
                "has_image": True,
                "image_verified": verification_result["is_relevant"],
                "verification_status": verification_result["status"],
                "verification_message": verification_result["explanation"],
                "image_filename": image_filename,
                "image_size": image_size,
                "confidence_score": verification_result.get("confidence_score", 0.0)
            }
            
        except (InvalidFileTypeError, FileTooLargeError, FileUploadError):
            raise  # Re-raise specific file errors so route can return 400
        except Exception as e:
            logger.error(f"Image upload error for {complaint_id}: {e}")
            raise ValueError(f"Failed to upload image: {str(e)}")
    
    async def get_complaint_image(
        self,
        complaint_id: UUID,
        requester_roll_no: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ✅ NEW: Get complaint image data.
        
        Args:
            complaint_id: Complaint UUID
            requester_roll_no: Optional student requesting image (for permission check)
        
        Returns:
            Dictionary with image_bytes, mimetype, and metadata
        """
        complaint = await self.complaint_repo.get(complaint_id)
        if not complaint:
            raise ValueError("Complaint not found")
        
        # Check permission for private complaints
        if complaint.visibility == "Private":
            if not requester_roll_no or complaint.student_roll_no != requester_roll_no:
                raise PermissionError("Not authorized to view this complaint's image")
        
        if not complaint.has_image or not complaint.image_data:
            raise ValueError("Complaint has no image")
        
        return {
            "complaint_id": str(complaint_id),
            "image_bytes": complaint.image_data,
            "mimetype": complaint.image_mimetype,
            "filename": complaint.image_filename,
            "size": complaint.image_size,
            "verified": complaint.image_verified,
            "verification_status": complaint.image_verification_status
        }
    
    async def update_complaint_status(
        self,
        complaint_id: UUID,
        new_status: str,
        authority_id: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update complaint status (by authority).
        
        Args:
            complaint_id: Complaint UUID
            new_status: New status (Raised, In Progress, Resolved, Rejected, Escalated)
            authority_id: Authority making the change
            reason: Optional reason for change
        
        Returns:
            Updated complaint info
        """
        complaint = await self.complaint_repo.get(complaint_id)
        if not complaint:
            raise ValueError("Complaint not found")
        
        # Check if authority has permission (Admin can update any complaint)
        from src.repositories.authority_repo import AuthorityRepository
        authority_repo = AuthorityRepository(self.db)
        authority = await authority_repo.get(authority_id)
        is_admin = authority and authority.authority_type == "Admin"

        if not is_admin and complaint.assigned_authority_id != authority_id:
            raise PermissionError("Not authorized to update this complaint")
        
        old_status = complaint.status
        
        # Don't allow updating already resolved complaints (except Close or Reopen)
        if old_status == "Resolved" and new_status not in ("Reopened", "Closed"):
            raise ValueError("Cannot modify resolved complaint")
        
        # Update status
        complaint.status = new_status

        # Clear spam flags when admin un-spams a complaint
        if old_status == "Spam" and new_status in ("Raised", "In Progress"):
            complaint.is_marked_as_spam = False
            complaint.spam_reason = None
            complaint.has_disputed = False

        # ✅ FIXED: Use timezone-aware datetime
        current_time = datetime.now(timezone.utc)

        # Update resolved_at if status is Resolved
        if new_status == "Resolved":
            complaint.resolved_at = current_time
        elif new_status == "Reopened":
            complaint.resolved_at = None
        
        await self.db.commit()
        
        # Create status update record
        status_update = StatusUpdate(
            complaint_id=complaint_id,
            old_status=old_status,
            new_status=new_status,
            updated_by=authority_id,
            reason=reason,
            updated_at=current_time
        )
        self.db.add(status_update)
        await self.db.commit()
        
        # Notify student (str() prevents enum repr like ComplaintStatus.CLOSED)
        _status_str = str(new_status).split(".")[-1] if "." in str(new_status) else str(new_status)
        await notification_service.create_notification(
            self.db,
            recipient_type="Student",
            recipient_id=complaint.student_roll_no,
            complaint_id=complaint_id,
            notification_type="status_update",
            message=f"Your complaint status changed to '{_status_str}'" +
                    (f": {reason}" if reason else "")
        )

        # Bug 6 fix: If the status update was made by an admin (not the assigned authority),
        # also notify the assigned authority so they are aware of the change.
        if complaint.assigned_authority_id and complaint.assigned_authority_id != authority_id:
            try:
                await notification_service.create_notification(
                    self.db,
                    recipient_type="Authority",
                    recipient_id=str(complaint.assigned_authority_id),
                    complaint_id=complaint_id,
                    notification_type="status_updated",
                    message=f"Complaint status updated to '{_status_str}' by admin" +
                            (f": {reason}" if reason else "")
                )
            except Exception as _notif_err:
                logger.warning(f"Failed to send authority status notification: {_notif_err}")

        logger.info(
            f"Complaint {complaint_id} status updated by authority {authority_id}: "
            f"{old_status} → {new_status}"
        )
        
        return {
            "complaint_id": str(complaint_id),
            "old_status": old_status,
            "new_status": new_status,
            "updated_at": current_time.isoformat(),
            "reason": reason,
            "resolved_at": complaint.resolved_at.isoformat() if complaint.resolved_at else None
        }
    
    async def get_public_feed(
        self,
        student_roll_no: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get public feed filtered by visibility rules.

        Args:
            student_roll_no: Student requesting feed
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of complaint dictionaries
        """
        student = await self.student_repo.get_with_department(student_roll_no)
        if not student:
            raise ValueError("Student not found")

        complaints = await self.complaint_repo.get_public_feed(
            student_stay_type=student.stay_type,
            student_department_id=student.department_id,
            student_gender=student.gender,
            skip=skip,
            limit=limit
        )
        
        # Format complaints for response
        result = []
        for complaint in complaints:
            result.append({
                "id": str(complaint.id),
                "rephrased_text": complaint.rephrased_text,
                "category": complaint.category.name if complaint.category else "Unknown",
                "priority": complaint.priority,
                "status": complaint.status,
                "upvotes": complaint.upvotes,
                "downvotes": complaint.downvotes,
                "created_at": complaint.submitted_at.isoformat(),
                "visibility": complaint.visibility,
                "is_own_complaint": complaint.student_roll_no == student_roll_no,
                # ✅ NEW: Image fields
                "has_image": complaint.has_image,
                "image_verified": complaint.image_verified,
                "image_verification_status": complaint.image_verification_status
            })
        
        return result
    
    async def get_complaint_details(
        self,
        complaint_id: UUID,
        requester_roll_no: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed complaint information.
        
        Args:
            complaint_id: Complaint UUID
            requester_roll_no: Optional student requesting details
        
        Returns:
            Detailed complaint info
        """
        complaint = await self.complaint_repo.get_with_relations(complaint_id)
        if not complaint:
            raise ValueError("Complaint not found")
        
        # Check if requester has permission to view
        if complaint.visibility == "Private":
            if not requester_roll_no or complaint.student_roll_no != requester_roll_no:
                raise PermissionError("Not authorized to view this complaint")
        
        return {
            "id": str(complaint.id),
            "original_text": complaint.original_text,
            "rephrased_text": complaint.rephrased_text,
            "category": complaint.category.name if complaint.category else "Unknown",
            "priority": complaint.priority,
            "priority_score": complaint.priority_score,
            "status": complaint.status,
            "visibility": complaint.visibility,
            "upvotes": complaint.upvotes,
            "downvotes": complaint.downvotes,
            "created_at": complaint.submitted_at.isoformat(),
            "updated_at": complaint.updated_at.isoformat() if complaint.updated_at else None,
            "resolved_at": complaint.resolved_at.isoformat() if complaint.resolved_at else None,
            "assigned_authority": complaint.assigned_authority.name if complaint.assigned_authority else None,
            "student_roll_no": complaint.student_roll_no if complaint.visibility != "Anonymous" else "Anonymous",
            "is_spam": complaint.is_marked_as_spam,
            # ✅ NEW: Image fields (no image_url)
            "has_image": complaint.has_image,
            "image_verified": complaint.image_verified,
            "image_verification_status": complaint.image_verification_status,
            "image_filename": complaint.image_filename,
            "image_size": complaint.image_size
        }
    
    async def get_student_complaints(
        self,
        student_roll_no: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get all complaints by a student with status tracking.
        
        Args:
            student_roll_no: Student roll number
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of student's complaints with status info
        """
        complaints = await self.complaint_repo.get_by_student(
            student_roll_no, skip=skip, limit=limit
        )
        
        result = []
        for complaint in complaints:
            result.append({
                "id": str(complaint.id),
                "title": complaint.rephrased_text[:100] + "..." if len(complaint.rephrased_text) > 100 else complaint.rephrased_text,
                "category": complaint.category.name if complaint.category else "Unknown",
                "status": complaint.status,
                "priority": complaint.priority,
                "created_at": complaint.submitted_at.isoformat(),
                "updated_at": complaint.updated_at.isoformat() if complaint.updated_at else None,
                "resolved_at": complaint.resolved_at.isoformat() if complaint.resolved_at else None,
                "assigned_authority": complaint.assigned_authority.name if complaint.assigned_authority else "Unassigned",
                "upvotes": complaint.upvotes,
                "downvotes": complaint.downvotes,
                "visibility": complaint.visibility,
                # ✅ NEW: Image fields
                "has_image": complaint.has_image,
                "image_verified": complaint.image_verified
            })
        
        return result
    
    async def get_complaint_status_history(
        self,
        complaint_id: UUID,
        student_roll_no: str
    ) -> List[Dict[str, Any]]:
        """
        Get status update history for a complaint.
        
        Args:
            complaint_id: Complaint UUID
            student_roll_no: Student requesting history (for permission check)
        
        Returns:
            List of status updates
        """
        # Verify ownership
        complaint = await self.complaint_repo.get(complaint_id)
        if not complaint:
            raise ValueError("Complaint not found")
        
        if complaint.student_roll_no != student_roll_no:
            raise PermissionError("Not authorized to view this complaint history")
        
        # Get status history
        query = select(StatusUpdate).where(
            StatusUpdate.complaint_id == complaint_id
        ).order_by(StatusUpdate.updated_at.asc())
        
        result = await self.db.execute(query)
        status_updates = result.scalars().all()
        
        history = []
        for update in status_updates:
            history.append({
                "old_status": update.old_status,
                "new_status": update.new_status,
                "updated_at": update.updated_at.isoformat() if update.updated_at else datetime.now(timezone.utc).isoformat(),
                "reason": update.reason,
                "updated_by_authority_id": update.updated_by
            })
        
        return history
    
    async def get_complaint_statistics(
        self,
        student_roll_no: str
    ) -> Dict[str, Any]:
        """
        Get complaint statistics for a student.

        Args:
            student_roll_no: Student roll number

        Returns:
            Statistics dictionary
        """
        complaints = await self.complaint_repo.get_by_student(student_roll_no)

        total = len(complaints)
        resolved = sum(1 for c in complaints if c.status == "Resolved")
        in_progress = sum(1 for c in complaints if c.status == "In Progress")
        raised = sum(1 for c in complaints if c.status == "Raised")
        spam = sum(1 for c in complaints if c.is_marked_as_spam)
        with_images = sum(1 for c in complaints if c.has_image)  # ✅ NEW
        verified_images = sum(1 for c in complaints if c.image_verified)  # ✅ NEW

        return {
            "total_complaints": total,
            "resolved": resolved,
            "in_progress": in_progress,
            "raised": raised,
            "spam_flagged": spam,
            "resolution_rate": (resolved / total * 100) if total > 0 else 0,
            # ✅ NEW: Image statistics
            "with_images": with_images,
            "verified_images": verified_images
        }

    # ==================== PARTIAL ANONYMITY ====================

    async def get_complaint_for_authority(
        self,
        complaint_id: UUID,
        authority_id: int,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        ✅ NEW: Get complaint with partial anonymity enforcement.

        Rules:
        - Admin: Can view all student information for all complaints
        - Authority: Can view student info ONLY if complaint is marked as spam
        - Non-spam complaints: Hide student personal details from authorities

        Args:
            complaint_id: Complaint UUID
            authority_id: Authority requesting details
            is_admin: Whether requester is admin

        Returns:
            Complaint with conditionally redacted student info
        """
        complaint = await self.complaint_repo.get_with_relations(complaint_id)
        if not complaint:
            raise ValueError("Complaint not found")

        # Check if authority has permission to view
        if not is_admin and complaint.assigned_authority_id != authority_id:
            raise PermissionError("Not authorized to view this complaint")

        # Build base response
        response = {
            "id": str(complaint.id),
            "original_text": complaint.original_text,
            "rephrased_text": complaint.rephrased_text,
            "category": complaint.category.name if complaint.category else "Unknown",
            "priority": complaint.priority,
            "priority_score": complaint.priority_score,
            "status": complaint.status,
            "visibility": complaint.visibility,
            "upvotes": complaint.upvotes,
            "downvotes": complaint.downvotes,
            "created_at": complaint.submitted_at.isoformat(),
            "updated_at": complaint.updated_at.isoformat() if complaint.updated_at else None,
            "resolved_at": complaint.resolved_at.isoformat() if complaint.resolved_at else None,
            "assigned_authority": complaint.assigned_authority.name if complaint.assigned_authority else None,
            "is_spam": complaint.is_marked_as_spam,
            "spam_reason": complaint.spam_reason,
            "is_marked_as_spam": complaint.is_marked_as_spam,
            "has_disputed": complaint.has_disputed,
            "appeal_reason": complaint.appeal_reason,
            # Image fields
            "has_image": complaint.has_image,
            "image_verified": complaint.image_verified,
            "image_verification_status": complaint.image_verification_status,
            "image_filename": complaint.image_filename,
            "image_size": complaint.image_size
        }

        # ✅ CRITICAL: Partial Anonymity Logic
        if is_admin:
            # Admin can see ALL student information
            response["student_roll_no"] = complaint.student_roll_no
            response["student_name"] = complaint.student.name if complaint.student else None
            response["student_email"] = complaint.student.email if complaint.student else None
            response["student_gender"] = complaint.student.gender if complaint.student else None
            response["student_stay_type"] = complaint.student.stay_type if complaint.student else None
            response["student_year"] = complaint.student.year if complaint.student else None
            response["student_department"] = complaint.student.department.name if complaint.student and complaint.student.department else None
            logger.info(f"Admin {authority_id} viewing complaint {complaint_id} - Full student info provided")

        elif complaint.is_marked_as_spam:
            # Authority can see student info for SPAM complaints
            response["student_roll_no"] = complaint.student_roll_no
            response["student_name"] = complaint.student.name if complaint.student else None
            response["student_email"] = complaint.student.email if complaint.student else None
            response["student_gender"] = complaint.student.gender if complaint.student else None
            response["student_stay_type"] = complaint.student.stay_type if complaint.student else None
            response["student_year"] = complaint.student.year if complaint.student else None
            response["student_department"] = complaint.student.department.name if complaint.student and complaint.student.department else None
            logger.info(
                f"Authority {authority_id} viewing SPAM complaint {complaint_id} - "
                f"Student info revealed: {complaint.student_roll_no}"
            )

        else:
            # Non-spam complaints: Hide student details from authorities
            response["student_roll_no"] = "Hidden (non-spam)"
            response["student_name"] = "Hidden (non-spam)"
            response["student_email"] = "Hidden (non-spam)"
            response["student_gender"] = None
            response["student_stay_type"] = None
            response["student_year"] = None
            response["student_department"] = None
            logger.info(
                f"Authority {authority_id} viewing NON-SPAM complaint {complaint_id} - "
                f"Student info hidden (partial anonymity)"
            )

        return response


__all__ = ["ComplaintService"]
