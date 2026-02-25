"""
Complaint repository with specialized queries.

✅ FIXED: Added create() method with image binary support
✅ FIXED: Added image-specific query methods
✅ FIXED: Updated get_with_relations() to include image verification logs
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
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
        conditions = [Complaint.student_roll_no == student_roll_no]
        if status:
            conditions.append(Complaint.status == status)
        
        query = (
            select(Complaint)
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
            .where(Complaint.category_id == category_id)
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
            .where(Complaint.status == status)
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
            .where(Complaint.priority == priority)
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
        conditions = [Complaint.assigned_authority_id == authority_id]
        if status:
            conditions.append(Complaint.status == status)

        query = (
            select(Complaint)
            .options(
                selectinload(Complaint.student),
                selectinload(Complaint.category)
            )
            .where(and_(*conditions))
            .order_by(desc(Complaint.priority_score))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_public_feed(
        self,
        student_stay_type: str,
        student_department_id: int,
        student_gender: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Complaint]:
        """
        Get public feed filtered by visibility rules.

        Args:
            student_stay_type: Student's stay type (Hostel/Day Scholar)
            student_department_id: Student's department ID
            student_gender: Student's gender (Male/Female/Other) for hostel filtering
            skip: Number to skip
            limit: Maximum results

        Returns:
            List of complaints
        """
        from src.database.models import Student

        # Get category IDs for hostel categories
        mens_hostel_query = select(ComplaintCategory.id).where(ComplaintCategory.name == "Men's Hostel")
        womens_hostel_query = select(ComplaintCategory.id).where(ComplaintCategory.name == "Women's Hostel")
        mens_hostel_result = await self.session.execute(mens_hostel_query)
        womens_hostel_result = await self.session.execute(womens_hostel_query)
        mens_hostel_id = mens_hostel_result.scalar()
        womens_hostel_id = womens_hostel_result.scalar()

        # Get General and Disciplinary Committee category IDs
        general_query = select(ComplaintCategory.id).where(ComplaintCategory.name == "General")
        disciplinary_query = select(ComplaintCategory.id).where(ComplaintCategory.name == "Disciplinary Committee")
        general_result = await self.session.execute(general_query)
        disciplinary_result = await self.session.execute(disciplinary_query)
        general_id = general_result.scalar()
        disciplinary_id = disciplinary_result.scalar()

        # Bug 4 fix: Exclude Spam complaints from the public feed in addition to Closed.
        # Spam complaints (flagged by authority or auto-detected) must never be visible
        # in any public or department feed.
        conditions = [
            Complaint.visibility == "Public",
            Complaint.status != "Closed",
            Complaint.status != "Spam",
            Complaint.is_marked_as_spam == False,
        ]

        # Collect hostel category IDs
        hostel_category_ids = [cid for cid in [mens_hostel_id, womens_hostel_id] if cid is not None]

        if student_stay_type == "Day Scholar":
            # ✅ FIX: Dual-layer hostel exclusion for day scholars:
            # Layer 1: Exclude by category_id (catches correctly-categorized hostel complaints)
            if mens_hostel_id:
                conditions.append(Complaint.category_id != mens_hostel_id)
            if womens_hostel_id:
                conditions.append(Complaint.category_id != womens_hostel_id)
            # Layer 2: Exclude complaints submitted by hostel students that aren't
            # General/Disciplinary (catches LLM miscategorized hostel complaints)
            if hostel_category_ids:
                hostel_submitters_sq = (
                    select(Student.roll_no)
                    .where(Student.stay_type == "Hostel")
                    .scalar_subquery()
                )
                non_general_disc_ids = [
                    cid for cid in hostel_category_ids
                ]
                # If category is NOT general/disciplinary AND submitter is a hostel student → exclude
                safe_category_ids = [cid for cid in [general_id, disciplinary_id] if cid is not None]
                if safe_category_ids:
                    # Exclude: submitter is hostel student AND category is not in safe categories
                    conditions.append(
                        or_(
                            Complaint.student_roll_no.notin_(hostel_submitters_sq),
                            Complaint.category_id.in_(safe_category_ids)
                        )
                    )
                else:
                    # No safe categories found - just exclude all hostel submitters' non-hostel posts
                    conditions.append(
                        Complaint.student_roll_no.notin_(hostel_submitters_sq)
                    )
        else:
            # Hostel students: Filter by gender
            # Men should not see women's hostel complaints
            # Women should not see men's hostel complaints
            if student_gender == "Male" and womens_hostel_id:
                conditions.append(Complaint.category_id != womens_hostel_id)
            elif student_gender == "Female" and mens_hostel_id:
                conditions.append(Complaint.category_id != mens_hostel_id)
            # For "Other" gender, show both hostel categories

        # Bug 1 fix: Hostel complaints must be visible to ALL same-gender hostel
        # students regardless of department. The department filter must NOT apply to
        # hostel-category complaints.
        #
        # Students can see:
        # 1. Men's Hostel complaints → any male hostel student (no dept restriction)
        # 2. Women's Hostel complaints → any female hostel student (no dept restriction)
        # 3. Complaints from their own department (Department category)
        # 4. General category complaints (visible to all)
        # 5. Disciplinary Committee complaints (visible to all)
        inter_dept_conditions = [
            Complaint.complaint_department_id == student_department_id
        ]
        if general_id:
            inter_dept_conditions.append(Complaint.category_id == general_id)
        if disciplinary_id:
            inter_dept_conditions.append(Complaint.category_id == disciplinary_id)

        # ✅ BUG 1 FIX: Hostel complaints are visible to all same-gender hostel students —
        # no department restriction. Only add hostel pass-through for hostel students
        # (day scholars are already excluded above via the category_id != hostel_id conditions).
        if student_stay_type != "Day Scholar":
            if student_gender == "Male" and mens_hostel_id:
                inter_dept_conditions.append(Complaint.category_id == mens_hostel_id)
            elif student_gender == "Female" and womens_hostel_id:
                inter_dept_conditions.append(Complaint.category_id == womens_hostel_id)
            elif student_gender not in ("Male", "Female"):
                # "Other" gender hostel students: show both hostel categories
                for hid in hostel_category_ids:
                    inter_dept_conditions.append(Complaint.category_id == hid)

        conditions.append(or_(*inter_dept_conditions))

        query = (
            select(Complaint)
            .options(selectinload(Complaint.category))
            .where(and_(*conditions))
            .order_by(desc(Complaint.submitted_at))  # Newest first
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

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
                    Complaint.status.in_(["Raised", "In Progress"])
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
            .where(Complaint.is_marked_as_spam == True)
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
        conditions = [Complaint.student_roll_no == student_roll_no]
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
