"""
Comment repository with specialized queries.
Manages comments on complaints from students and authorities.
"""

from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, and_, or_, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.database.models import Comment, Student, Authority, Complaint
from src.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    """Repository for Comment operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Comment)
    
    # ==================== READ OPERATIONS ====================
    
    async def get_with_relations(self, comment_id: int) -> Optional[Comment]:
        """
        Get comment with all relationships loaded.
        
        Args:
            comment_id: Comment ID
            
        Returns:
            Comment with relations or None
        """
        query = (
            select(Comment)
            .options(
                selectinload(Comment.complaint),
                selectinload(Comment.student),
                selectinload(Comment.authority)
            )
            .where(Comment.id == comment_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_complaint(
        self,
        complaint_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Comment]:
        """
        Get all comments for a complaint.
        
        Args:
            complaint_id: Complaint UUID
            skip: Number to skip
            limit: Maximum results
            
        Returns:
            List of comments ordered by creation time
        """
        query = (
            select(Comment)
            .where(Comment.complaint_id == complaint_id)
            .order_by(Comment.created_at.asc())  # Oldest first for conversation flow
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_student(
        self,
        student_roll_no: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Comment]:
        """
        Get all comments by a student.
        
        Args:
            student_roll_no: Student roll number
            skip: Number to skip
            limit: Maximum results
            
        Returns:
            List of comments by student
        """
        query = (
            select(Comment)
            .where(
                and_(
                    Comment.commenter_type == "Student",
                    Comment.student_roll_no == student_roll_no
                )
            )
            .order_by(desc(Comment.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_authority(
        self,
        authority_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Comment]:
        """
        Get all comments by an authority.
        
        Args:
            authority_id: Authority ID
            skip: Number to skip
            limit: Maximum results
            
        Returns:
            List of comments by authority
        """
        query = (
            select(Comment)
            .where(
                and_(
                    Comment.commenter_type == "Authority",
                    Comment.authority_id == authority_id
                )
            )
            .order_by(desc(Comment.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_recent_comments(
        self,
        limit: int = 50,
        complaint_id: Optional[UUID] = None
    ) -> List[Comment]:
        """
        Get recent comments across the system or for a specific complaint.
        
        Args:
            limit: Maximum results
            complaint_id: Optional complaint filter
            
        Returns:
            List of recent comments
        """
        conditions = []
        if complaint_id:
            conditions.append(Comment.complaint_id == complaint_id)
        
        if conditions:
            query = (
                select(Comment)
                .where(and_(*conditions))
                .order_by(desc(Comment.created_at))
                .limit(limit)
            )
        else:
            query = (
                select(Comment)
                .order_by(desc(Comment.created_at))
                .limit(limit)
            )
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_comments_with_user_info(
        self,
        complaint_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Comment]:
        """
        Get comments with student/authority info eagerly loaded.
        
        Args:
            complaint_id: Complaint UUID
            skip: Number to skip
            limit: Maximum results
            
        Returns:
            List of comments with user information
        """
        query = (
            select(Comment)
            .options(
                selectinload(Comment.student),
                selectinload(Comment.authority)
            )
            .where(Comment.complaint_id == complaint_id)
            .order_by(Comment.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def search_comments(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
        complaint_id: Optional[UUID] = None
    ) -> List[Comment]:
        """
        Search comments by content.
        
        Args:
            search_term: Search term
            skip: Number to skip
            limit: Maximum results
            complaint_id: Optional complaint filter
            
        Returns:
            List of matching comments
        """
        search_pattern = f"%{search_term}%"
        
        conditions = [Comment.content.ilike(search_pattern)]
        
        if complaint_id:
            conditions.append(Comment.complaint_id == complaint_id)
        
        query = (
            select(Comment)
            .where(and_(*conditions))
            .order_by(desc(Comment.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    # ==================== COUNT OPERATIONS ====================
    
    async def count_by_complaint(self, complaint_id: UUID) -> int:
        """
        Count comments for a complaint.
        
        Args:
            complaint_id: Complaint UUID
            
        Returns:
            Number of comments
        """
        query = (
            select(func.count())
            .select_from(Comment)
            .where(Comment.complaint_id == complaint_id)
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def count_by_student(self, student_roll_no: str) -> int:
        """
        Count comments by a student.
        
        Args:
            student_roll_no: Student roll number
            
        Returns:
            Number of comments
        """
        query = (
            select(func.count())
            .select_from(Comment)
            .where(
                and_(
                    Comment.commenter_type == "Student",
                    Comment.student_roll_no == student_roll_no
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def count_by_authority(self, authority_id: int) -> int:
        """
        Count comments by an authority.
        
        Args:
            authority_id: Authority ID
            
        Returns:
            Number of comments
        """
        query = (
            select(func.count())
            .select_from(Comment)
            .where(
                and_(
                    Comment.commenter_type == "Authority",
                    Comment.authority_id == authority_id
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def count_recent_comments(
        self,
        hours: int = 24,
        complaint_id: Optional[UUID] = None
    ) -> int:
        """
        Count comments in the last N hours.
        
        Args:
            hours: Number of hours to look back
            complaint_id: Optional complaint filter
            
        Returns:
            Number of recent comments
        """
        threshold = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        conditions = [Comment.created_at >= threshold]
        
        if complaint_id:
            conditions.append(Comment.complaint_id == complaint_id)
        
        query = (
            select(func.count())
            .select_from(Comment)
            .where(and_(*conditions))
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    # ==================== DELETE OPERATIONS ====================
    
    async def delete_by_complaint(self, complaint_id: UUID) -> int:
        """
        Delete all comments for a complaint (cascade cleanup).
        
        Args:
            complaint_id: Complaint UUID
            
        Returns:
            Number of deleted comments
        """
        stmt = delete(Comment).where(Comment.complaint_id == complaint_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    async def delete_by_student(self, student_roll_no: str) -> int:
        """
        Delete all comments by a student (user cleanup).
        
        Args:
            student_roll_no: Student roll number
            
        Returns:
            Number of deleted comments
        """
        stmt = delete(Comment).where(
            and_(
                Comment.commenter_type == "Student",
                Comment.student_roll_no == student_roll_no
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    async def delete_by_authority(self, authority_id: int) -> int:
        """
        Delete all comments by an authority (user cleanup).
        
        Args:
            authority_id: Authority ID
            
        Returns:
            Number of deleted comments
        """
        stmt = delete(Comment).where(
            and_(
                Comment.commenter_type == "Authority",
                Comment.authority_id == authority_id
            )
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    async def delete_old_comments(
        self,
        days: int = 365
    ) -> int:
        """
        Delete comments older than specified days (cleanup).
        
        Args:
            days: Number of days
            
        Returns:
            Number of deleted comments
        """
        threshold = datetime.now(timezone.utc) - timedelta(days=days)
        
        stmt = delete(Comment).where(Comment.created_at < threshold)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    # ==================== UTILITY OPERATIONS ====================
    
    async def get_comment_stats(
        self,
        complaint_id: Optional[UUID] = None
    ) -> Dict[str, any]:
        """
        Get comment statistics.
        
        Args:
            complaint_id: Optional complaint filter for specific stats
            
        Returns:
            Dictionary with stats
        """
        if complaint_id:
            total = await self.count_by_complaint(complaint_id)
            recent_24h = await self.count_recent_comments(24, complaint_id)
            
            # Count by commenter type for this complaint
            query_students = (
                select(func.count())
                .select_from(Comment)
                .where(
                    and_(
                        Comment.complaint_id == complaint_id,
                        Comment.commenter_type == "Student"
                    )
                )
            )
            result_students = await self.session.execute(query_students)
            student_comments = result_students.scalar() or 0
            
            query_authorities = (
                select(func.count())
                .select_from(Comment)
                .where(
                    and_(
                        Comment.complaint_id == complaint_id,
                        Comment.commenter_type == "Authority"
                    )
                )
            )
            result_authorities = await self.session.execute(query_authorities)
            authority_comments = result_authorities.scalar() or 0
            
            return {
                "total": total,
                "recent_24h": recent_24h,
                "by_students": student_comments,
                "by_authorities": authority_comments,
            }
        else:
            # Overall system stats
            total = await self.count()
            recent_24h = await self.count_recent_comments(24)
            
            # Count by commenter type
            query_students = (
                select(func.count())
                .select_from(Comment)
                .where(Comment.commenter_type == "Student")
            )
            result_students = await self.session.execute(query_students)
            student_comments = result_students.scalar() or 0
            
            query_authorities = (
                select(func.count())
                .select_from(Comment)
                .where(Comment.commenter_type == "Authority")
            )
            result_authorities = await self.session.execute(query_authorities)
            authority_comments = result_authorities.scalar() or 0
            
            return {
                "total": total,
                "recent_24h": recent_24h,
                "by_students": student_comments,
                "by_authorities": authority_comments,
            }
    
    async def get_top_commenters(
        self,
        limit: int = 10,
        commenter_type: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        Get users with most comments.
        
        Args:
            limit: Maximum results
            commenter_type: Optional filter (Student/Authority)
            
        Returns:
            List of top commenters with counts
        """
        if commenter_type == "Student":
            query = (
                select(Comment.student_roll_no, func.count(Comment.id).label("count"))
                .where(Comment.commenter_type == "Student")
                .group_by(Comment.student_roll_no)
                .order_by(desc("count"))
                .limit(limit)
            )
        elif commenter_type == "Authority":
            query = (
                select(Comment.authority_id, func.count(Comment.id).label("count"))
                .where(Comment.commenter_type == "Authority")
                .group_by(Comment.authority_id)
                .order_by(desc("count"))
                .limit(limit)
            )
        else:
            # Return both types
            query_students = (
                select(Comment.student_roll_no.label("user_id"), func.count(Comment.id).label("count"))
                .where(Comment.commenter_type == "Student")
                .group_by(Comment.student_roll_no)
                .order_by(desc("count"))
                .limit(limit)
            )
            result = await self.session.execute(query_students)
            return [{"user_id": row[0], "count": row[1], "type": "Student"} for row in result.all()]
        
        result = await self.session.execute(query)
        return [{"user_id": row[0], "count": row[1]} for row in result.all()]
    
    async def has_commented(
        self,
        complaint_id: UUID,
        user_type: str,
        user_id: str
    ) -> bool:
        """
        Check if a user has commented on a complaint.
        
        Args:
            complaint_id: Complaint UUID
            user_type: Student or Authority
            user_id: Roll number or authority ID
            
        Returns:
            True if user has commented
        """
        if user_type == "Student":
            conditions = [
                Comment.complaint_id == complaint_id,
                Comment.commenter_type == "Student",
                Comment.student_roll_no == user_id
            ]
        else:
            conditions = [
                Comment.complaint_id == complaint_id,
                Comment.commenter_type == "Authority",
                Comment.authority_id == int(user_id)
            ]
        
        query = select(Comment).where(and_(*conditions)).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None


__all__ = ["CommentRepository"]
