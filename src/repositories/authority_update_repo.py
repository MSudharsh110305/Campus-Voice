"""
Authority Update/Announcement repository with specialized queries.
Manages authority announcements, notices, alerts, and updates.
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, or_, update, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.database.models import AuthorityUpdate, Authority
from src.repositories.base import BaseRepository


class AuthorityUpdateRepository(BaseRepository[AuthorityUpdate]):
    """Repository for AuthorityUpdate (Announcement) operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, AuthorityUpdate)
    
    # ==================== READ OPERATIONS ====================
    
    async def get_with_authority(self, update_id: int) -> Optional[AuthorityUpdate]:
        """
        Get announcement with authority relationship loaded.
        
        Args:
            update_id: Announcement ID
            
        Returns:
            AuthorityUpdate with authority or None
        """
        query = (
            select(AuthorityUpdate)
            .options(selectinload(AuthorityUpdate.authority))
            .where(AuthorityUpdate.id == update_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_authority(
        self,
        authority_id: int,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False
    ) -> List[AuthorityUpdate]:
        """
        Get announcements by authority.
        
        Args:
            authority_id: Authority ID
            skip: Number to skip
            limit: Maximum results
            active_only: Return only active announcements
            
        Returns:
            List of announcements
        """
        conditions = [AuthorityUpdate.authority_id == authority_id]
        
        if active_only:
            conditions.append(AuthorityUpdate.is_active == True)
            conditions.append(
                or_(
                    AuthorityUpdate.expires_at.is_(None),
                    AuthorityUpdate.expires_at > datetime.now(timezone.utc)
                )
            )
        
        query = (
            select(AuthorityUpdate)
            .where(and_(*conditions))
            .order_by(desc(AuthorityUpdate.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_category(
        self,
        category: str,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True
    ) -> List[AuthorityUpdate]:
        """
        Get announcements by category.
        
        Args:
            category: Announcement category (Announcement, Notice, Alert, etc.)
            skip: Number to skip
            limit: Maximum results
            active_only: Return only active announcements
            
        Returns:
            List of announcements
        """
        conditions = [AuthorityUpdate.category == category]
        
        if active_only:
            conditions.append(AuthorityUpdate.is_active == True)
            conditions.append(
                or_(
                    AuthorityUpdate.expires_at.is_(None),
                    AuthorityUpdate.expires_at > datetime.now(timezone.utc)
                )
            )
        
        query = (
            select(AuthorityUpdate)
            .where(and_(*conditions))
            .order_by(desc(AuthorityUpdate.priority_order), desc(AuthorityUpdate.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_priority(
        self,
        priority: str,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True
    ) -> List[AuthorityUpdate]:
        """
        Get announcements by priority.
        
        Args:
            priority: Priority level (Low, Medium, High, Critical)
            skip: Number to skip
            limit: Maximum results
            active_only: Return only active announcements
            
        Returns:
            List of announcements
        """
        conditions = [AuthorityUpdate.priority == priority]
        
        if active_only:
            conditions.append(AuthorityUpdate.is_active == True)
            conditions.append(
                or_(
                    AuthorityUpdate.expires_at.is_(None),
                    AuthorityUpdate.expires_at > datetime.now(timezone.utc)
                )
            )
        
        query = (
            select(AuthorityUpdate)
            .where(and_(*conditions))
            .order_by(desc(AuthorityUpdate.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_active_announcements(
        self,
        skip: int = 0,
        limit: int = 100,
        visibility: Optional[str] = None
    ) -> List[AuthorityUpdate]:
        """
        Get all active (non-expired) announcements.
        
        Args:
            skip: Number to skip
            limit: Maximum results
            visibility: Optional visibility filter
            
        Returns:
            List of active announcements
        """
        conditions = [
            AuthorityUpdate.is_active == True,
            or_(
                AuthorityUpdate.expires_at.is_(None),
                AuthorityUpdate.expires_at > datetime.now(timezone.utc)
            )
        ]
        
        if visibility:
            conditions.append(AuthorityUpdate.visibility == visibility)
        
        query = (
            select(AuthorityUpdate)
            .where(and_(*conditions))
            .order_by(desc(AuthorityUpdate.priority_order), desc(AuthorityUpdate.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_expired_announcements(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuthorityUpdate]:
        """
        Get expired announcements.
        
        Args:
            skip: Number to skip
            limit: Maximum results
            
        Returns:
            List of expired announcements
        """
        query = (
            select(AuthorityUpdate)
            .where(
                and_(
                    AuthorityUpdate.expires_at.is_not(None),
                    AuthorityUpdate.expires_at <= datetime.now(timezone.utc)
                )
            )
            .order_by(desc(AuthorityUpdate.expires_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_visible_to_student(
        self,
        student_stay_type: str,
        student_department_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuthorityUpdate]:
        """
        Get announcements visible to a student based on visibility rules.
        
        Args:
            student_stay_type: Student's stay type (Hostel/Day Scholar)
            student_department_id: Student's department ID
            skip: Number to skip
            limit: Maximum results
            
        Returns:
            List of visible announcements
        """
        # Build visibility conditions
        visibility_conditions = [
            AuthorityUpdate.visibility == "All Students"
        ]
        
        # Add department-specific visibility
        visibility_conditions.append(
            and_(
                AuthorityUpdate.visibility == "Department Only",
                AuthorityUpdate.authority.has(
                    Authority.department_id == student_department_id
                )
            )
        )
        
        # Add hostel-specific visibility
        if student_stay_type == "Hostel":
            visibility_conditions.append(
                AuthorityUpdate.visibility == "Hostel Only"
            )
        
        # Public announcements
        visibility_conditions.append(
            AuthorityUpdate.visibility == "Public"
        )
        
        query = (
            select(AuthorityUpdate)
            .where(
                and_(
                    AuthorityUpdate.is_active == True,
                    or_(
                        AuthorityUpdate.expires_at.is_(None),
                        AuthorityUpdate.expires_at > datetime.now(timezone.utc)
                    ),
                    or_(*visibility_conditions)
                )
            )
            .order_by(desc(AuthorityUpdate.priority_order), desc(AuthorityUpdate.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_high_priority(
        self,
        limit: int = 50
    ) -> List[AuthorityUpdate]:
        """
        Get high priority (High/Critical) active announcements.
        
        Args:
            limit: Maximum results
            
        Returns:
            List of high priority announcements
        """
        query = (
            select(AuthorityUpdate)
            .where(
                and_(
                    AuthorityUpdate.is_active == True,
                    AuthorityUpdate.priority.in_(["High", "Critical"]),
                    or_(
                        AuthorityUpdate.expires_at.is_(None),
                        AuthorityUpdate.expires_at > datetime.now(timezone.utc)
                    )
                )
            )
            .order_by(desc(AuthorityUpdate.priority_order), desc(AuthorityUpdate.created_at))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def search_announcements(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True
    ) -> List[AuthorityUpdate]:
        """
        Search announcements by title or content.
        
        Args:
            search_term: Search term
            skip: Number to skip
            limit: Maximum results
            active_only: Return only active announcements
            
        Returns:
            List of matching announcements
        """
        search_pattern = f"%{search_term}%"
        
        conditions = [
            or_(
                AuthorityUpdate.title.ilike(search_pattern),
                AuthorityUpdate.content.ilike(search_pattern)
            )
        ]
        
        if active_only:
            conditions.append(AuthorityUpdate.is_active == True)
            conditions.append(
                or_(
                    AuthorityUpdate.expires_at.is_(None),
                    AuthorityUpdate.expires_at > datetime.now(timezone.utc)
                )
            )
        
        query = (
            select(AuthorityUpdate)
            .where(and_(*conditions))
            .order_by(desc(AuthorityUpdate.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    # ==================== UPDATE OPERATIONS ====================
    
    async def increment_views(self, update_id: int) -> bool:
        """
        Increment view count for an announcement.
        
        Args:
            update_id: Announcement ID
            
        Returns:
            True if successful
        """
        announcement = await self.get(update_id)
        if announcement:
            announcement.views_count += 1
            await self.session.commit()
            return True
        return False
    
    async def toggle_active(self, update_id: int, is_active: bool) -> bool:
        """
        Toggle announcement active status.
        
        Args:
            update_id: Announcement ID
            is_active: New active status
            
        Returns:
            True if successful
        """
        announcement = await self.get(update_id)
        if announcement:
            announcement.is_active = is_active
            await self.session.commit()
            return True
        return False
    
    async def expire_old_announcements(self) -> int:
        """
        Mark expired announcements as inactive.
        
        Returns:
            Number of expired announcements
        """
        stmt = (
            update(AuthorityUpdate)
            .where(
                and_(
                    AuthorityUpdate.is_active == True,
                    AuthorityUpdate.expires_at.is_not(None),
                    AuthorityUpdate.expires_at <= datetime.now(timezone.utc)
                )
            )
            .values(is_active=False)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    # ==================== COUNT/STATS OPERATIONS ====================
    
    async def count_by_category(self, active_only: bool = True) -> Dict[str, int]:
        """
        Count announcements by category.
        
        Args:
            active_only: Count only active announcements
            
        Returns:
            Dictionary of category counts
        """
        conditions = []
        if active_only:
            conditions.append(AuthorityUpdate.is_active == True)
            conditions.append(
                or_(
                    AuthorityUpdate.expires_at.is_(None),
                    AuthorityUpdate.expires_at > datetime.now(timezone.utc)
                )
            )
        
        if conditions:
            query = (
                select(AuthorityUpdate.category, func.count(AuthorityUpdate.id))
                .where(and_(*conditions))
                .group_by(AuthorityUpdate.category)
            )
        else:
            query = (
                select(AuthorityUpdate.category, func.count(AuthorityUpdate.id))
                .group_by(AuthorityUpdate.category)
            )
        
        result = await self.session.execute(query)
        return dict(result.all())
    
    async def count_by_priority(self, active_only: bool = True) -> Dict[str, int]:
        """
        Count announcements by priority.
        
        Args:
            active_only: Count only active announcements
            
        Returns:
            Dictionary of priority counts
        """
        conditions = []
        if active_only:
            conditions.append(AuthorityUpdate.is_active == True)
            conditions.append(
                or_(
                    AuthorityUpdate.expires_at.is_(None),
                    AuthorityUpdate.expires_at > datetime.now(timezone.utc)
                )
            )
        
        if conditions:
            query = (
                select(AuthorityUpdate.priority, func.count(AuthorityUpdate.id))
                .where(and_(*conditions))
                .group_by(AuthorityUpdate.priority)
            )
        else:
            query = (
                select(AuthorityUpdate.priority, func.count(AuthorityUpdate.id))
                .group_by(AuthorityUpdate.priority)
            )
        
        result = await self.session.execute(query)
        return dict(result.all())
    
    async def count_by_authority(self, authority_id: int) -> int:
        """
        Count announcements by specific authority.
        
        Args:
            authority_id: Authority ID
            
        Returns:
            Number of announcements
        """
        query = (
            select(func.count())
            .select_from(AuthorityUpdate)
            .where(AuthorityUpdate.authority_id == authority_id)
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def count_active(self) -> int:
        """
        Count active (non-expired) announcements.
        
        Returns:
            Number of active announcements
        """
        query = (
            select(func.count())
            .select_from(AuthorityUpdate)
            .where(
                and_(
                    AuthorityUpdate.is_active == True,
                    or_(
                        AuthorityUpdate.expires_at.is_(None),
                        AuthorityUpdate.expires_at > datetime.now(timezone.utc)
                    )
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def count_expired(self) -> int:
        """
        Count expired announcements.
        
        Returns:
            Number of expired announcements
        """
        query = (
            select(func.count())
            .select_from(AuthorityUpdate)
            .where(
                and_(
                    AuthorityUpdate.expires_at.is_not(None),
                    AuthorityUpdate.expires_at <= datetime.now(timezone.utc)
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def get_stats(self) -> Dict[str, any]:
        """
        Get comprehensive announcement statistics.
        
        Returns:
            Dictionary with stats
        """
        total = await self.count()
        active = await self.count_active()
        expired = await self.count_expired()
        by_category = await self.count_by_category(active_only=True)
        by_priority = await self.count_by_priority(active_only=True)
        
        return {
            "total": total,
            "active": active,
            "expired": expired,
            "by_category": by_category,
            "by_priority": by_priority,
        }


__all__ = ["AuthorityUpdateRepository"]
