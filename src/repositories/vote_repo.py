"""
Vote repository with specialized queries.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import Vote
from src.repositories.base import BaseRepository


class VoteRepository(BaseRepository[Vote]):
    """Repository for Vote operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Vote)
    
    async def get_by_complaint_and_student(
        self,
        complaint_id: UUID,
        student_roll_no: str
    ) -> Optional[Vote]:
        """
        Get vote by complaint and student.
        
        Args:
            complaint_id: Complaint UUID
            student_roll_no: Student roll number
        
        Returns:
            Vote or None
        """
        query = select(Vote).where(
            and_(
                Vote.complaint_id == complaint_id,
                Vote.student_roll_no == student_roll_no
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def create_or_update_vote(
        self,
        complaint_id: UUID,
        student_roll_no: str,
        vote_type: str
    ) -> Vote:
        """
        Create new vote or update existing.
        
        Args:
            complaint_id: Complaint UUID
            student_roll_no: Student roll number
            vote_type: Upvote or Downvote
        
        Returns:
            Vote instance
        """
        existing = await self.get_by_complaint_and_student(
            complaint_id, student_roll_no
        )
        
        if existing:
            existing.vote_type = vote_type
            await self.session.commit()
            return existing
        else:
            return await self.create(
                complaint_id=complaint_id,
                student_roll_no=student_roll_no,
                vote_type=vote_type
            )
    
    async def delete_vote(
        self,
        complaint_id: UUID,
        student_roll_no: str
    ) -> bool:
        """
        Delete a vote.
        
        Args:
            complaint_id: Complaint UUID
            student_roll_no: Student roll number
        
        Returns:
            True if deleted
        """
        stmt = delete(Vote).where(
            and_(
                Vote.complaint_id == complaint_id,
                Vote.student_roll_no == student_roll_no
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def get_votes_by_complaint(
        self,
        complaint_id: UUID
    ) -> List[Vote]:
        """
        Get all votes for a complaint.
        
        Args:
            complaint_id: Complaint UUID
        
        Returns:
            List of votes
        """
        query = select(Vote).where(Vote.complaint_id == complaint_id)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_votes_by_student(
        self,
        student_roll_no: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Vote]:
        """
        Get all votes by a student.
        
        Args:
            student_roll_no: Student roll number
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of votes
        """
        query = (
            select(Vote)
            .where(Vote.student_roll_no == student_roll_no)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def count_votes_by_complaint(
        self,
        complaint_id: UUID
    ) -> dict:
        """
        Count upvotes and downvotes for a complaint.
        
        Args:
            complaint_id: Complaint UUID
        
        Returns:
            Dictionary with upvote and downvote counts
        """
        votes = await self.get_votes_by_complaint(complaint_id)
        upvotes = sum(1 for v in votes if v.vote_type == "Upvote")
        downvotes = sum(1 for v in votes if v.vote_type == "Downvote")
        
        return {
            "upvotes": upvotes,
            "downvotes": downvotes,
            "total": len(votes)
        }
    
    async def count_votes_by_student(
        self,
        student_roll_no: str
    ) -> int:
        """Count total votes cast by a student."""
        from sqlalchemy import func
        query = select(Vote).where(Vote.student_roll_no == student_roll_no)
        count_query = select(func.count(Vote.id)).where(
            Vote.student_roll_no == student_roll_no
        )
        result = await self.session.execute(count_query)
        return result.scalar() or 0

    async def has_voted(
        self,
        complaint_id: UUID,
        student_roll_no: str
    ) -> bool:
        """
        Check if student has voted on complaint.
        
        Args:
            complaint_id: Complaint UUID
            student_roll_no: Student roll number
        
        Returns:
            True if voted
        """
        vote = await self.get_by_complaint_and_student(
            complaint_id, student_roll_no
        )
        return vote is not None


__all__ = ["VoteRepository"]
