"""
Vote service for voting logic and priority calculation.

Priority formula — Wilson Score Lower Bound (Bayesian ranking):
  wilson         = lower bound of 95% CI for the upvote ratio
  adjusted_score = wilson * 200   (maps 0–1 → 0–200)

  Map adjusted_score → priority:  Critical ≥ 150 | High ≥ 75 | Medium ≥ 20 | Low < 20
  Guard: never change priority by more than one level per vote update.

  Advantages over arithmetic score:
  - Accounts for sample size (1 vote isn't the same confidence as 100 votes)
  - Naturally balances upvote ratio against vote volume
  - Resilient to manipulation via mass downvotes
"""

import logging
import math
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Vote, Complaint
from src.repositories.vote_repo import VoteRepository
from src.repositories.complaint_repo import ComplaintRepository
from src.config.constants import PRIORITY_SCORES  # kept for potential external callers

logger = logging.getLogger(__name__)


class VoteService:
    """Service for vote operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vote_repo = VoteRepository(db)
        self.complaint_repo = ComplaintRepository(db)
    
    async def add_vote(
        self,
        complaint_id: UUID,
        student_roll_no: str,
        vote_type: str
    ) -> Dict[str, Any]:
        """
        Add or update vote on a complaint.
        
        Args:
            complaint_id: Complaint UUID
            student_roll_no: Student roll number
            vote_type: Upvote or Downvote
        
        Returns:
            Updated vote counts and priority
        """
        # Validate vote type
        if vote_type not in ["Upvote", "Downvote"]:
            raise ValueError("Invalid vote type. Must be 'Upvote' or 'Downvote'")
        
        # Get complaint
        complaint = await self.complaint_repo.get(complaint_id)
        if not complaint:
            raise ValueError("Complaint not found")
        
        # Check if complaint is resolved (optional: disable voting on resolved complaints)
        if complaint.status == "Resolved":
            raise ValueError("Cannot vote on resolved complaints")
        
        # Check if voting on own complaint
        if complaint.student_roll_no == student_roll_no:
            raise ValueError("Cannot vote on your own complaint")
        
        # Check if already voted
        existing_vote = await self.vote_repo.get_by_complaint_and_student(
            complaint_id, student_roll_no
        )
        
        if existing_vote:
            old_type = existing_vote.vote_type

            if old_type == vote_type:
                # Toggle off: same vote type clicked again → remove the vote
                logger.info(f"Toggle-off vote for {student_roll_no}: removing {vote_type}")
                if old_type == "Upvote":
                    await self.complaint_repo.decrement_votes(complaint_id, upvote=True)
                else:
                    await self.complaint_repo.decrement_votes(complaint_id, upvote=False)
                await self.vote_repo.delete_vote(complaint_id, student_roll_no)
                try:
                    await self.recalculate_priority(complaint_id)
                except Exception as e:
                    logger.warning(f"Priority recalc failed after toggle-off (vote still removed): {e}")
                complaint = await self.complaint_repo.get(complaint_id)
                return {
                    "complaint_id": str(complaint_id),
                    "vote_type": None,
                    "action": "removed",
                    "upvotes": complaint.upvotes,
                    "downvotes": complaint.downvotes,
                    "vote_score": complaint.upvotes - complaint.downvotes,
                    "priority_score": complaint.priority_score,
                    "priority": complaint.priority,
                    "message": "Vote removed successfully"
                }

            logger.info(f"Updating vote for {student_roll_no}: {old_type} → {vote_type}")

            # IMPORTANT: Update the vote record BEFORE any commit.
            # decrement_votes / increment_votes each commit the session, which
            # expires ALL tracked objects — including existing_vote.  If we try
            # to write existing_vote.vote_type AFTER those commits we trigger an
            # async lazy-load → greenlet_spawn error.  Setting the field here
            # means it will be flushed together with the first commit below.
            existing_vote.vote_type = vote_type
            existing_vote.updated_at = datetime.now(timezone.utc)

            # Decrement old vote (commits — also persists the vote_type change above)
            if old_type == "Upvote":
                await self.complaint_repo.decrement_votes(complaint_id, upvote=True)
            else:
                await self.complaint_repo.decrement_votes(complaint_id, upvote=False)

            # Increment new vote (commits)
            if vote_type == "Upvote":
                await self.complaint_repo.increment_votes(complaint_id, upvote=True)
            else:
                await self.complaint_repo.increment_votes(complaint_id, upvote=False)

            action = "changed"
        else:
            # Create new vote
            await self.vote_repo.create(
                complaint_id=complaint_id,
                student_roll_no=student_roll_no,
                vote_type=vote_type
            )

            # Increment vote count
            if vote_type == "Upvote":
                await self.complaint_repo.increment_votes(complaint_id, upvote=True)
            else:
                await self.complaint_repo.increment_votes(complaint_id, upvote=False)

            action = "added"

        # Recalculate priority — non-fatal: vote is already committed
        try:
            await self.recalculate_priority(complaint_id)
        except Exception as e:
            logger.warning(f"Priority recalc failed (vote still saved): {e}")

        # Get updated complaint
        complaint = await self.complaint_repo.get(complaint_id)
        
        logger.info(
            f"Vote {action}: {vote_type} by {student_roll_no} on complaint {complaint_id} "
            f"(Upvotes: {complaint.upvotes}, Downvotes: {complaint.downvotes})"
        )
        
        return {
            "complaint_id": str(complaint_id),
            "vote_type": vote_type,
            "action": action,
            "upvotes": complaint.upvotes,
            "downvotes": complaint.downvotes,
            "vote_score": complaint.upvotes - complaint.downvotes,
            "priority_score": complaint.priority_score,
            "priority": complaint.priority,
            "message": f"Vote {action} successfully"
        }
    
    async def remove_vote(
        self,
        complaint_id: UUID,
        student_roll_no: str
    ) -> Dict[str, Any]:
        """
        Remove vote from complaint (un-vote).
        
        Args:
            complaint_id: Complaint UUID
            student_roll_no: Student roll number
        
        Returns:
            Updated vote counts
        """
        vote = await self.vote_repo.get_by_complaint_and_student(
            complaint_id, student_roll_no
        )
        
        if not vote:
            raise ValueError("You have not voted on this complaint")
        
        vote_type = vote.vote_type
        
        # Decrement vote count
        if vote_type == "Upvote":
            await self.complaint_repo.decrement_votes(complaint_id, upvote=True)
        else:
            await self.complaint_repo.decrement_votes(complaint_id, upvote=False)
        
        # Delete vote
        await self.vote_repo.delete_vote(complaint_id, student_roll_no)

        # Recalculate priority — non-fatal: vote is already removed
        try:
            await self.recalculate_priority(complaint_id)
        except Exception as e:
            logger.warning(f"Priority recalc failed after remove_vote (vote still removed): {e}")

        # Get updated complaint
        complaint = await self.complaint_repo.get(complaint_id)
        
        logger.info(
            f"Vote removed: {vote_type} by {student_roll_no} on complaint {complaint_id}"
        )
        
        return {
            "complaint_id": str(complaint_id),
            "removed_vote_type": vote_type,
            "upvotes": complaint.upvotes,
            "downvotes": complaint.downvotes,
            "vote_score": complaint.upvotes - complaint.downvotes,
            "priority_score": complaint.priority_score,
            "priority": complaint.priority,
            "message": "Vote removed successfully"
        }
    
    async def get_user_vote(
        self,
        complaint_id: UUID,
        student_roll_no: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's vote on a complaint.
        
        Args:
            complaint_id: Complaint UUID
            student_roll_no: Student roll number
        
        Returns:
            Vote information or None
        """
        vote = await self.vote_repo.get_by_complaint_and_student(
            complaint_id, student_roll_no
        )
        
        if not vote:
            return None
        
        return {
            "complaint_id": str(complaint_id),
            "student_roll_no": student_roll_no,
            "vote_type": vote.vote_type,
            "voted_at": vote.created_at.isoformat(),
            "updated_at": vote.updated_at.isoformat() if vote.updated_at else None
        }
    
    # Priority level order (low → high index)
    _PRIORITY_ORDER = ["Low", "Medium", "High", "Critical"]

    def _priority_index(self, priority: str) -> int:
        try:
            return self._PRIORITY_ORDER.index(priority)
        except ValueError:
            return 1  # default to Medium index

    def _score_to_priority(self, score: float) -> str:
        if score >= 150:
            return "Critical"
        elif score >= 75:
            return "High"
        elif score >= 20:
            return "Medium"
        else:
            return "Low"

    @staticmethod
    def _wilson_lower_bound(upvotes: int, downvotes: int, z: float = 1.96) -> float:
        """
        Wilson Score Lower Bound — Bayesian confidence interval for vote ranking.

        Rewards complaints with a high upvote *ratio* backed by sufficient votes.
        A complaint with 1 upvote / 1 total is ranked below 90 upvotes / 100 total,
        even though both have a 100% / 90% ratio, because the sample is too small.

        Returns a value in [0, 1]. Multiply by 200 to get the priority_score range.
        """
        n = upvotes + downvotes
        if n == 0:
            return 0.0
        p = upvotes / n
        return (
            (p + z * z / (2 * n) - z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n))
            / (1 + z * z / n)
        )

    async def recalculate_priority(self, complaint_id: UUID) -> float:
        """
        Recalculate priority using Wilson Score Lower Bound (Bayesian ranking).

          wilson = _wilson_lower_bound(upvotes, downvotes)
          adjusted_score = wilson * 200

        Maps to priority: Critical ≥ 150 (wilson ≥ 0.75) | High ≥ 75 (0.375+) |
                          Medium ≥ 20 (0.10+) | Low < 20

        Guard: new priority cannot be more than 1 level away from the current priority.
        """
        complaint = await self.complaint_repo.get(complaint_id)
        if not complaint:
            logger.warning(f"Cannot recalculate priority — complaint {complaint_id} not found")
            return 0.0

        upvotes = complaint.upvotes or 0
        downvotes = complaint.downvotes or 0
        reach = upvotes + downvotes

        if reach == 0:
            # No votes yet — nothing to update
            return complaint.priority_score or 0.0

        # Wilson Score → priority_score (0–200 scale)
        wilson = self._wilson_lower_bound(upvotes, downvotes)
        adjusted_score = wilson * 200

        # Map score → priority level
        proposed_priority = self._score_to_priority(adjusted_score)

        # Guard: never change by more than 1 level per vote update.
        # Capture priority BEFORE update_priority_score() which commits and
        # expires the SQLAlchemy session (accessing complaint.priority afterward
        # would trigger a lazy load → async greenlet error).
        old_priority = complaint.priority
        current_idx = self._priority_index(old_priority)
        proposed_idx = self._priority_index(proposed_priority)
        guarded_idx = max(current_idx - 1, min(current_idx + 1, proposed_idx))
        guarded_priority = self._PRIORITY_ORDER[guarded_idx]

        # Persist priority_score (commits → expires session objects)
        await self.complaint_repo.update_priority_score(complaint_id, adjusted_score)

        # Update priority level only if it changed
        if guarded_priority != old_priority:
            # Re-fetch complaint since session was expired by the commit above
            fresh = await self.complaint_repo.get(complaint_id)
            if fresh:
                fresh.priority = guarded_priority
                await self.db.commit()
                logger.info(
                    f"Priority updated for {complaint_id}: {old_priority} → {guarded_priority}"
                )

        logger.info(
            f"Vote priority for {complaint_id}: up={upvotes} down={downvotes} "
            f"wilson={wilson:.4f} adj={adjusted_score:.2f} → {proposed_priority} "
            f"(was={old_priority} guarded={guarded_priority})"
        )

        return adjusted_score
    
    async def _get_filtered_vote_counts(self, complaint: Complaint) -> tuple[int, int]:
        """
        ✅ NEW: Get filtered vote counts based on complaint visibility rules.

        Only counts votes from students who can actually see the complaint:
        - Men's Hostel: Only male hostel students
        - Women's Hostel: Only female hostel students
        - Department complaints: Only students from that department
        - General: All students

        Args:
            complaint: Complaint object

        Returns:
            Tuple of (filtered_upvotes, filtered_downvotes)
        """
        from sqlalchemy import select, and_
        from src.database.models import Student

        # Get all votes for this complaint
        votes = await self.vote_repo.get_votes_by_complaint(complaint.id)

        if not votes:
            return (0, 0)

        # Get category name
        category_name = complaint.category.name if complaint.category else "General"

        # Determine filtering rules based on category
        if category_name == "Men's Hostel":
            # Only count votes from male hostel students
            eligible_roll_nos = set()
            for vote in votes:
                student_query = select(Student).where(
                    and_(
                        Student.roll_no == vote.student_roll_no,
                        Student.gender == "Male",
                        Student.stay_type == "Hostel"
                    )
                )
                result = await self.db.execute(student_query)
                student = result.scalar_one_or_none()
                if student:
                    eligible_roll_nos.add(vote.student_roll_no)

        elif category_name == "Women's Hostel":
            # Only count votes from female hostel students
            eligible_roll_nos = set()
            for vote in votes:
                student_query = select(Student).where(
                    and_(
                        Student.roll_no == vote.student_roll_no,
                        Student.gender == "Female",
                        Student.stay_type == "Hostel"
                    )
                )
                result = await self.db.execute(student_query)
                student = result.scalar_one_or_none()
                if student:
                    eligible_roll_nos.add(vote.student_roll_no)

        elif category_name == "Department" and complaint.complaint_department_id:
            # Only count votes from students in the complaint's department
            eligible_roll_nos = set()
            for vote in votes:
                student_query = select(Student).where(
                    and_(
                        Student.roll_no == vote.student_roll_no,
                        Student.department_id == complaint.complaint_department_id
                    )
                )
                result = await self.db.execute(student_query)
                student = result.scalar_one_or_none()
                if student:
                    eligible_roll_nos.add(vote.student_roll_no)

        else:
            # General complaints - count all votes
            eligible_roll_nos = {vote.student_roll_no for vote in votes}

        # Count filtered upvotes and downvotes
        filtered_upvotes = sum(1 for vote in votes if vote.student_roll_no in eligible_roll_nos and vote.vote_type == "Upvote")
        filtered_downvotes = sum(1 for vote in votes if vote.student_roll_no in eligible_roll_nos and vote.vote_type == "Downvote")

        logger.info(
            f"Filtered votes for complaint {complaint.id}: "
            f"Total={len(votes)}, Eligible={len(eligible_roll_nos)}, "
            f"Filtered_Upvotes={filtered_upvotes}, Filtered_Downvotes={filtered_downvotes}"
        )

        return (filtered_upvotes, filtered_downvotes)

    def _calculate_priority_level(self, priority_score: float) -> str:
        """Calculate priority level from score (delegates to _score_to_priority)."""
        return self._score_to_priority(priority_score)
    
    async def get_vote_statistics(
        self,
        complaint_id: UUID
    ) -> Dict[str, Any]:
        """
        ✅ ENHANCED: Get voting statistics with filtered vote counts and Reddit-style metrics.

        Args:
            complaint_id: Complaint UUID

        Returns:
            Vote statistics including filtered counts and vote ratio
        """
        complaint = await self.complaint_repo.get(complaint_id)
        if not complaint:
            raise ValueError("Complaint not found")

        # Get all votes
        votes = await self.vote_repo.get_votes_by_complaint(complaint_id)

        total_votes = len(votes)
        upvotes = complaint.upvotes
        downvotes = complaint.downvotes
        vote_score = upvotes - downvotes

        # ✅ NEW: Get filtered vote counts
        filtered_upvotes, filtered_downvotes = await self._get_filtered_vote_counts(complaint)
        filtered_total = filtered_upvotes + filtered_downvotes
        filtered_score = filtered_upvotes - filtered_downvotes

        # Calculate percentages (all votes)
        upvote_percentage = (upvotes / total_votes * 100) if total_votes > 0 else 0
        downvote_percentage = (downvotes / total_votes * 100) if total_votes > 0 else 0

        # ✅ NEW: Calculate Reddit-style vote ratio (filtered)
        vote_ratio = (filtered_upvotes / filtered_total) if filtered_total > 0 else 0.5

        return {
            "complaint_id": str(complaint_id),
            "total_votes": total_votes,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "vote_score": vote_score,
            "upvote_percentage": round(upvote_percentage, 2),
            "downvote_percentage": round(downvote_percentage, 2),
            # ✅ NEW: Filtered vote metrics
            "filtered_total_votes": filtered_total,
            "filtered_upvotes": filtered_upvotes,
            "filtered_downvotes": filtered_downvotes,
            "filtered_vote_score": filtered_score,
            "vote_ratio": round(vote_ratio, 4),  # Reddit-style upvote ratio (0.0 to 1.0)
            "vote_ratio_percentage": round(vote_ratio * 100, 2),  # As percentage
            # Priority
            "priority_score": complaint.priority_score,
            "priority": complaint.priority
        }
    
    async def get_top_voted_complaints(
        self,
        limit: int = 10,
        vote_type: str = "upvote"
    ) -> List[Dict[str, Any]]:
        """
        Get top voted complaints.
        
        Args:
            limit: Maximum number of results
            vote_type: "upvote" or "downvote"
        
        Returns:
            List of top voted complaints
        """
        from sqlalchemy import select, desc
        
        # Build query based on vote type
        if vote_type.lower() == "upvote":
            query = select(Complaint).where(
                Complaint.status != "Spam"
            ).order_by(desc(Complaint.upvotes)).limit(limit)
        else:
            query = select(Complaint).where(
                Complaint.status != "Spam"
            ).order_by(desc(Complaint.downvotes)).limit(limit)
        
        result = await self.db.execute(query)
        complaints = result.scalars().all()
        
        top_complaints = []
        for complaint in complaints:
            top_complaints.append({
                "id": str(complaint.id),
                "rephrased_text": complaint.rephrased_text[:150] + "..." if len(complaint.rephrased_text) > 150 else complaint.rephrased_text,
                "category": complaint.category.name if complaint.category else "Unknown",
                "upvotes": complaint.upvotes,
                "downvotes": complaint.downvotes,
                "vote_score": complaint.upvotes - complaint.downvotes,
                "priority": complaint.priority,
                "status": complaint.status,
                "created_at": complaint.created_at.isoformat()
            })
        
        return top_complaints
    
    async def get_student_voting_history(
        self,
        student_roll_no: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get voting history for a student.
        
        Args:
            student_roll_no: Student roll number
            limit: Maximum results
        
        Returns:
            List of votes
        """
        votes = await self.vote_repo.get_votes_by_student(student_roll_no)
        
        history = []
        for vote in votes[:limit]:
            complaint = await self.complaint_repo.get(vote.complaint_id)
            if complaint:
                history.append({
                    "complaint_id": str(vote.complaint_id),
                    "complaint_title": complaint.rephrased_text[:100] + "..." if len(complaint.rephrased_text) > 100 else complaint.rephrased_text,
                    "vote_type": vote.vote_type,
                    "voted_at": vote.created_at.isoformat(),
                    "complaint_status": complaint.status
                })
        
        return history
    
    async def bulk_recalculate_priorities(self) -> Dict[str, Any]:
        """
        Recalculate priorities for all complaints (maintenance task).
        Should be run periodically as a scheduled job.
        
        Returns:
            Recalculation statistics
        """
        from sqlalchemy import select
        
        # Get all non-spam complaints
        query = select(Complaint).where(Complaint.status != "Spam")
        result = await self.db.execute(query)
        complaints = result.scalars().all()
        
        total = len(complaints)
        updated = 0
        errors = 0
        
        logger.info(f"Starting bulk priority recalculation for {total} complaints")
        
        for complaint in complaints:
            try:
                await self.recalculate_priority(complaint.id)
                updated += 1
            except Exception as e:
                logger.error(f"Error recalculating priority for {complaint.id}: {e}")
                errors += 1
        
        logger.info(f"Bulk recalculation complete: {updated} updated, {errors} errors")
        
        return {
            "total_complaints": total,
            "updated": updated,
            "errors": errors,
            "success_rate": (updated / total * 100) if total > 0 else 0
        }


__all__ = ["VoteService"]
