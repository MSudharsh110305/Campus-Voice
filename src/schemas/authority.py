"""
Pydantic schemas for Authority endpoints.
"""


from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationInfo
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone  # ✅ Added timezone import

from src.config.constants import (
    AuthorityType,
    AnnouncementCategory,
    AnnouncementPriority,
    VisibilityLevel,
    UpdateCategory,
    UpdatePriority,
)

# ✅ Forward reference to avoid circular imports
if TYPE_CHECKING:
    from .complaint import ComplaintResponse


class AuthorityLogin(BaseModel):
    """Schema for authority login"""
    
    email: EmailStr = Field(
        ...,
        description="Authority email address"
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Password"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "warden@college.edu",
                "password": "SecurePass123!"
            }
        }
    }


class AuthorityCreate(BaseModel):
    """Schema for creating authority (admin only)"""
    
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone: Optional[str] = Field(
        None,
        pattern=r'^[6-9]\d{9}$',
        description="Indian mobile number (10 digits starting with 6-9)"
    )
    authority_type: AuthorityType
    department_id: Optional[int] = Field(None, gt=0)
    designation: Optional[str] = Field(None, max_length=255)
    authority_level: int = Field(..., ge=1, le=100)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Dr. John Smith",
                "email": "john.smith@college.edu",
                "password": "SecurePass123!",
                "phone": "9876543210",
                "authority_type": "Warden",
                "department_id": None,
                "designation": "Chief Warden",
                "authority_level": 5
            }
        }
    }


class AuthorityProfile(BaseModel):
    """Schema for authority profile"""
    
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    authority_type: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    designation: Optional[str] = None
    authority_level: int
    is_active: bool
    created_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "Dr. John Smith",
                "email": "john.smith@college.edu",
                "phone": "9876543210",
                "authority_type": "Warden",
                "department_id": None,
                "department_name": None,
                "designation": "Chief Warden",
                "authority_level": 5,
                "is_active": True,
                "created_at": "2025-08-15T09:00:00"
            }
        }
    }


class AuthorityResponse(BaseModel):
    """Schema for authority login response"""

    id: int
    name: str
    email: str
    authority_type: str
    department_id: Optional[int] = None
    designation: Optional[str] = None
    token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "Dr. John Smith",
                "email": "john.smith@college.edu",
                "authority_type": "Warden",
                "department_id": None,
                "designation": "Chief Warden",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 604800
            }
        }
    }


class AuthorityStats(BaseModel):
    """Schema for authority statistics"""
    
    total_assigned: int
    pending: int
    in_progress: int
    resolved: int
    closed: int
    spam_flagged: int
    avg_resolution_time_hours: Optional[float] = None
    performance_rating: Optional[float] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_assigned": 50,
                "pending": 5,
                "in_progress": 10,
                "resolved": 30,
                "closed": 5,
                "spam_flagged": 2,
                "avg_resolution_time_hours": 24.5,
                "performance_rating": 4.5
            }
        }
    }


class AuthorityDashboard(BaseModel):
    """Schema for authority dashboard data"""
    
    profile: AuthorityProfile
    stats: AuthorityStats
    recent_complaints: List[dict]  # ✅ Keep as dict for now to avoid circular import in runtime
    urgent_complaints: List[dict]  # ✅ Can be typed as ComplaintResponse in routes
    unread_notifications: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "profile": {},
                "stats": {},
                "recent_complaints": [],
                "urgent_complaints": [],
                "unread_notifications": 3
            }
        }
    }


class AuthorityProfileUpdate(BaseModel):
    """Schema for updating authority profile"""
    
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(
        None,
        pattern=r'^[6-9]\d{9}$',
        description="Indian mobile number (10 digits starting with 6-9)"
    )
    designation: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Dr. John Smith",
                "phone": "9876543210",
                "designation": "Senior Warden"
            }
        }
    }


class AuthorityListResponse(BaseModel):
    """Schema for authority list"""
    
    authorities: List[AuthorityProfile]
    total: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "authorities": [],
                "total": 10
            }
        }
    }


# ==================== AUTHORITY ANNOUNCEMENTS/UPDATES ====================


