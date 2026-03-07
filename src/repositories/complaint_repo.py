"""
Complaint repository with specialized queries.

✅ FIXED: Added create() method with image binary support
✅ FIXED: Added image-specific query methods
✅ FIXED: Updated get_with_relations() to include image verification logs
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
import math
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.database.models import Complaint, Student, Authority, ComplaintCategory
from src.repositories.base import BaseRepository


class ComplaintRepository(BaseRepository[Complaint]):
    """Repository for Complaint operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Complaint)
    
    # ==================== CREATE OPERATIONS ====================
    
    async def create(
        self,
        student_roll_no: str,
        category_id: int,
        original_text: str,
        rephrased_text: str,
        visibility: str,
        priority: str,
        priority_score: float,
        status: str,
        is_marked_as_spam: bool = False,
        spam_reason: Optional[str] = None,
        complaint_department_id: Optional[int] = None,
        complainant_department_id: Optional[int] = None,
        is_cross_department: bool = False,
        is_anonymous: bool = False,
        # ✅ NEW: Image binary parameters
        image_data: Optional[bytes] = None,
        image_filename: Optional[str] = None,
        image_mimetype: Optional[str] = None,
        image_size: Optional[int] = None,
        thumbnail_data: Optional[bytes] = None,
        thumbnail_size: Optional[int] = None,
        image_verified: bool = False,
        image_verification_status: Optional[str] = None
    ) -> Complaint:
        """
        Create new complaint with optional image.
        
        Args:
            student_roll_no: Student roll number
            category_id: Category ID
            original_text: Original complaint text
            rephrased_text: Rephrased text from LLM
            visibility: Visibility level (Private/Department/Public)
            priority: Priority level (Low/Medium/High/Critical)
            priority_score: Numeric priority score
            status: Initial status (Raised/Spam)
            is_marked_as_spam: Whether complaint is spam
            spam_reason: Reason if marked as spam
            complaint_department_id: Department ID
            image_data: Image binary data
            image_filename: Original filename
            image_mimetype: MIME type (image/jpeg, image/png)
            image_size: Size in bytes
            thumbnail_data: Thumbnail binary data
            thumbnail_size: Thumbnail size in bytes
            image_verified: Whether image is verified
            image_verification_status: Verification status (Pending/Verified/Rejected)
        
        Returns:
            Created complaint
        """
        # ✅ FIXED: Use timezone-aware datetime
        current_time = datetime.now(timezone.utc)
        
        complaint = Complaint(
            student_roll_no=student_roll_no,
            category_id=category_id,
            original_text=original_text,
            rephrased_text=rephrased_text,
            visibility=visibility,
            priority=priority,
            priority_score=priority_score,
            status=status,
            is_marked_as_spam=is_marked_as_spam,
            spam_reason=spam_reason,
            complaint_department_id=complaint_department_id,
            complainant_department_id=complainant_department_id,
            is_cross_department=is_cross_department,
            is_anonymous=is_anonymous,
            submitted_at=current_time,
            updated_at=current_time,
            # ✅ NEW: Image fields
            image_data=image_data,
            image_filename=image_filename,
            image_mimetype=image_mimetype,
            image_size=image_size,
            thumbnail_data=thumbnail_data,
            thumbnail_size=thumbnail_size,
            image_verified=image_verified,
            image_verification_status=image_verification_status
        )
        
        self.session.add(complaint)
        await self.session.commit()
        await self.session.refresh(complaint)
        return complaint
    
    # ==================== READ OPERATIONS ====================
    
    async def get_with_relations(self, complaint_id: UUID) -> Optional[Complaint]:
        """
        Get complaint with all relationships loaded.
        
        Args:
            complaint_id: Complaint UUID
        
        Returns:
            Complaint with relations or None
        """
        query = (
            select(Complaint)
            .options(
                selectinload(Complaint.student),
                selectinload(Complaint.category),
                selectinload(Complaint.assigned_authority),
                selectinload(Complaint.complaint_department),
                selectinload(Complaint.comments),
                selectinload(Complaint.status_updates),
                selectinload(Complaint.image_verification_logs)
            )
            .where(Complaint.id == complaint_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_student(
        self,
        student_roll_no: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Complaint]:
        """
        Get complaints by student.
        
        Args:
            student_roll_no: Student roll number
            skip: Number to skip
            limit: Maximum results
            status: Optional status filter
        
        Returns:
            List of complaints
        """
        conditions = [
            Complaint.student_roll_no == student_roll_no,
            Complaint.is_deleted == False,
        ]
        if status:
            conditions.append(Complaint.status == status)

        query = (
            select(Complaint)
            .options(selectinload(Complaint.category), selectinload(Complaint.assigned_authority))
            .where(and_(*conditions))
            .order_by(desc(Complaint.submitted_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_category(
        self,
        category_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Complaint]:
        """
        Get complaints by category.
        
        Args:
            category_id: Category ID
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of complaints
        """
        query = (
            select(Complaint)
            .where(and_(Complaint.category_id == category_id, Complaint.is_deleted == False))
            .order_by(desc(Complaint.priority_score))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Complaint]:
        """
        Get complaints by status.
        
        Args:
            status: Complaint status
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of complaints
        """
        query = (
            select(Complaint)
            .where(and_(Complaint.status == status, Complaint.is_deleted == False))
            .order_by(desc(Complaint.submitted_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_priority(
        self,
        priority: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Complaint]:
        """
        Get complaints by priority.
        
        Args:
            priority: Priority level
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of complaints
        """
        query = (
            select(Complaint)
            .where(and_(Complaint.priority == priority, Complaint.is_deleted == False))
            .order_by(desc(Complaint.priority_score))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_assigned_to_authority(
        self,
        authority_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Complaint]:
        """
        Get complaints assigned to an authority.
        
        Args:
            authority_id: Authority ID
            skip: Number to skip
            limit: Maximum results
            status: Optional status filter
        
        Returns:
            List of complaints
        """
        conditions = [
            Complaint.assigned_authority_id == authority_id,
            Complaint.is_deleted == False,
        ]
        if status:
            conditions.append(Complaint.status == status)

        # Fetch all assigned complaints — Priority Queue with Aging sorts in Python
        query = (
            select(Complaint)
            .options(
                selectinload(Complaint.student),
                selectinload(Complaint.category)
            )
            .where(and_(*conditions))
        )
        result = await self.session.execute(query)
        complaints = list(result.scalars().all())

        # Priority Queue with Aging:
        #   aging_score = priority_score + (hours_open / 24) * 10 + upvotes * 2
        # Older unresolved complaints automatically rise in the queue,
        # preventing starvation of long-pending issues.
        now_utc = datetime.now(timezone.utc)

        def _aging_score(c: Complaint) -> float:
            base = c.priority_score or 0.0
            submitted = c.submitted_at
            if submitted is not None:
                if submitted.tzinfo is None:
                    submitted = submitted.replace(tzinfo=timezone.utc)
                hours_open = max(0.0, (now_utc - submitted).total_seconds() / 3600)
            else:
                hours_open = 0.0
            return base + (hours_open / 24) * 10 + (c.upvotes or 0) * 2

        complaints.sort(key=_aging_score, reverse=True)
        return complaints[skip: skip + limit]

    async def get_public_feed(
        self,
        student_stay_type: str,
        student_department_id: int,
        student_gender: Optional[str] = None,
        student_roll_no: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        category_id: Optional[int] = None,
        sort_by: str = "hot",
    ) -> List[Complaint]:
        """
        Get public feed filtered by visibility rules.

        Visibility rules enforced:
          H1 — Day Scholars never see hostel complaints
          H2 — Male hostel students see only Men's Hostel; Female see only Women's Hostel
          H3 — Hostel complaints are cross-department (all same-gender hostel students see them)
          D1 — Same-department students see Department complaints
          D2 — Cross-dept: both target dept AND submitter's dept see the complaint
          D3 — Other departments do NOT see department complaints
          D4 — Day Scholars and hostel students from same dept both see dept complaints
          G1 — All students see General complaints (unless Private)
          DC1 — Disciplinary Committee complaints NEVER appear in public feed

        Args:
            student_stay_type: Student's stay type (Hostel/Day Scholar)
            student_department_id: Student's department ID
            student_gender: Student's gender (Male/Female/Other) for hostel filtering
            student_roll_no: Student's roll number for self-visibility
            skip: Number to skip
            limit: Maximum results
            category_id: Optional category filter
            sort_by: Sort order (hot/new/top)

        Returns:
            List of complaints
        """
        # Resolve category IDs once
        cat_id_query = select(ComplaintCategory.id, ComplaintCategory.name)
        cat_id_result = await self.session.execute(cat_id_query)
        cat_name_to_id: dict = {row[1]: row[0] for row in cat_id_result.all()}

        mens_hostel_id = cat_name_to_id.get("Men's Hostel")
        womens_hostel_id = cat_name_to_id.get("Women's Hostel")
        general_id = cat_name_to_id.get("General")
        disciplinary_id = cat_name_to_id.get("Disciplinary Committee")
        department_id = cat_name_to_id.get("Department")

        # Base conditions applied to EVERY complaint in the feed:
        # - Must be Public visibility (Private = only submitter sees it)
        # - Must not be Closed or Spam
        # - DC1: Disciplinary Committee complaints NEVER appear in public feed
        # - Hide merged-away duplicates (they have a canonical complaint)
        # - Hide soft-deleted complaints
        conditions = [
            Complaint.visibility == "Public",
            Complaint.status != "Closed",
            Complaint.status != "Spam",
            Complaint.is_marked_as_spam == False,
            Complaint.merged_into_id == None,  # Hide merged-away duplicates
            Complaint.is_deleted == False,
        ]

        # DC1: Always exclude Disciplinary Committee from public feed
        if disciplinary_id:
            conditions.append(Complaint.category_id != disciplinary_id)

        # H1: Day Scholars never see hostel complaints (either gender)
        if student_stay_type == "Day Scholar":
            if mens_hostel_id:
                conditions.append(Complaint.category_id != mens_hostel_id)
            if womens_hostel_id:
                conditions.append(Complaint.category_id != womens_hostel_id)
        else:
            # H2: Hostel students see only their gender's hostel complaints
            if student_gender == "Male" and womens_hostel_id:
                conditions.append(Complaint.category_id != womens_hostel_id)
            elif student_gender == "Female" and mens_hostel_id:
                conditions.append(Complaint.category_id != mens_hostel_id)
            # "Other" gender hostel students: show both hostel categories (no extra exclusion)

        # Now build per-category OR conditions to determine which non-excluded complaints
        # this student is allowed to see.  Each branch handles one category type.
        visible_conditions = []

        # G1: General complaints visible to all students (already excluded Private via base conditions)
        if general_id:
            visible_conditions.append(Complaint.category_id == general_id)

        # H3: Hostel complaints visible to all same-gender hostel students (no dept filter)
        # (Day Scholars already excluded above via the NOT conditions on base conditions)
        if student_stay_type != "Day Scholar":
            if student_gender == "Male" and mens_hostel_id:
                visible_conditions.append(Complaint.category_id == mens_hostel_id)
            elif student_gender == "Female" and womens_hostel_id:
                visible_conditions.append(Complaint.category_id == womens_hostel_id)
            elif student_gender not in ("Male", "Female"):
                # "Other" gender hostel students see both hostel categories
                hostel_ids = [i for i in [mens_hostel_id, womens_hostel_id] if i is not None]
                if hostel_ids:
                    visible_conditions.append(Complaint.category_id.in_(hostel_ids))

        # D1/D2/D4: Department complaints visible if:
        #   - complaint targets this student's department (D1), OR
        #   - complaint was filed BY a student in this department, i.e. complainant_department_id matches (D2)
        #   Both hostel and day-scholar students in the department see it (D4)
        if department_id:
            dept_visible = or_(
                # D1: complaint targets this student's department
                Complaint.complaint_department_id == student_department_id,
                # D2: complaint was submitted by someone from this student's department
                Complaint.complainant_department_id == student_department_id,
            )
            visible_conditions.append(
                and_(Complaint.category_id == department_id, dept_visible)
            )

        # Self-visibility: a student always sees their own public complaints regardless of category
        if student_roll_no:
            visible_conditions.append(Complaint.student_roll_no == student_roll_no)

        # Combine: complaint must satisfy base conditions AND at least one visible_condition
        if visible_conditions:
            conditions.append(or_(*visible_conditions))
        else:
            # No visible conditions → no results (safety guard)
            conditions.append(False)

        # Optional category filter
        if category_id is not None:
            conditions.append(Complaint.category_id == category_id)

        # Fetch up to 1000 matching complaints; sort in Python for flexibility.
        query = (
            select(Complaint)
            .options(selectinload(Complaint.category), selectinload(Complaint.assigned_authority))
            .where(and_(*conditions))
            .order_by(desc(Complaint.submitted_at))  # Pre-sort newest so we cap at 1000 sensibly
            .limit(1000)
        )
        result = await self.session.execute(query)
        complaints = list(result.scalars().all())

        now_utc = datetime.now(timezone.utc)

        def _hot_score(c: Complaint) -> float:
            """True HN Hot Score with logarithmic scaling.
            log10(max(1, net_votes)) / (age_hours + 2)^1.5
            Logarithmic scaling prevents vote-bombing: 100 votes is only 2x better than 1, not 100x.
            Merged canonical complaints get a boost from their combined votes."""
            import math
            submitted = c.submitted_at
            if submitted is None:
                age_hours = 999999.0
            else:
                if submitted.tzinfo is None:
                    submitted = submitted.replace(tzinfo=timezone.utc)
                age_hours = max(0.0, (now_utc - submitted).total_seconds() / 3600)
            votes = max(1, (c.upvotes or 0) - (c.downvotes or 0))
            log_votes = math.log10(votes)
            return log_votes / (age_hours + 2) ** 1.5

        # Apply sort order
        if sort_by == "new":
            complaints.sort(key=lambda c: c.submitted_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        elif sort_by == "top":
            complaints.sort(key=lambda c: (c.upvotes or 0) - (c.downvotes or 0), reverse=True)
        else:  # default: "hot"
            complaints.sort(key=_hot_score, reverse=True)

        return complaints[skip: skip + limit]

    async def get_high_priority(self, limit: int = 50) -> List[Complaint]:
        """
        Get high priority complaints.
        
        Args:
            limit: Maximum results
        
        Returns:
            List of high priority complaints
        """
        query = (
            select(Complaint)
            .where(
                and_(
                    Complaint.priority.in_(["High", "Critical"]),
                    Complaint.status.in_(["Raised", "In Progress"]),
                    Complaint.is_deleted == False,
                )
            )
            .order_by(desc(Complaint.priority_score))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_spam_flagged(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Complaint]:
        """
        Get spam flagged complaints.
        
        Args:
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of spam complaints
        """
        query = (
            select(Complaint)
            .where(and_(Complaint.is_marked_as_spam == True, Complaint.is_deleted == False))
            .order_by(desc(Complaint.spam_flagged_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    # ==================== IMAGE-SPECIFIC QUERIES ====================
    
    async def get_with_images(
        self,
        skip: int = 0,
        limit: int = 100,
        verified_only: bool = False
    ) -> List[Complaint]:
        """
        Get complaints that have images attached.
        
        Args:
            skip: Number to skip
            limit: Maximum results
            verified_only: Only return verified images
        
        Returns:
            List of complaints with images
        """
        conditions = [Complaint.image_data.isnot(None)]
        
        if verified_only:
            conditions.append(Complaint.image_verified == True)
        
        query = (
            select(Complaint)
            .where(and_(*conditions))
            .order_by(desc(Complaint.submitted_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_pending_image_verification(
        self,
        limit: int = 50
    ) -> List[Complaint]:
        """
        Get complaints with images pending verification.
        
        Args:
            limit: Maximum results
        
        Returns:
            List of complaints with unverified images
        """
        query = (
            select(Complaint)
            .options(selectinload(Complaint.category))
            .where(
                and_(
                    Complaint.image_data.isnot(None),
                    Complaint.image_verification_status == "Pending"
                )
            )
            .order_by(desc(Complaint.submitted_at))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_rejected_images(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Complaint]:
        """
        Get complaints with rejected images.
        
        Args:
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of complaints with rejected images
        """
        query = (
            select(Complaint)
            .where(
                and_(
                    Complaint.image_data.isnot(None),
                    Complaint.image_verification_status == "Rejected"
                )
            )
            .order_by(desc(Complaint.submitted_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def count_images(self) -> Dict[str, int]:
        """
        Count images by verification status.
        
        Returns:
            Dictionary of image counts
        """
        # Total with images
        total_query = select(func.count(Complaint.id)).where(
            Complaint.image_data.isnot(None)
        )
        total_result = await self.session.execute(total_query)
        total_images = total_result.scalar() or 0
        
        # By verification status
        status_query = (
            select(
                Complaint.image_verification_status,
                func.count(Complaint.id)
            )
            .where(Complaint.image_data.isnot(None))
            .group_by(Complaint.image_verification_status)
        )
        status_result = await self.session.execute(status_query)
        status_counts = dict(status_result.all())
        
        return {
            "total": total_images,
            "verified": status_counts.get("Verified", 0),
            "pending": status_counts.get("Pending", 0),
            "rejected": status_counts.get("Rejected", 0),
            "error": status_counts.get("Error", 0)
        }
    
    # ==================== UPDATE OPERATIONS ====================
    
    async def update_image_verification(
        self,
        complaint_id: UUID,
        is_verified: bool,
        verification_status: str
    ) -> bool:
        """
        Update image verification status.
        
        Args:
            complaint_id: Complaint UUID
            is_verified: Whether image is verified
            verification_status: Verification status (Verified/Rejected/Error)
        
        Returns:
            True if successful
        """
        complaint = await self.get(complaint_id)
        if complaint and complaint.image_data:
            complaint.image_verified = is_verified
            complaint.image_verification_status = verification_status
            complaint.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return True
        return False
    
    async def update_priority_score(
        self,
        complaint_id: UUID,
        new_score: float
    ) -> bool:
        """
        Update complaint priority score.
        
        Args:
            complaint_id: Complaint UUID
            new_score: New priority score
        
        Returns:
            True if successful
        """
        complaint = await self.get(complaint_id)
        if complaint:
            complaint.priority_score = new_score
            
            # Update priority level based on score
            if new_score >= 200:
                complaint.priority = "Critical"
            elif new_score >= 100:
                complaint.priority = "High"
            elif new_score >= 50:
                complaint.priority = "Medium"
            else:
                complaint.priority = "Low"
            
            complaint.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return True
        return False
    
    async def increment_votes(
        self,
        complaint_id: UUID,
        upvote: bool = True
    ) -> bool:
        """
        Increment upvote or downvote count.
        
        Args:
            complaint_id: Complaint UUID
            upvote: True for upvote, False for downvote
        
        Returns:
            True if successful
        """
        complaint = await self.get(complaint_id)
        if complaint:
            if upvote:
                complaint.upvotes += 1
            else:
                complaint.downvotes += 1
            complaint.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return True
        return False
    
    async def decrement_votes(
        self,
        complaint_id: UUID,
        upvote: bool = True
    ) -> bool:
        """
        Decrement upvote or downvote count.
        
        Args:
            complaint_id: Complaint UUID
            upvote: True for upvote, False for downvote
        
        Returns:
            True if successful
        """
        complaint = await self.get(complaint_id)
        if complaint:
            if upvote and complaint.upvotes > 0:
                complaint.upvotes -= 1
            elif not upvote and complaint.downvotes > 0:
                complaint.downvotes -= 1
            complaint.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            return True
        return False
    
    # ==================== STATISTICS ====================
    
    async def count_by_status(self) -> Dict[str, int]:
        """
        Count complaints by status.
        
        Returns:
            Dictionary of status counts
        """
        query = (
            select(Complaint.status, func.count(Complaint.id))
            .group_by(Complaint.status)
        )
        result = await self.session.execute(query)
        return dict(result.all())
    
    async def count_by_category(self) -> Dict[str, int]:
        """
        Count complaints by category.
        
        Returns:
            Dictionary of category counts
        """
        query = (
            select(ComplaintCategory.name, func.count(Complaint.id))
            .join(Complaint.category)
            .group_by(ComplaintCategory.name)
        )
        result = await self.session.execute(query)
        return dict(result.all())
    
    async def count_by_priority(self) -> Dict[str, int]:
        """
        Count complaints by priority.
        
        Returns:
            Dictionary of priority counts
        """
        query = (
            select(Complaint.priority, func.count(Complaint.id))
            .group_by(Complaint.priority)
        )
        result = await self.session.execute(query)
        return dict(result.all())
    
    async def count_by_student(
        self,
        student_roll_no: str,
        status: Optional[str] = None
    ) -> int:
        """
        Count complaints by student, optionally filtered by status.
        """
        conditions = [
            Complaint.student_roll_no == student_roll_no,
            Complaint.is_deleted == False,
        ]
        if status:
            conditions.append(Complaint.status == status)

        query = select(func.count(Complaint.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_pending_for_escalation(
        self,
        hours: int = 48
    ) -> List[Complaint]:
        """
        Get complaints pending for escalation.
        
        Args:
            hours: Hours threshold for escalation
        
        Returns:
            List of complaints needing escalation
        """
        threshold_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = (
            select(Complaint)
            .where(
                and_(
                    Complaint.status == "Raised",
                    Complaint.assigned_at < threshold_time
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()


__all__ = ["ComplaintRepository"]
