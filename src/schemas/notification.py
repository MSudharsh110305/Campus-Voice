"""
Pydantic schemas for Notification endpoints.

✅ ADDED: UnreadCountResponse (alias for NotificationUnreadCount)
✅ Maintains backward compatibility with test_schemas.py
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID
from src.config.constants import NotificationType


class NotificationCreate(BaseModel):
    """Schema for creating a notification (internal use)"""
    
    recipient_type: Literal["Student", "Authority"] = Field(
        ...,
        description="Type of recipient"
    )
    recipient_id: str = Field(
        ...,
        min_length=1,
        description="Roll number or authority ID"
    )
    complaint_id: Optional[UUID] = None
    notification_type: NotificationType
    message: str = Field(..., min_length=1, max_length=500)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "recipient_type": "Student",
                "recipient_id": "22CS231",
                "complaint_id": "123e4567-e89b-12d3-a456-426614174000",
                "notification_type": "status_update",
                "message": "Your complaint has been updated to 'In Progress'"
            }
        }
    }


class NotificationResponse(BaseModel):
    """Schema for notification response"""
    
    id: int
    recipient_type: str
    complaint_id: Optional[UUID] = None
    notification_type: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None
    complaint_title: Optional[str] = None
    complaint_status: Optional[str] = None
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "recipient_type": "Student",
                "complaint_id": "123e4567-e89b-12d3-a456-426614174000",
                "notification_type": "status_update",
                "message": "Your complaint has been updated to 'In Progress'",
                "is_read": False,
                "created_at": "2026-02-01T10:00:00",
                "read_at": None,
                "complaint_title": "Room fan not working",
                "complaint_status": "In Progress"
            }
        }
    }


class NotificationListResponse(BaseModel):
    """Schema for notification list"""
    
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "notifications": [],
                "total": 10,
                "unread_count": 3
            }
        }
    }


class NotificationMarkRead(BaseModel):
    """Schema for marking notifications as read"""
    
    notification_ids: List[int] = Field(
        ...,
        min_length=1,
        description="List of notification IDs to mark as read"
    )
    
    @field_validator('notification_ids')
    @classmethod
    def validate_notification_ids(cls, v: List[int]) -> List[int]:
        """Validate all notification IDs are positive"""
        if not v:
            raise ValueError("At least one notification ID is required")
        if any(nid <= 0 for nid in v):
            raise ValueError("All notification IDs must be positive integers")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "notification_ids": [1, 2, 3]
            }
        }
    }


class NotificationUnreadCount(BaseModel):
    """Schema for unread notification count"""
    
    unread_count: int = Field(
        ...,
        ge=0,
        description="Number of unread notifications"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "unread_count": 5
            }
        }
    }


# ✅ NEW: Alias for students.py import compatibility
UnreadCountResponse = NotificationUnreadCount


__all__ = [
    "NotificationCreate",
    "NotificationResponse",
    "NotificationListResponse",
    "NotificationMarkRead",
    "NotificationUnreadCount",
    "UnreadCountResponse",  # ✅ ADDED: Alias for backward compatibility
]
