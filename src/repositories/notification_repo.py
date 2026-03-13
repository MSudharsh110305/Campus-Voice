"""
Notification repository with specialized queries.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import Notification
from src.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """Repository for Notification operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Notification)
    
    async def get_by_recipient(
        self,
        recipient_type: str,
        recipient_id: str,
        skip: int = 0,
        limit: int = 100,
        unread_only: bool = False
    ) -> List[Notification]:
        """
        Get notifications for a recipient.
        
        Args:
            recipient_type: Student or Authority
            recipient_id: Recipient ID
            skip: Number to skip
            limit: Maximum results
            unread_only: Return only unread notifications
        
        Returns:
            List of notifications
        """
        conditions = [
            Notification.recipient_type == recipient_type,
            Notification.recipient_id == recipient_id
        ]
        
        if unread_only:
            conditions.append(Notification.is_read == False)
        
        query = (
            select(Notification)
            .where(and_(*conditions))
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def count_unread(
        self,
        recipient_type: str,
        recipient_id: str
    ) -> int:
        """
        Count unread notifications for a recipient.
        
        Args:
            recipient_type: Student or Authority
            recipient_id: Recipient ID
        
        Returns:
            Number of unread notifications
        """
        return await self.count(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            is_read=False
        )
    
    async def mark_as_read(
        self,
        notification_id: int
    ) -> bool:
        """
        Mark notification as read.
        
        Args:
            notification_id: Notification ID
        
        Returns:
            True if successful
        """
        notification = await self.get(notification_id)
        if notification:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await self.session.commit()
            return True
        return False
    
    async def mark_many_as_read(
        self,
        notification_ids: List[int]
    ) -> int:
        """
        Mark multiple notifications as read.
        
        Args:
            notification_ids: List of notification IDs
        
        Returns:
            Number of updated notifications
        """
        stmt = (
            update(Notification)
            .where(Notification.id.in_(notification_ids))
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    async def mark_all_as_read(
        self,
        recipient_type: str,
        recipient_id: str
    ) -> int:
        """
        Mark all notifications as read for a recipient.
        
        Args:
            recipient_type: Student or Authority
            recipient_id: Recipient ID
        
        Returns:
            Number of updated notifications
        """
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.recipient_type == recipient_type,
                    Notification.recipient_id == recipient_id,
                    Notification.is_read == False
                )
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    async def count_by_recipient(
        self,
        recipient_type: str,
        recipient_id: str,
        unread_only: bool = False
    ) -> int:
        """
        Count notifications for a recipient.
        """
        conditions = [
            Notification.recipient_type == recipient_type,
            Notification.recipient_id == recipient_id
        ]
        if unread_only:
            conditions.append(Notification.is_read == False)

        query = select(func.count(Notification.id)).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def delete_old_notifications(
        self,
        days: int = 30
    ) -> int:
        """
        Delete notifications older than specified days.
        
        Args:
            days: Number of days
        
        Returns:
            Number of deleted notifications
        """
        threshold = datetime.now(timezone.utc) - timedelta(days=days)
        
        stmt = delete(Notification).where(
            Notification.created_at < threshold
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount
    
    async def get_by_complaint(
        self,
        complaint_id: UUID
    ) -> List[Notification]:
        """
        Get notifications for a complaint.
        
        Args:
            complaint_id: Complaint UUID
        
        Returns:
            List of notifications
        """
        query = (
            select(Notification)
            .where(Notification.complaint_id == complaint_id)
            .order_by(Notification.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_type(
        self,
        recipient_type: str,
        recipient_id: str,
        notification_type: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Notification]:
        """
        Get notifications by type.
        
        Args:
            recipient_type: Student or Authority
            recipient_id: Recipient ID
            notification_type: Notification type
            skip: Number to skip
            limit: Maximum results
        
        Returns:
            List of notifications
        """
        query = (
            select(Notification)
            .where(
                and_(
                    Notification.recipient_type == recipient_type,
                    Notification.recipient_id == recipient_id,
                    Notification.notification_type == notification_type
                )
            )
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()


__all__ = ["NotificationRepository"]
