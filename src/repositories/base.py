"""
Base repository with generic CRUD operations.
All specific repositories inherit from this.
"""

from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from src.database.models import Base

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Base repository providing generic CRUD operations.
    
    Usage:
        student_repo = BaseRepository(session, Student)
        student = await student_repo.get(roll_no="21CSE001")
    """
    
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        """
        Initialize repository.
        
        Args:
            session: Async database session
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model
    
    # ==================== CREATE ====================
    
    async def create(self, **kwargs) -> ModelType:
        """
        Create a new record.
        
        Args:
            **kwargs: Field values for the new record
        
        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance
    
    async def create_many(self, instances: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records.
        
        Args:
            instances: List of dictionaries with field values
        
        Returns:
            List of created model instances
        """
        objects = [self.model(**data) for data in instances]
        self.session.add_all(objects)
        await self.session.commit()
        for obj in objects:
            await self.session.refresh(obj)
        return objects
    
    # ==================== READ ====================
    
    async def get(self, id: Any) -> Optional[ModelType]:
        """
        Get record by primary key.
        
        Args:
            id: Primary key value
        
        Returns:
            Model instance or None
        """
        return await self.session.get(self.model, id)
    
    async def get_by(self, **filters) -> Optional[ModelType]:
        """
        Get single record by filters.
        
        Args:
            **filters: Field=value filters
        
        Returns:
            Model instance or None
        """
        query = select(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        """
        Get multiple records with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Field=value filters
        
        Returns:
            List of model instances
        """
        query = select(self.model).filter_by(**filters).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_all(self, **filters) -> List[ModelType]:
        """
        Get all records matching filters.
        
        Args:
            **filters: Field=value filters
        
        Returns:
            List of all matching model instances
        """
        query = select(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def exists(self, **filters) -> bool:
        """
        Check if record exists.
        
        Args:
            **filters: Field=value filters
        
        Returns:
            True if exists, False otherwise
        """
        query = select(self.model).filter_by(**filters).limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    # ==================== UPDATE ====================
    
    async def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """
        Update record by primary key.
        
        Args:
            id: Primary key value
            **kwargs: Fields to update
        
        Returns:
            Updated model instance or None
        """
        instance = await self.get(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            await self.session.commit()
            await self.session.refresh(instance)
        return instance
    
    async def update_many(self, filters: Dict[str, Any], values: Dict[str, Any]) -> int:
        """
        Update multiple records matching filters.
        
        Args:
            filters: Filter conditions
            values: Values to update
        
        Returns:
            Number of updated records
        """
        stmt = update(self.model).filter_by(**filters).values(**values)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    # ==================== DELETE ====================
    
    async def delete(self, id: Any) -> bool:
        """
        Delete record by primary key.
        
        Args:
            id: Primary key value
        
        Returns:
            True if deleted, False if not found
        """
        instance = await self.get(id)
        if instance:
            await self.session.delete(instance)
            await self.session.commit()
            return True
        return False
    
    async def delete_many(self, **filters) -> int:
        """
        Delete multiple records matching filters.
        
        Args:
            **filters: Filter conditions
        
        Returns:
            Number of deleted records
        """
        stmt = delete(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    # ==================== COUNT ====================
    
    async def count(self, **filters) -> int:
        """
        Count records matching filters.
        
        Args:
            **filters: Filter conditions
        
        Returns:
            Number of matching records
        """
        query = select(func.count()).select_from(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    # ==================== UTILITY ====================
    
    async def refresh(self, instance: ModelType) -> ModelType:
        """
        Refresh instance from database.
        
        Args:
            instance: Model instance to refresh
        
        Returns:
            Refreshed instance
        """
        await self.session.refresh(instance)
        return instance
    
    async def commit(self):
        """Commit current transaction"""
        await self.session.commit()
    
    async def rollback(self):
        """Rollback current transaction"""
        await self.session.rollback()
    
    async def flush(self):
        """Flush pending changes"""
        await self.session.flush()


__all__ = ["BaseRepository"]
