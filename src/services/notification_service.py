"""
Notification service for creating and sending notifications.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Notification
from src.repositories.notification_repo import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for notification operations"""
    
    # Notification type templates
    NOTIFICATION_TEMPLATES = {
        "complaint_assigned": "New complaint assigned: {title}",
        "complaint_escalated": "Complaint escalated to you: {title}",
        "status_update": "Complaint status updated to '{status}': {title}",
        "new_comment": "New comment on your complaint: {comment}",
        "complaint_resolved": "Your complaint has been resolved: {title}",
        "authority_update": "New announcement: {title}",
        "vote_milestone": "Your complaint reached {count} upvotes!",
        "escalation_warning": "Complaint pending for {days} days - automatic escalation soon",
    }
    
    async def create_notification(
        self,
        db: AsyncSession,
        recipient_type: str,
        recipient_id: str,
        complaint_id: Optional[UUID],
        notification_type: str,
        message: str,
        title: Optional[str] = None,
        action_url: Optional[str] = None
    ) -> Notification:
        """
        Create a new notification.
        
        Args:
            db: Database session
            recipient_type: Student or Authority
            recipient_id: Recipient ID
            complaint_id: Optional complaint ID
            notification_type: Notification type
            message: Notification message
            title: Optional notification title
            action_url: Optional action URL
        
        Returns:
            Created notification
        """
        # Validate recipient type
        if recipient_type not in ["Student", "Authority"]:
            raise ValueError("Invalid recipient type. Must be 'Student' or 'Authority'")
        
        notification_repo = NotificationRepository(db)
        
        try:
            notification = await notification_repo.create(
                recipient_type=recipient_type,
                recipient_id=recipient_id,
                complaint_id=complaint_id,
                notification_type=notification_type,
                message=message
            )
            
            logger.info(
                f"Notification created: {notification_type} for {recipient_type}:{recipient_id} "
                f"(ID: {notification.id})"
            )
            
            # TODO: Send real-time notification via WebSocket
            await self._send_realtime_notification(notification)

            # Send Web Push notification (best-effort, non-blocking)
            await self._send_push_notification(db, notification)

            return notification
            
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            raise
    
    async def create_bulk_notifications(
        self,
        db: AsyncSession,
        recipients: List[Dict[str, str]],
        complaint_id: Optional[UUID],
        notification_type: str,
        message: str
    ) -> List[Notification]:
        """
        Create notifications for multiple recipients.
        
        Args:
            db: Database session
            recipients: List of dicts with recipient_type and recipient_id
            complaint_id: Optional complaint ID
            notification_type: Notification type
            message: Notification message
        
        Returns:
            List of created notifications
        """
        notifications = []
        
        for recipient in recipients:
            try:
                notification = await self.create_notification(
                    db=db,
                    recipient_type=recipient["recipient_type"],
                    recipient_id=recipient["recipient_id"],
                    complaint_id=complaint_id,
                    notification_type=notification_type,
                    message=message
                )
                notifications.append(notification)
            except Exception as e:
                logger.error(
                    f"Failed to create notification for {recipient['recipient_type']}:"
                    f"{recipient['recipient_id']} - {e}"
                )
                continue
        
        logger.info(f"Created {len(notifications)} bulk notifications")
        return notifications
    
    async def get_notifications(
        self,
        db: AsyncSession,
        recipient_type: str,
        recipient_id: str,
        skip: int = 0,
        limit: int = 20,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get notifications for a recipient.
        
        Args:
            db: Database session
            recipient_type: Student or Authority
            recipient_id: Recipient ID
            skip: Number to skip
            limit: Maximum results
            unread_only: Only return unread notifications
        
        Returns:
            List of notifications
        """
        notification_repo = NotificationRepository(db)
        
        notifications = await notification_repo.get_by_recipient(
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            skip=skip,
            limit=limit
        )
        
        # Filter unread if requested
        if unread_only:
            notifications = [n for n in notifications if not n.is_read]
        
        result = []
        for notification in notifications:
            result.append({
                "id": notification.id,
                "type": notification.notification_type,
                "message": notification.message,
                "is_read": notification.is_read,
                "complaint_id": str(notification.complaint_id) if notification.complaint_id else None,
                "created_at": notification.created_at.isoformat(),
                "read_at": notification.read_at.isoformat() if notification.read_at else None
            })
        
        return result
    
    async def get_notifications_by_type(
        self,
        db: AsyncSession,
        recipient_type: str,
        recipient_id: str,
        notification_type: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get notifications of a specific type.
        
        Args:
            db: Database session
            recipient_type: Student or Authority
            recipient_id: Recipient ID
            notification_type: Notification type filter
            limit: Maximum results
        
        Returns:
            List of notifications
        """
        notification_repo = NotificationRepository(db)
        
        notifications = await notification_repo.get_by_type(
            notification_type=notification_type
        )
        
        # Filter by recipient
        filtered = [
            n for n in notifications
            if n.recipient_type == recipient_type and n.recipient_id == recipient_id
        ][:limit]
        
        result = []
        for notification in filtered:
            result.append({
                "id": notification.id,
                "type": notification.notification_type,
                "message": notification.message,
                "is_read": notification.is_read,
                "complaint_id": str(notification.complaint_id) if notification.complaint_id else None,
                "created_at": notification.created_at.isoformat()
            })
        
        return result
    
    async def mark_as_read(
        self,
        db: AsyncSession,
        notification_id: int
    ) -> bool:
        """
        Mark notification as read.
        
        Args:
            db: Database session
            notification_id: Notification ID
        
        Returns:
            True if successful
        """
        notification_repo = NotificationRepository(db)
        
        success = await notification_repo.mark_as_read(notification_id)
        
        if success:
            logger.debug(f"Notification {notification_id} marked as read")
        else:
            logger.warning(f"Failed to mark notification {notification_id} as read")
        
        return success
    
    async def mark_many_as_read(
        self,
        db: AsyncSession,
        notification_ids: List[int]
    ) -> int:
        """
        Mark multiple notifications as read.
        
        Args:
            db: Database session
            notification_ids: List of notification IDs
        
        Returns:
            Number of notifications marked as read
        """
        notification_repo = NotificationRepository(db)
        
        count = await notification_repo.mark_many_as_read(notification_ids)
        
        logger.info(f"Marked {count} notifications as read")
        return count
    
    async def mark_all_as_read(
        self,
        db: AsyncSession,
        recipient_type: str,
        recipient_id: str
    ) -> int:
        """
        Mark all notifications as read for a recipient.
        
        Args:
            db: Database session
            recipient_type: Student or Authority
            recipient_id: Recipient ID
        
        Returns:
            Number of notifications marked as read
        """
        notification_repo = NotificationRepository(db)
        
        count = await notification_repo.mark_all_as_read(recipient_type, recipient_id)
        
        logger.info(f"Marked all notifications as read for {recipient_type}:{recipient_id} ({count} total)")
        return count
    
    async def get_unread_count(
        self,
        db: AsyncSession,
        recipient_type: str,
        recipient_id: str
    ) -> int:
        """
        Get unread notification count.
        
        Args:
            db: Database session
            recipient_type: Student or Authority
            recipient_id: Recipient ID
        
        Returns:
            Unread count
        """
        notification_repo = NotificationRepository(db)
        count = await notification_repo.count_unread(recipient_type, recipient_id)
        
        logger.debug(f"Unread count for {recipient_type}:{recipient_id} = {count}")
        return count
    
    async def delete_notification(
        self,
        db: AsyncSession,
        notification_id: int,
        recipient_id: str
    ) -> bool:
        """
        Delete a notification (soft delete or permission check).
        
        Args:
            db: Database session
            notification_id: Notification ID
            recipient_id: Recipient ID (for permission check)
        
        Returns:
            True if successful
        """
        notification_repo = NotificationRepository(db)
        
        # Get notification to verify ownership
        notification = await notification_repo.get(notification_id)
        
        if not notification:
            logger.warning(f"Notification {notification_id} not found")
            return False
        
        if notification.recipient_id != recipient_id:
            logger.warning(
                f"Permission denied: User {recipient_id} cannot delete "
                f"notification {notification_id}"
            )
            return False
        
        # Delete notification
        await notification_repo.delete(notification_id)
        logger.info(f"Notification {notification_id} deleted")
        
        return True
    
    async def delete_old_notifications(
        self,
        db: AsyncSession,
        days: int = 30
    ) -> int:
        """
        Delete old read notifications (cleanup task).
        Run as scheduled job.
        
        Args:
            db: Database session
            days: Delete notifications older than this many days
        
        Returns:
            Number of notifications deleted
        """
        notification_repo = NotificationRepository(db)
        
        count = await notification_repo.delete_old_notifications(days)
        
        logger.info(f"Deleted {count} old notifications (older than {days} days)")
        return count
    
    async def get_notification_statistics(
        self,
        db: AsyncSession,
        recipient_type: str,
        recipient_id: str
    ) -> Dict[str, Any]:
        """
        Get notification statistics for a recipient.
        
        Args:
            db: Database session
            recipient_type: Student or Authority
            recipient_id: Recipient ID
        
        Returns:
            Statistics dictionary
        """
        notification_repo = NotificationRepository(db)
        
        all_notifications = await notification_repo.get_by_recipient(
            recipient_type, recipient_id
        )
        
        total = len(all_notifications)
        unread = sum(1 for n in all_notifications if not n.is_read)
        read = total - unread
        
        # Count by type
        by_type = {}
        for notification in all_notifications:
            ntype = notification.notification_type
            by_type[ntype] = by_type.get(ntype, 0) + 1
        
        # Recent notifications (last 7 days)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent = sum(1 for n in all_notifications if n.created_at >= seven_days_ago)
        
        return {
            "total_notifications": total,
            "unread": unread,
            "read": read,
            "read_percentage": (read / total * 100) if total > 0 else 0,
            "by_type": by_type,
            "recent_7_days": recent
        }
    
    async def notify_complaint_assigned(
        self,
        db: AsyncSession,
        authority_id: int,
        complaint_id: UUID,
        complaint_title: str
    ) -> Notification:
        """
        Notify authority when complaint is assigned.
        
        Args:
            db: Database session
            authority_id: Authority ID
            complaint_id: Complaint UUID
            complaint_title: Brief complaint description
        
        Returns:
            Created notification
        """
        message = f"New complaint assigned: {complaint_title[:100]}"
        
        return await self.create_notification(
            db=db,
            recipient_type="Authority",
            recipient_id=str(authority_id),
            complaint_id=complaint_id,
            notification_type="complaint_assigned",
            message=message
        )
    
    async def notify_status_update(
        self,
        db: AsyncSession,
        student_roll_no: str,
        complaint_id: UUID,
        new_status: str,
        complaint_title: str
    ) -> Notification:
        """
        Notify student when complaint status changes.
        
        Args:
            db: Database session
            student_roll_no: Student roll number
            complaint_id: Complaint UUID
            new_status: New status
            complaint_title: Brief complaint description
        
        Returns:
            Created notification
        """
        message = f"Your complaint status changed to '{new_status}': {complaint_title[:80]}"
        
        return await self.create_notification(
            db=db,
            recipient_type="Student",
            recipient_id=student_roll_no,
            complaint_id=complaint_id,
            notification_type="status_update",
            message=message
        )
    
    async def create_status_change_notification(
        self,
        db: AsyncSession,
        complaint_id: UUID,
        student_roll_no: str,
        old_status: str,
        new_status: str
    ) -> Notification:
        """
        Create a notification for a complaint status change.

        Called by the authority status update endpoint.

        Args:
            db: Database session
            complaint_id: Complaint UUID
            student_roll_no: Student roll number
            old_status: Previous status
            new_status: New status

        Returns:
            Created notification
        """
        message = (
            f"Your complaint status changed from '{old_status}' to '{new_status}'"
        )

        return await self.create_notification(
            db=db,
            recipient_type="Student",
            recipient_id=student_roll_no,
            complaint_id=complaint_id,
            notification_type="status_update",
            message=message
        )

    async def notify_vote_milestone(
        self,
        db: AsyncSession,
        student_roll_no: str,
        complaint_id: UUID,
        upvote_count: int
    ) -> Notification:
        """
        Notify student when complaint reaches vote milestone.
        
        Args:
            db: Database session
            student_roll_no: Student roll number
            complaint_id: Complaint UUID
            upvote_count: Number of upvotes
        
        Returns:
            Created notification
        """
        message = f"🎉 Your complaint reached {upvote_count} upvotes!"
        
        return await self.create_notification(
            db=db,
            recipient_type="Student",
            recipient_id=student_roll_no,
            complaint_id=complaint_id,
            notification_type="vote_milestone",
            message=message
        )
    
    async def _send_realtime_notification(self, notification: Notification):
        """
        Send real-time notification via WebSocket.
        TODO: Implement WebSocket integration
        
        Args:
            notification: Notification object
        """
        # Placeholder for WebSocket implementation
        # Example:
        # await websocket_manager.send_to_user(
        #     user_id=notification.recipient_id,
        #     message={
        #         "type": "notification",
        #         "data": {
        #             "id": notification.id,
        #             "type": notification.notification_type,
        #             "message": notification.message
        #         }
        #     }
        # )
        
        logger.debug(f"TODO: Send WebSocket notification to {notification.recipient_id}")
        pass
    
    async def _send_push_notification(self, db: AsyncSession, notification: Notification):
        """Send Web Push notification to all registered devices for this user."""
        try:
            from src.services.push_service import send_push_to_user

            # Build a deep-link URL so tapping the notification opens the right page
            if notification.complaint_id:
                url = f"/complaint/{notification.complaint_id}"
            elif notification.notification_type in ("petition_approved", "petition_rejected"):
                url = "/petitions"
            else:
                url = "/notifications"

            # Urgent notification types get vibration pattern in SW
            urgent_types = {"complaint_escalated", "vote_milestone"}
            urgency = "high" if notification.notification_type in urgent_types else "normal"

            await send_push_to_user(
                db=db,
                user_id=notification.recipient_id,
                title="CampusVoice",
                body=notification.message,
                url=url,
                urgency=urgency,
            )
        except Exception as e:
            # Push is best-effort — never let it break the notification creation
            logger.debug(f"Push notification skipped for {notification.recipient_id}: {e}")


# Create global instance
notification_service = NotificationService()

__all__ = ["NotificationService", "notification_service"]
