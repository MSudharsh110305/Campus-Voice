"""
Authority repository with specialized queries.
"""

from typing import Optional, List
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.database.models import Authority, Department
from src.repositories.base import BaseRepository


class AuthorityRepository(BaseRepository[Authority]):
    """Repository for Authority operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Authority)
    
    async def get_by_email(self, email: str) -> Optional[Authority]:
        """
        Get authority by email.
        
        Args:
            email: Authority email
        
        Returns:
            Authority or None
        """
        query = select(Authority).where(Authority.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_with_department(self, authority_id: int) -> Optional[Authority]:
        """
        Get authority with department relationship loaded.
        
        Args:
            authority_id: Authority ID
        
        Returns:
            Authority with department or None
        """
        query = (
            select(Authority)
            .options(selectinload(Authority.department))
            .where(Authority.id == authority_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_type(
        self,
        authority_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Authority]:
        """
        Get authorities by type.
        
        Args:
            authority_type: Authority type
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of authorities
        """
        query = (
            select(Authority)
            .where(Authority.authority_type == authority_type)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_department(
        self,
        department_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Authority]:
        """
        Get authorities by department.
        
        Args:
            department_id: Department ID
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of authorities
        """
        query = (
            select(Authority)
            .where(Authority.department_id == department_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_level_range(
        self,
        min_level: int,
        max_level: int
    ) -> List[Authority]:
        """
        Get authorities within a level range.
        
        Args:
            min_level: Minimum authority level
            max_level: Maximum authority level
        
        Returns:
            List of authorities
        """
        query = (
            select(Authority)
            .where(
                and_(
                    Authority.authority_level >= min_level,
                    Authority.authority_level <= max_level
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_higher_authority(
        self,
        current_level: int,
        department_id: Optional[int] = None
    ) -> Optional[Authority]:
        """
        Get next higher authority for escalation.
        
        Args:
            current_level: Current authority level
            department_id: Optional department filter
        
        Returns:
            Higher authority or None
        """
        conditions = [Authority.authority_level > current_level]
        if department_id:
            conditions.append(
                or_(
                    Authority.department_id == department_id,
                    Authority.department_id.is_(None)  # Admin/General authorities
                )
            )
        
        query = (
            select(Authority)
            .where(and_(*conditions))
            .order_by(Authority.authority_level.asc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_default_for_category(
        self,
        category_name: str,
        department_id: Optional[int] = None
    ) -> Optional[Authority]:
        """
        Get default authority for a category.

        Args:
            category_name: Category name
            department_id: Optional department ID

        Returns:
            Authority or None
        """
        # Map category to authority type
        authority_type_map = {
            "Men's Hostel": "Men's Hostel Warden",
            "Women's Hostel": "Women's Hostel Warden",
            "General": "Admin Officer",
            "Department": "HOD",
            "Disciplinary Committee": "Disciplinary Committee"
        }

        authority_type = authority_type_map.get(category_name)
        if not authority_type:
            return None

        conditions = [Authority.authority_type == authority_type]

        # For department complaints, match department
        if authority_type == "HOD" and department_id:
            conditions.append(Authority.department_id == department_id)

        query = (
            select(Authority)
            .where(and_(*conditions))
            .order_by(Authority.id.asc())   # deterministic: always pick the first created
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_higher_authority_excluding_same_level(
        self,
        current_level: int,
        current_authority_type: str
    ) -> Optional[Authority]:
        """
        Get next higher authority, bypassing all authorities at the same level.
        Used when complaint is against an authority (e.g., warden complaining about warden).

        Args:
            current_level: Current authority level
            current_authority_type: Current authority type to exclude

        Returns:
            Higher authority or None
        """
        # Find authorities with strictly higher level
        query = (
            select(Authority)
            .where(Authority.authority_level > current_level)
            .order_by(Authority.authority_level.asc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_authorities(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Authority]:
        """
        Get active authorities.
        
        Args:
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of active authorities
        """
        query = (
            select(Authority)
            .where(Authority.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def search_authorities(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Authority]:
        """
        Search authorities by name or email.
        
        Args:
            search_term: Search term
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of matching authorities
        """
        search_pattern = f"%{search_term}%"
        query = (
            select(Authority)
            .where(
                or_(
                    Authority.name.ilike(search_pattern),
                    Authority.email.ilike(search_pattern)
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def count_by_type(self) -> dict:
        """
        Count authorities by type.
        
        Returns:
            Dictionary of type counts
        """
        query = (
            select(Authority.authority_type, func.count(Authority.id))
            .group_by(Authority.authority_type)
        )
        result = await self.session.execute(query)
        return dict(result.all())
    
    async def update_password(self, authority_id: int, password_hash: str) -> bool:
        """
        Update authority password.
        
        Args:
            authority_id: Authority ID
            password_hash: New password hash
        
        Returns:
            True if successful
        """
        authority = await self.get(authority_id)
        if authority:
            authority.password_hash = password_hash
            await self.session.commit()
            return True
        return False


__all__ = ["AuthorityRepository"]
