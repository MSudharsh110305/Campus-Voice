"""
Spam detection service.
"""

import logging
from typing import Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.complaint_repo import ComplaintRepository
from src.config.constants import SPAM_KEYWORDS, MIN_COMPLAINT_LENGTH

logger = logging.getLogger(__name__)


class SpamDetectionService:
    """Service for spam detection"""
    
    async def check_spam_blacklist(
        self,
        db: AsyncSession,
        student_roll_no: str
    ) -> Dict[str, Any]:
        """
        Check if student is on spam blacklist.
        
        Args:
            db: Database session
            student_roll_no: Student roll number
        
        Returns:
            Dictionary with is_blacklisted status
        """
        from src.database.models import SpamBlacklist
        from sqlalchemy import select
        
        query = select(SpamBlacklist).where(
            SpamBlacklist.student_roll_no == student_roll_no
        )
        result = await db.execute(query)
        blacklist = result.scalar_one_or_none()
        
        if not blacklist:
            return {"is_blacklisted": False}
        
        # Check if temporary ban expired
        if not blacklist.is_permanent and blacklist.expires_at:
            # ✅ FIXED: Use timezone-aware datetime
            if datetime.now(timezone.utc) > blacklist.expires_at:
                # Ban expired, remove from blacklist
                await db.delete(blacklist)
                await db.commit()
                logger.info(f"Temporary ban expired for {student_roll_no}, removed from blacklist")
                return {"is_blacklisted": False}
        
        logger.warning(f"Student {student_roll_no} is blacklisted: {blacklist.reason}")
        return {
            "is_blacklisted": True,
            "reason": blacklist.reason,
            "is_permanent": blacklist.is_permanent,
            "expires_at": blacklist.expires_at.isoformat() if blacklist.expires_at else None
        }
    
    @staticmethod
    def _levenshtein(s: str, t: str) -> int:
        """Compute Levenshtein edit distance (DP, O(n) space)."""
        m, n = len(s), len(t)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[:]
            dp[0] = i
            for j in range(1, n + 1):
                if s[i - 1] == t[j - 1]:
                    dp[j] = prev[j - 1]
                else:
                    dp[j] = 1 + min(prev[j], dp[j - 1], prev[j - 1])
        return dp[n]

    def contains_spam_keywords(self, text: str) -> bool:
        """
        Check if text contains spam keywords using Levenshtein fuzzy matching.

        Strategy:
        - Short keywords (≤ 3 chars) or phrase keywords (contains space):
          exact substring match (too short / too specific for fuzzy).
        - Single-word keywords (> 3 chars): fuzzy match against every word
          in the text, allowing up to 2 edits for keywords ≥ 6 chars,
          1 edit for keywords 4–5 chars.

        Args:
            text: Text to check

        Returns:
            True if text contains a spam keyword (exact or fuzzy)
        """
        text_lower = text.lower()
        words = text_lower.split()

        for keyword in SPAM_KEYWORDS:
            klen = len(keyword)

            # Short or multi-word keywords: exact substring match only
            if klen <= 3 or ' ' in keyword:
                if keyword in text_lower:
                    logger.warning(f"Spam keyword (exact): '{keyword}'")
                    return True
                continue

            # Determine allowed edit distance by keyword length
            max_dist = 2 if klen >= 6 else 1

            for word in words:
                # Skip words that are too different in length to ever match
                if abs(len(word) - klen) > max_dist:
                    continue
                if self._levenshtein(word, keyword) <= max_dist:
                    logger.warning(f"Spam keyword (fuzzy): '{keyword}' ≈ '{word}'")
                    return True

        return False
    
    async def get_spam_count(
        self,
        db: AsyncSession,
        student_roll_no: str
    ) -> int:
        """
        Get count of spam complaints by student.
        
        Args:
            db: Database session
            student_roll_no: Student roll number
        
        Returns:
            Count of spam complaints
        """
        from src.database.models import Complaint
        from sqlalchemy import select, func
        
        query = select(func.count()).where(
            Complaint.student_roll_no == student_roll_no,
            Complaint.is_marked_as_spam == True
        )
        result = await db.execute(query)
        count = result.scalar_one()
        
        return count
    
    async def add_to_blacklist(
        self,
        db: AsyncSession,
        student_roll_no: str,
        reason: str,
        is_permanent: bool = False,
        ban_duration_days: int = 7
    ) -> Dict[str, Any]:
        """
        Add student to spam blacklist.
        
        Args:
            db: Database session
            student_roll_no: Student roll number
            reason: Reason for blacklisting
            is_permanent: Whether ban is permanent
            ban_duration_days: Duration in days (if temporary)
        
        Returns:
            Blacklist entry details
        """
        from src.database.models import SpamBlacklist
        from datetime import timedelta
        from sqlalchemy import select
        
        # Check if already blacklisted
        query = select(SpamBlacklist).where(
            SpamBlacklist.student_roll_no == student_roll_no
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing blacklist entry
            existing.reason = reason
            existing.is_permanent = is_permanent
            if not is_permanent:
                existing.expires_at = datetime.now(timezone.utc) + timedelta(days=ban_duration_days)
            else:
                existing.expires_at = None
            
            logger.info(f"Updated blacklist for {student_roll_no}")
        else:
            # Create new blacklist entry
            expires_at = None
            if not is_permanent:
                expires_at = datetime.now(timezone.utc) + timedelta(days=ban_duration_days)
            
            blacklist = SpamBlacklist(
                student_roll_no=student_roll_no,
                reason=reason,
                is_permanent=is_permanent,
                expires_at=expires_at
            )
            db.add(blacklist)
            logger.warning(f"Added {student_roll_no} to blacklist: {reason}")
        
        await db.commit()
        
        return {
            "student_roll_no": student_roll_no,
            "is_blacklisted": True,
            "reason": reason,
            "is_permanent": is_permanent,
            "expires_at": expires_at.isoformat() if expires_at else None
        }
    
    async def remove_from_blacklist(
        self,
        db: AsyncSession,
        student_roll_no: str
    ) -> bool:
        """
        Remove student from blacklist.
        
        Args:
            db: Database session
            student_roll_no: Student roll number
        
        Returns:
            True if removed successfully
        """
        from src.database.models import SpamBlacklist
        from sqlalchemy import select
        
        query = select(SpamBlacklist).where(
            SpamBlacklist.student_roll_no == student_roll_no
        )
        result = await db.execute(query)
        blacklist = result.scalar_one_or_none()
        
        if blacklist:
            await db.delete(blacklist)
            await db.commit()
            logger.info(f"Removed {student_roll_no} from blacklist")
            return True
        
        return False


# Create global instance
spam_detection_service = SpamDetectionService()

__all__ = ["SpamDetectionService", "spam_detection_service"]
