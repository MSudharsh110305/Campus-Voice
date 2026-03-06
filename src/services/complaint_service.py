"""
Complaint service with main business logic.

✅ UPDATED: Binary image storage support
✅ UPDATED: Image verification integration
✅ UPDATED: No image_url field usage
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone
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
from src.config.constants import PRIORITY_SCORES

logger = logging.getLogger(__name__)


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

        # Build context for LLM.
        # Pass gender and stay_type so the LLM can pick the correct hostel
        # category (Men's vs Women's) directly when the complaint text is ambiguous.
        # The LLM prompt already guards against hostel-bias for non-hostel text.
        context = {
            "department": student.department.code if (student.department and hasattr(student.department, 'code')) else "Unknown",
            "gender": student.gender or "",
            "stay_type": student.stay_type or "",
        }

        # LLM Processing
        logger.info(f"Processing complaint for {student_roll_no}")

        # Flag: set to True if spam is detected; complaint will be saved as spam
        is_spam_complaint = False
        spam_complaint_reason = None

        try:
            # 1. Check for spam FIRST (before processing)
            spam_check = await llm_service.detect_spam(original_text)

            # Save as spam (not block) when LLM has high confidence
            SPAM_CONFIDENCE_THRESHOLD = 0.75
            spam_confident = spam_check.get("confidence", 1.0) >= SPAM_CONFIDENCE_THRESHOLD
            if spam_check.get("is_spam") and spam_confident:
                spam_complaint_reason = spam_check.get("reason", "Content flagged as spam or abusive")
                is_spam_complaint = True
                logger.warning(
                    f"Spam complaint detected for {student_roll_no}: {spam_complaint_reason} — saving as spam"
                )

            llm_failed = False
            if not is_spam_complaint:
                # 2. Categorize and get priority (✅ NOW INCLUDES department detection)
                categorization = await llm_service.categorize_complaint(original_text, context)

                # Bug 2 fix: Do NOT force-correct hostel category based on student
                # stay_type. The LLM prompt now categorises purely on complaint text.
                # Only apply the academic override (keyword-based deterministic safety net).
                ai_category = categorization.get("category")
                categorization = llm_service._apply_academic_override(original_text, categorization)
                # BUG-014: also apply facility/hygiene override
                categorization = llm_service._apply_facility_general_override(original_text, categorization)
                ai_category = categorization.get("category")

                # Validate hostel category against student profile
                if ai_category in ("Men's Hostel", "Women's Hostel"):
                    # Check stay type - Day scholars cannot submit hostel complaints
                    if student.stay_type == "Day Scholar":
                        raise ValueError("Day scholars cannot submit hostel complaints")

                    # Auto-correct hostel category to match student gender.
                    # LLM doesn't know the student's gender, so it may guess wrong.
                    # Silently correct rather than rejecting valid hostel complaints.
                    if ai_category == "Men's Hostel" and student.gender == "Female":
                        logger.info(
                            f"Auto-correcting hostel category: Men's Hostel → Women's Hostel for female student {student_roll_no}"
                        )
                        categorization["category"] = "Women's Hostel"
                        ai_category = "Women's Hostel"

                    elif ai_category == "Women's Hostel" and student.gender == "Male":
                        logger.info(
                            f"Auto-correcting hostel category: Women's Hostel → Men's Hostel for male student {student_roll_no}"
                        )
                        categorization["category"] = "Men's Hostel"
                        ai_category = "Men's Hostel"

                # 3. Rephrase for professionalism.
                # If rephrase_complaint returns None (gibberish/repeated words), flag as spam
                # but still save the complaint (using original_text as fallback).
                rephrased_text = await llm_service.rephrase_complaint(original_text)
                if rephrased_text is None:
                    logger.warning(
                        f"Rephraser returned None (gibberish/repeated words) for {student_roll_no} — saving as spam"
                    )
                    is_spam_complaint = True
                    spam_complaint_reason = "Content appears to be meaningless or contains repeated words"
                    rephrased_text = original_text  # Use original as fallback for storage

                # 4. Check if image is REQUIRED for this complaint (only if still not spam)
                if not is_spam_complaint:
                    image_requirement = await llm_service.check_image_requirement(
                        complaint_text=original_text,
                        category=categorization.get("category")
                    )
                    if image_requirement.get("image_required") and not image_file:
                        reason = image_requirement.get("reasoning", "Visual evidence required")
                        suggested = image_requirement.get("suggested_evidence", "relevant photo")
                        error_msg = (
                            f"This complaint requires supporting images. {reason}. "
                            f"Please upload at least one image showing {suggested}."
                        )
                        logger.warning(f"Image required but not provided for {student_roll_no}: {reason}")
                        raise ValueError(error_msg)
                else:
                    image_requirement = {"image_required": False}
            else:
                # Spam detected early — skip ALL LLM processing, use safe defaults
                logger.info(f"Skipping LLM pipeline for spam complaint from {student_roll_no}")
                categorization = {
                    "category": "General",
                    "target_department": context.get("department", "CSE"),
                    "priority": "Low",
                    "confidence": 1.0,
                    "is_against_authority": False,
                }
                rephrased_text = original_text
                image_requirement = {"image_required": False}

        except ValueError:
            # Re-raise ValueError (spam rejection or missing image)
            raise
        except Exception as e:
            logger.error(f"LLM processing error: {e}")
            # Fallback values
            categorization = {
                "category": "General",
                "target_department": context.get("department", "CSE"),
                "priority": "Medium",
                "confidence": 0.5,
                "is_against_authority": False
            }
            rephrased_text = original_text
            image_requirement = {"image_required": False}
            llm_failed = True

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

        # Calculate initial priority score
        priority = categorization.get("priority", "Medium")
        priority_score = PRIORITY_SCORES.get(priority, 50.0)

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

                # BUG-006 fix: mark complaint as spam if image is irrelevant or low confidence
                img_is_relevant = verification_result.get("is_relevant", True)
                img_confidence = verification_result.get("confidence_score", 1.0)
                if not img_is_relevant or img_confidence < 0.5:
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

                # BUG-016: Detect complaints against hostel staff by keyword and apply bypass routing
                _text_lower = original_text.lower()
                _hostel_staff_bypass_type = None
                _hostel_staff_keywords = {
                    "senior deputy warden": "Senior Deputy Warden",
                    "deputy warden": "Men's Hostel Deputy Warden",  # generic — may be men's or women's
                    "warden": "Men's Hostel Warden",               # generic — may be men's or women's
                }
                for kw, authority_type in _hostel_staff_keywords.items():
                    if kw in _text_lower:
                        _hostel_staff_bypass_type = authority_type
                        break  # Use most-specific match (ordered from most to least specific)

                authority = await authority_service.route_complaint(
                    self.db,
                    category_id,
                    target_department_id,
                    categorization.get("is_against_authority", False) or (_hostel_staff_bypass_type is not None),
                    complaint_about_authority_type=_hostel_staff_bypass_type
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
                            f"New complaint assigned to you: {_category_name} complaint "
                            f"from student {student_roll_no}. "
                            f"Issue: {rephrased_text[:80]}..."
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
            f"Image Required: {image_requirement.get('image_required', False)}, "
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
                else "Complaint submitted successfully"
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
            "image_was_required": image_requirement.get("image_required", False),
            "image_requirement_reasoning": image_requirement.get("reasoning")
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