class AuthorityAnnouncementCreate(BaseModel):
    """Schema for creating authority announcement/update"""
    
    title: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Announcement title",
        examples=["Important: Hostel Maintenance Schedule"]
    )
    content: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Announcement content/message",
        examples=["The hostel will undergo routine maintenance from Feb 10-12. Please cooperate."]
    )
    category: AnnouncementCategory = Field(
        ...,
        description="Announcement category: Announcement, Notice, Alert, Maintenance, Event",
        examples=["Maintenance"]
    )
    priority: AnnouncementPriority = Field(
        default="Medium",
        description="Priority level: Low, Medium, High, Critical",
        examples=["High"]
    )
    visibility: VisibilityLevel = Field(
        default="All Students",
        description="Who can see this: All Students, Department Only, Hostel Only, Public",
        examples=["Hostel Only"]
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="When this announcement expires (optional)",
        examples=["2026-02-12T23:59:59"]
    )
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title"""
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        if v.isupper():
            raise ValueError("Please avoid writing title in all caps")
        return v
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content"""
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Content must be at least 10 characters")
        return v
    
    @field_validator('expires_at')
    @classmethod
    def validate_expires_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate expiry date is in future"""
        if v is not None:
            # Normalize naive datetime to UTC to avoid offset-naive vs offset-aware comparison error
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= datetime.now(timezone.utc):
                raise ValueError("Expiry date must be in the future")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Important: Hostel Maintenance Schedule",
                "content": "The hostel will undergo routine maintenance from Feb 10-12, 2026. Water supply will be affected from 9 AM to 5 PM. Please store water in advance. We apologize for the inconvenience.",
                "category": "Maintenance",
                "priority": "High",
                "visibility": "Hostel Only",
                "expires_at": "2026-02-12T23:59:59"
            }
        }
    }


class AuthorityAnnouncementUpdate(BaseModel):
    """Schema for updating authority announcement"""
    
    title: Optional[str] = Field(
        None,
        min_length=5,
        max_length=255,
        description="Updated title"
    )
    content: Optional[str] = Field(
        None,
        min_length=10,
        max_length=5000,
        description="Updated content"
    )
    category: Optional[AnnouncementCategory] = None
    priority: Optional[AnnouncementPriority] = None
    visibility: Optional[VisibilityLevel] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = Field(
        None,
        description="Set to False to hide/archive the announcement"
    )
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Validate title"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title cannot be empty")
            if v.isupper():
                raise ValueError("Please avoid writing title in all caps")
        return v
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: Optional[str]) -> Optional[str]:
        """Validate content"""
        if v is not None:
            v = v.strip()
            if len(v) < 10:
                raise ValueError("Content must be at least 10 characters")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Updated: Hostel Maintenance Postponed",
                "content": "The maintenance has been postponed to Feb 15-17.",
                "priority": "Medium",
                "expires_at": "2026-02-17T23:59:59"
            }
        }
    }


class AuthorityAnnouncementResponse(BaseModel):
    """Schema for authority announcement response"""
    
    id: int
    authority_id: int
    authority_name: Optional[str] = None
    authority_type: Optional[str] = None
    title: str
    content: str
    category: str
    priority: str
    visibility: str
    views_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "authority_id": 5,
                "authority_name": "Dr. John Smith",
                "authority_type": "Warden",
                "title": "Important: Hostel Maintenance Schedule",
                "content": "The hostel will undergo routine maintenance...",
                "category": "Maintenance",
                "priority": "High",
                "visibility": "Hostel Only",
                "views_count": 150,
                "is_active": True,
                "created_at": "2026-02-05T10:00:00",
                "updated_at": "2026-02-05T10:00:00",
                "expires_at": "2026-02-12T23:59:59"
            }
        }
    }


class AuthorityAnnouncementListResponse(BaseModel):
    """Schema for authority announcement list with pagination"""
    
    announcements: List[AuthorityAnnouncementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    active_count: int
    expired_count: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "announcements": [],
                "total": 25,
                "page": 1,
                "page_size": 10,
                "total_pages": 3,
                "active_count": 20,
                "expired_count": 5
            }
        }
    }

# ==================== AUTHORITY UPDATES (FOR COMPLAINTS) ====================

class AuthorityUpdateCreate(BaseModel):
    """
    Schema for authority posting update about complaint progress.
    
    Different from announcements - this is tied to a specific complaint.
    Used when authority wants to post public update like:
    "Technician assigned, will fix AC by tomorrow"
    """
    
    title: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Update title/summary"
    )
    content: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Detailed update message"
    )
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title"""
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        if v.isupper():
            raise ValueError("Please avoid writing title in all caps")
        return v
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content"""
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Content must be at least 10 characters")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "AC Repair Progress Update",
                "content": "Technician has been assigned and will complete the repair by tomorrow afternoon. Spare parts have been ordered."
            }
        }
    }


class AuthorityUpdateResponse(BaseModel):
    """
    Schema for authority update response.
    
    Returns details of complaint update posted by authority.
    """
    
    update_id: int = Field(..., description="Status update ID")
    complaint_id: str = Field(..., description="Related complaint UUID")
    authority_id: int = Field(..., description="Authority who posted update")
    authority_name: str = Field(..., description="Authority name")
    title: str = Field(..., description="Update title")
    content: str = Field(..., description="Update content")
    posted_at: datetime = Field(..., description="When update was posted")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "update_id": 15,
                "complaint_id": "123e4567-e89b-12d3-a456-426614174000",
                "authority_id": 5,
                "authority_name": "Dr. John Smith",
                "title": "AC Repair Progress Update",
                "content": "Technician assigned, repair scheduled for tomorrow.",
                "posted_at": "2026-02-03T15:30:00"
            }
        }
    }

# ==================== NOTICE / BROADCAST ====================

class NoticeCreate(BaseModel):
    """Schema for creating a targeted notice/broadcast to students"""

    title: str = Field(..., min_length=5, max_length=255, description="Notice title")
    content: str = Field(..., min_length=10, max_length=5000, description="Notice body")
    category: UpdateCategory = Field(
        default=UpdateCategory.ANNOUNCEMENT,
        description="Category: Announcement, Policy Change, Maintenance, Event, Emergency, General"
    )
    priority: UpdatePriority = Field(
        default=UpdatePriority.MEDIUM,
        description="Priority: Low, Medium, High, Urgent"
    )
    # Targeting filters — null/empty means no restriction on that dimension
    target_gender: Optional[List[str]] = Field(
        None,
        description="Gender filter: ['Male'], ['Female'], ['Male','Female'] or null for all"
    )
    target_stay_types: Optional[List[str]] = Field(
        None,
        description="Residence filter: ['Hostel'], ['Day Scholar'] or null for all"
    )
    target_departments: Optional[List[str]] = Field(
        None,
        description="Dept codes e.g. ['CSE','ECE'] or null for all"
    )
    target_years: Optional[List[str]] = Field(
        None,
        description="Year numbers as strings: ['1','2','3','4'] or null for all"
    )
    expires_at: Optional[datetime] = Field(None, description="Expiry timestamp (optional)")

    @field_validator('target_gender')
    @classmethod
    def validate_target_gender(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            valid = {"Male", "Female", "Other"}
            for g in v:
                if g not in valid:
                    raise ValueError(f"Invalid gender value: {g}. Must be Male, Female, or Other")
        return v

    @field_validator('target_stay_types')
    @classmethod
    def validate_stay_types(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            valid = {"Hostel", "Day Scholar"}
            for s in v:
                if s not in valid:
                    raise ValueError(f"Invalid stay type: {s}. Must be Hostel or Day Scholar")
        return v

    @field_validator('target_years')
    @classmethod
    def validate_years(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            for y in v:
                if not y.isdigit() or not (1 <= int(y) <= 10):
                    raise ValueError(f"Invalid year: {y}. Must be a digit between 1 and 10")
        return v

    @field_validator('expires_at')
    @classmethod
    def validate_expires_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= datetime.now(timezone.utc):
                raise ValueError("Expiry date must be in the future")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Hot water maintenance this Sunday",
                "content": "Hot water supply in Block A will be unavailable this Sunday 9 AM–5 PM for pipe maintenance.",
                "category": "Maintenance",
                "priority": "High",
                "target_gender": ["Male"],
                "target_stay_types": ["Hostel"],
                "target_departments": None,
                "target_years": None,
                "expires_at": "2026-02-25T23:59:59"
            }
        }
    }


class NoticeAttachmentItem(BaseModel):
    """A single attachment belonging to a notice."""
    id: int
    filename: str
    mimetype: str
    size: int

    model_config = {"from_attributes": True}


class NoticeResponse(BaseModel):
    """Schema for a notice/broadcast response"""

    id: int
    authority_id: int
    authority_name: Optional[str] = None
    authority_type: Optional[str] = None
    title: str
    content: str
    category: str
    priority: str
    target_gender: Optional[List[str]] = None
    target_stay_types: Optional[List[str]] = None
    target_departments: Optional[List[str]] = None
    target_years: Optional[List[str]] = None
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    attachment_filename: Optional[str] = None
    attachment_mimetype: Optional[str] = None
    # Multi-file attachments (new)
    attachments: List[NoticeAttachmentItem] = []

    model_config = {"from_attributes": True}


class NoticeListResponse(BaseModel):
    """Schema for paginated notice list"""

    notices: List[NoticeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "notices": [],
                "total": 5,
                "page": 1,
                "page_size": 20,
                "total_pages": 1
            }
        }
    }


__all__ = [
    # Authority Management
    "AuthorityLogin",
    "AuthorityCreate",
    "AuthorityProfile",
    "AuthorityResponse",
    "AuthorityStats",
    "AuthorityDashboard",
    "AuthorityProfileUpdate",
    "AuthorityListResponse",

    # Authority Announcements (general broadcasts)
    "AuthorityAnnouncementCreate",
    "AuthorityAnnouncementUpdate",
    "AuthorityAnnouncementResponse",
    "AuthorityAnnouncementListResponse",

    # Authority Updates (complaint-specific updates)
    "AuthorityUpdateCreate",
    "AuthorityUpdateResponse",

    # Notice / Broadcast
    "NoticeCreate",
    "NoticeResponse",
    "NoticeListResponse",
    "NoticeAttachmentItem",
]
