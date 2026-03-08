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

    @staticmethod
    def _wilson_lower_bound(upvotes: int, downvotes: int, z: float = 1.96) -> float:
        """
        Wilson Score Lower Bound — Bayesian confidence interval for vote ranking.

        Rewards complaints with a high upvote *ratio* backed by sufficient votes.
        A complaint with 1 upvote / 1 total is ranked below 90 upvotes / 100 total,
        even though both have a 100% / 90% ratio, because the sample is too small.

        Returns a value in [0, 1].
        """
        n = upvotes + downvotes
        if n == 0:
            return 0.0
        p = upvotes / n
        return (
            (p + z * z / (2 * n) - z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n))
            / (1 + z * z / n)
        )

    def _engagement_priority(
        self, upvotes: int, downvotes: int, reach: int, view_count: int
    ) -> tuple:
        """
        Engagement-aware priority score combining Wilson Score + community engagement rate.

        Formula:
            vote_rate       = total_votes / max(reach, 1)   capped at 1.0
            engagement_factor = 1.0 + (vote_rate * 2.0)     range [1.0, 3.0]
            adjusted_score  = wilson * 100 * engagement_factor

        This prevents a small group of friends inflating priority:
            3 upvotes / reach=100  → vote_rate=0.03 → factor=1.06 → ~46  (Medium)
            3 upvotes / reach=5    → vote_rate=0.60 → factor=2.20 → ~97  (High — small group, all engaged)
            30 upvotes / reach=100 → vote_rate=0.30 → factor=1.60 → ~141 (High, near Critical)
            50 upvotes / reach=100 → vote_rate=0.50 → factor=2.00 → ~186 (Critical)

        Returns (adjusted_score: float, priority: str)
        """
        total_votes = upvotes + downvotes
        if total_votes == 0:
            return 0.0, "Low"

        wilson = self._wilson_lower_bound(upvotes, downvotes)
        vote_rate = min(total_votes / max(reach, 1), 1.0)
        engagement_factor = 1.0 + (vote_rate * 2.0)          # [1.0, 3.0]
        adjusted_score = wilson * 100 * engagement_factor     # [0, ~300]

        if adjusted_score >= 150:
            priority = "Critical"
        elif adjusted_score >= 75:
            priority = "High"
        elif adjusted_score >= 25:
            priority = "Medium"
        else:
            priority = "Low"

        return adjusted_score, priority

    # ── Blended priority: initial score + vote contribution ─────────────────
    # Maps initial priority string → approximate base score (0-100 scale
    # from priority_service: Critical≥50, High≥35, Medium≥20, Low<20)
    _INITIAL_BASE_SCORES = {"Low": 12, "Medium": 27, "High": 42, "Critical": 60}

    @staticmethod
    def _vote_contribution(upvotes: int, downvotes: int, reach: int) -> float:
        """
        Calculate vote contribution to priority score, dampened by reach.

        Formula:
            net_ratio = net_votes / reach        → what fraction supports it
            engagement = total_votes / reach     → what fraction interacted
            contribution = net_ratio * 100 * min(engagement + 0.5, 2.0)
            Capped to ±30 points.

        For a department of 180 students:
            1 upvote   → ~0.3 points  (negligible)
            10 upvotes → ~3.1 points  (noticeable)
            30 upvotes → ~11  points  (moves priority 1 tier)
            50 upvotes → ~20  points  (significant, capped)
        """
        net = upvotes - downvotes
        total = upvotes + downvotes
        if reach <= 0 or total == 0:
            return 0.0
        net_ratio = net / reach
        engagement = total / reach
        contribution = net_ratio * 100 * min(engagement + 0.5, 2.0)
        return max(-30.0, min(30.0, contribution))

    @staticmethod
    def _engagement_bonus(upvotes: int, downvotes: int, reach: int) -> float:
        """
        Engagement bonus: high participation = more credible signal.
        Max +10 points. Only applies when engagement > 5% of reach.
        """
        total = upvotes + downvotes
        if reach <= 0 or total == 0:
            return 0.0
        engagement_ratio = total / reach
        if engagement_ratio < 0.05:
            return 0.0
        return min(10.0, engagement_ratio * 50.0)

    def _blended_priority(
        self, upvotes: int, downvotes: int, reach: int, initial_priority: str
    ) -> tuple:
        """
        Blended priority: initial base score + vote contribution + engagement bonus.
        Returns (final_score, proposed_priority).

        The initial priority anchors the score. Votes can shift it by max ±30 + 10 bonus.
        Scale: 0-100. Thresholds: Critical≥50, High≥35, Medium≥20, Low<20.
        """
        base = self._INITIAL_BASE_SCORES.get(initial_priority, 20)
        vote_cont = self._vote_contribution(upvotes, downvotes, reach)
        eng_bonus = self._engagement_bonus(upvotes, downvotes, reach)

        final_score = max(0.0, min(100.0, base + vote_cont + eng_bonus))

        if final_score >= 50:
            priority = "Critical"
        elif final_score >= 35:
            priority = "High"
        elif final_score >= 20:
            priority = "Medium"
        else:
            priority = "Low"

        return final_score, priority

    async def recalculate_priority(self, complaint_id: UUID) -> float:
        """
        Recalculate priority using blended system: initial base + vote contribution.

        The initial priority (set by priority_service at creation) serves as the anchor.
        Votes add/subtract from this base, dampened by reach (total eligible viewers).
        Max vote influence: ±30 points + 10 engagement bonus = ±40.

        Guard: new priority cannot be more than 1 level away from current priority.
        """
        complaint = await self.complaint_repo.get(complaint_id)
        if not complaint:
            logger.warning(f"Cannot recalculate priority — complaint {complaint_id} not found")
            return 0.0

        upvotes = complaint.upvotes or 0
        downvotes = complaint.downvotes or 0
        total_votes = upvotes + downvotes

        if total_votes == 0:
            return complaint.priority_score or 0.0

        # Floor reach at 30 so old complaints (reach=0 before migration) still
        # respond to votes. 30 is conservative — actual reach is always higher.
        reach = max(complaint.reach or 0, 30)

        # Always anchor from initial_priority (LLM assessment at creation time),
        # not current priority. This prevents vote drift: Low complaints cannot
        # ratchet to Critical through accumulated votes — they are always scored
        # relative to the original LLM baseline.
        old_priority = complaint.priority
        anchor_priority = complaint.initial_priority or old_priority
        blended_score, proposed_priority = self._blended_priority(
            upvotes, downvotes, reach, anchor_priority
        )

        # Guard: never change by more than 1 level per vote update
        current_idx = self._priority_index(old_priority)
        proposed_idx = self._priority_index(proposed_priority)
        guarded_idx = max(current_idx - 1, min(current_idx + 1, proposed_idx))
        guarded_priority = self._PRIORITY_ORDER[guarded_idx]

        # Persist priority_score (commits → expires session objects)
        await self.complaint_repo.update_priority_score(complaint_id, blended_score)

        # Update priority level only if it changed
        if guarded_priority != old_priority:
            fresh = await self.complaint_repo.get(complaint_id)
            if fresh:
                fresh.priority = guarded_priority
                await self.db.commit()
                logger.info(
                    f"Priority updated for {complaint_id}: {old_priority} → {guarded_priority}"
                )

                # Notify admin when votes promote to High or Critical
                if guarded_priority in ("High", "Critical") and old_priority not in ("High", "Critical"):
                    try:
                        from src.services.notification_service import notification_service
                        from src.repositories.authority_repo import AuthorityRepository
                        authority_repo = AuthorityRepository(self.db)
                        admins = await authority_repo.get_by_type("Admin")
                        preview = (fresh.rephrased_text or fresh.original_text or "")[:100]
                        for admin in admins:
                            await notification_service.create_notification(
                                self.db,
                                recipient_type="Authority",
                                recipient_id=str(admin.id),
                                complaint_id=complaint_id,
                                notification_type="priority_promoted",
                                message=(
                                    f"Complaint promoted to {guarded_priority} priority via votes "
                                    f"(was {old_priority}): \"{preview}...\""
                                )
                            )
                    except Exception as _ne:
                        logger.warning(f"Failed to notify admin of priority promotion: {_ne}")

        logger.info(
            f"Blended priority for {complaint_id}: up={upvotes} down={downvotes} "
            f"reach={reach} base={self._INITIAL_BASE_SCORES.get(old_priority, 20)} "
            f"vote_cont={self._vote_contribution(upvotes, downvotes, reach):.1f} "
            f"eng_bonus={self._engagement_bonus(upvotes, downvotes, reach):.1f} "
            f"score={blended_score:.1f} → {proposed_priority} "
            f"(was={old_priority} guarded={guarded_priority})"
        )

        return blended_score
    
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
