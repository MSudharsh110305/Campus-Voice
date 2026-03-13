"""
Pydantic schemas for Complaint endpoints.

✅ FIXED: Removed image_url from create/update schemas
✅ FIXED: Added has_image, image_verification_status fields
✅ FIXED: Updated ImageUploadResponse for binary storage
✅ ADDED: ImageVerificationResult schema for Groq Vision API response
"""

from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID
from src.config.constants import ComplaintStatus, PriorityLevel, VisibilityLevel


class ComplaintCreate(BaseModel):
    """Schema for creating a complaint (✅ FULLY AI-DRIVEN - no category_id required)"""

    # ✅ REMOVED: category_id is NO LONGER required - determined by AI
    # Kept as optional for backward compatibility, but ignored by backend
    category_id: Optional[int] = Field(
        None,
        gt=0,
        description="[DEPRECATED] Category is now auto-determined by AI. This field is ignored.",
        examples=[1]
    )

    original_text: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Original complaint text",
        examples=["The hostel room fan is not working for the past 3 days..."]
    )
    visibility: Optional[VisibilityLevel] = Field(
        default="Public",
        description="Complaint visibility level (Public or Private only)"
    )

    # ✅ Image is handled separately via multipart/form-data
    # No image_url field here

    @field_validator('original_text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate complaint text"""
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Complaint must be at least 10 characters")
        if v.isupper():
            raise ValueError("Please avoid writing in all caps")
        return v

    @field_validator('visibility')
    @classmethod
    def validate_visibility(cls, v: Optional[str]) -> Optional[str]:
        """Validate visibility is only Public or Private"""
        if v and v not in ["Public", "Private"]:
            raise ValueError("Visibility must be either 'Public' or 'Private'. 'Department' is no longer supported.")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "original_text": "The hostel room fan is not working for the past 3 days. It's very hot and difficult to sleep.",
                "visibility": "Public"
            }
        }
    }


class ComplaintUpdate(BaseModel):
    """Schema for updating complaint status (by authority)"""
    
    status: ComplaintStatus = Field(
        ...,
        description="New status"
    )
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for status change"
    )
    
    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate reason for certain status changes"""
        if v is not None:
            v = v.strip()
            if 'status' in info.data:
                status = info.data['status']
                if status in ['Closed', 'Spam'] and not v:
                    raise ValueError(f"Reason is required when marking complaint as {status}")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "In Progress",
                "reason": "Forwarded to maintenance team"
            }
        }
    }


class ComplaintResponse(BaseModel):
    """Schema for complaint response (basic)"""
    
    id: UUID
    category_id: int
    category_name: Optional[str] = None
    original_text: str
    rephrased_text: Optional[str] = None
    visibility: str
    upvotes: int
    downvotes: int
    priority: str
    priority_score: float
    status: str
    assigned_authority_name: Optional[str] = None
    is_marked_as_spam: bool
    spam_reason: Optional[str] = None
    spam_flagged_at: Optional[datetime] = None
    has_disputed: bool = False
    appeal_reason: Optional[str] = None
    # Dispute lifecycle fields
    dispute_deadline: Optional[datetime] = None
    dispute_status: Optional[str] = None
    appeal_deadline: Optional[datetime] = None
    # Soft-delete (excluded from normal responses but present for completeness)
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    # ✅ NEW: Binary image storage fields (replaces image_url)
    has_image: bool = Field(
        default=False,
        description="Whether complaint has an attached image"
    )
    image_verified: bool = Field(
        default=False,
        description="Whether image has been verified by AI"
    )
    image_verification_status: Optional[str] = Field(
        default=None,
        description="Image verification status (Pending/Verified/Rejected)"
    )
    location_verified: bool = Field(
        default=False,
        description="Image EXIF GPS coordinates confirmed within SREC campus"
    )
    # Image grace-period fields — shown to the complaint owner
    image_required: bool = Field(
        default=False,
        description="LLM flagged this complaint as needing a supporting image"
    )
    image_pending: bool = Field(
        default=False,
        description="Complaint is in the image-upload grace period (awaiting owner upload)"
    )
    image_required_deadline: Optional[datetime] = Field(
        default=None,
        description="Deadline by which the owner must upload the image"
    )
    
    submitted_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    student_roll_no: Optional[str] = None
    student_name: Optional[str] = None
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "category_id": 1,
                "category_name": "Hostel",
                "original_text": "Room fan not working",
                "rephrased_text": "Issue: The ceiling fan in my hostel room has stopped functioning...",
                "visibility": "Public",
                "upvotes": 5,
                "downvotes": 0,
                "priority": "Medium",
                "priority_score": 50.5,
                "status": "In Progress",
                "assigned_authority_name": "Hostel Warden",
                "is_marked_as_spam": False,
                "has_image": True,
                "image_verified": True,
                "image_verification_status": "Verified",
                "submitted_at": "2026-02-01T10:00:00",
                "updated_at": "2026-02-01T12:00:00",
                "resolved_at": None
            }
        }
    }


class ComplaintDetailResponse(ComplaintResponse):
    """Schema for detailed complaint response (with status history)"""
    
    student_department: Optional[str] = None
    student_gender: Optional[str] = None
    student_stay_type: Optional[str] = None
    student_year: Optional[int] = None
    complaint_department_id: Optional[int] = None
    is_cross_department: bool = False
    status_updates: Optional[List[dict]] = None
    comments_count: int = 0
    vote_count: int = 0
    
    # ✅ NEW: Image metadata (optional, for detailed view)
    image_filename: Optional[str] = None
    image_size: Optional[int] = None
    image_mimetype: Optional[str] = None
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "category_id": 1,
                "category_name": "Hostel",
                "original_text": "Room fan not working",
                "rephrased_text": "Issue: The ceiling fan in my hostel room has stopped functioning...",
                "visibility": "Public",
                "upvotes": 5,
                "downvotes": 0,
                "priority": "Medium",
                "priority_score": 50.5,
                "status": "In Progress",
                "assigned_authority_name": "Hostel Warden",
                "is_marked_as_spam": False,
                "has_image": True,
                "image_verified": True,
                "image_verification_status": "Verified",
                "submitted_at": "2026-02-01T10:00:00",
                "updated_at": "2026-02-01T12:00:00",
                "resolved_at": None,
                "student_roll_no": "22CS231",
                "student_name": "John Doe",
                "student_department": "Computer Science",
                "student_gender": "Male",
                "student_stay_type": "Hostel",
                "student_year": 3,
                "complaint_department_id": 1,
                "is_cross_department": False,
                "image_filename": "broken_fan.jpg",
                "image_size": 245678,
                "image_mimetype": "image/jpeg",
                "status_updates": [
                    {
                        "status": "Raised",
                        "changed_by": "System",
                        "reason": "Complaint submitted",
                        "changed_at": "2026-02-01T10:00:00"
                    },
                    {
                        "status": "In Progress",
                        "changed_by": "Hostel Warden",
                        "reason": "Forwarded to maintenance team",
                        "changed_at": "2026-02-01T12:00:00"
                    }
                ],
                "comments_count": 2,
                "vote_count": 5
            }
        }
    }


class ComplaintSubmitResponse(BaseModel):
    """Schema for complaint submission response (✅ UPDATED: AI-driven fields)"""

    id: UUID
    status: str
    message: str
    rephrased_text: Optional[str] = None
    priority: str
    assigned_authority: Optional[str] = None

    # ✅ NEW: AI-driven categorization results
    category: Optional[str] = Field(
        None,
        description="AI-determined category"
    )
    target_department_id: Optional[int] = Field(
        None,
        description="AI-determined target department ID"
    )
    target_department_code: Optional[str] = Field(
        None,
        description="AI-determined target department code"
    )
    cross_department: bool = Field(
        default=False,
        description="Whether complaint targets a different department than student's"
    )
    llm_failed: bool = Field(
        default=False,
        description="Whether LLM analysis failed (fallback used)"
    )
    confidence_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="AI confidence score (0.0-1.0)"
    )

    # ✅ Spam status
    is_spam: bool = Field(default=False, description="Whether complaint was auto-detected as spam")
    spam_reason: Optional[str] = Field(default=None, description="Reason for spam detection")

    # ✅ Image processing results
    has_image: bool = False
    image_verified: bool = False
    image_verification_status: Optional[str] = None
    image_verification_message: Optional[str] = None
    location_verified: bool = False

    # ✅ Image requirement information
    image_was_required: bool = Field(
        default=False,
        description="Whether image was required by LLM for this complaint"
    )
    image_requirement_reasoning: Optional[str] = Field(
        default=None,
        description="LLM reasoning for image requirement decision"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "Submitted",
                "message": "Your complaint has been submitted and assigned to the Hostel Warden",
                "rephrased_text": "Issue: The ceiling fan in my hostel room...",
                "priority": "Medium",
                "assigned_authority": "Hostel Warden",
                "category": "Men's Hostel",
                "target_department_id": 1,
                "target_department_code": "CSE",
                "cross_department": False,
                "llm_failed": False,
                "confidence_score": 0.95,
                "has_image": True,
                "image_verified": True,
                "image_verification_status": "Verified",
                "image_verification_message": "Image is relevant to the complaint",
                "image_was_required": True,
                "image_requirement_reasoning": "Infrastructure issue requiring visual evidence"
            }
        }
    }


class ComplaintListResponse(BaseModel):
    """Schema for complaint list with pagination"""
    
    complaints: List[ComplaintResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "complaints": [],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5
            }
        }
    }


class ComplaintFilter(BaseModel):
    """Schema for filtering complaints"""
    
    status: Optional[ComplaintStatus] = None
    priority: Optional[PriorityLevel] = None
    category_id: Optional[int] = None
    department_id: Optional[int] = None
    assigned_to_me: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    # ✅ NEW: Filter by image presence/verification
    has_image: Optional[bool] = Field(
        None,
        description="Filter by complaints with/without images"
    )
    image_verified: Optional[bool] = Field(
        None,
        description="Filter by verified/unverified images"
    )
    
    search: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Search in complaint text"
    )
    
    @field_validator('date_to')
    @classmethod
    def validate_date_range(cls, v: Optional[datetime], info: ValidationInfo) -> Optional[datetime]:
        """Validate that date_to is not before date_from"""
        if v is not None and 'date_from' in info.data:
            date_from = info.data['date_from']
            if date_from is not None and v < date_from:
                raise ValueError("date_to must be greater than or equal to date_from")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "Raised",
                "priority": "High",
                "category_id": 1,
                "has_image": True,
                "image_verified": True,
                "search": "fan"
            }
        }
    }


class SpamFlag(BaseModel):
    """Schema for flagging complaint as spam"""
    
    reason: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Reason for marking as spam"
    )
    is_permanent: bool = Field(
        default=False,
        description="Permanent ban or temporary"
    )
    
    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v: str) -> str:
        """Validate spam reason"""
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Reason must be at least 10 characters")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "reason": "This complaint contains abusive language and is not a genuine issue",
                "is_permanent": False
            }
        }
    }


# ✅ NEW: Image verification result schema (from Groq Vision API)
class ImageVerificationResult(BaseModel):
    """Schema for image verification result from Groq Vision API"""
    
    is_relevant: bool = Field(
        ...,
        description="Whether image is relevant to complaint"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0)"
    )
    explanation: str = Field(
        ...,
        description="Explanation of verification result"
    )
    status: str = Field(
        ...,
        description="Verification status (Verified/Rejected/Pending)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "is_relevant": True,
                "confidence_score": 0.95,
                "explanation": "The image clearly shows a broken ceiling fan, which is directly related to the complaint about a non-functional fan.",
                "status": "Verified"
            }
        }
    }


# ✅ UPDATED: Image upload response for binary storage
class ImageUploadResponse(BaseModel):
    """Schema for image upload response (binary database storage)"""
    
    complaint_id: UUID = Field(
        ...,
        description="Complaint ID that image is attached to"
    )
    has_image: bool = Field(
        ...,
        description="Whether image was successfully stored"
    )
    image_verified: bool = Field(
        ...,
        description="Whether image passed AI verification"
    )
    verification_status: str = Field(
        ...,
        description="Verification status (Pending/Verified/Rejected)"
    )
    verification_message: str = Field(
        ...,
        description="Human-readable verification message"
    )
    
    # Optional metadata
    image_filename: Optional[str] = None
    image_size: Optional[int] = Field(
        None,
        description="Image size in bytes"
    )
    image_mimetype: Optional[str] = None
    confidence_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="AI confidence score"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "complaint_id": "123e4567-e89b-12d3-a456-426614174000",
                "has_image": True,
                "image_verified": True,
                "verification_status": "Verified",
                "verification_message": "Image is relevant to the complaint and has been verified successfully",
                "image_filename": "broken_fan.jpg",
                "image_size": 245678,
                "image_mimetype": "image/jpeg",
                "confidence_score": 0.95
            }
        }
    }


# ✅ NEW: Schema for retrieving complaint image (binary data endpoint)
class ComplaintImageResponse(BaseModel):
    """Schema for complaint image retrieval metadata"""
    
    complaint_id: UUID
    has_image: bool
    image_verified: bool
    image_filename: Optional[str] = None
    image_size: Optional[int] = None
    image_mimetype: Optional[str] = None
    
    # Note: Actual binary data is returned via StreamingResponse, not JSON
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "complaint_id": "123e4567-e89b-12d3-a456-426614174000",
                "has_image": True,
                "image_verified": True,
                "image_filename": "broken_fan.jpg",
                "image_size": 245678,
                "image_mimetype": "image/jpeg"
            }
        }
    }


class CommentCreate(BaseModel):
    """Schema for creating a comment on a complaint"""
    
    content: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Comment content"
    )
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate comment content"""
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Comment must be at least 5 characters")
        if v.isupper():
            raise ValueError("Please avoid writing in all caps")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "content": "I am also facing the same issue in my room."
            }
        }
    }


class CommentResponse(BaseModel):
    """Schema for comment response"""
    
    id: int
    complaint_id: UUID
    commenter_type: str
    commenter_name: str
    content: str
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "complaint_id": "123e4567-e89b-12d3-a456-426614174000",
                "commenter_type": "Student",
                "commenter_name": "John Doe",
                "content": "I am also facing the same issue in my room.",
                "created_at": "2026-02-01T14:00:00",
                "updated_at": "2026-02-01T14:00:00"
            }
        }
    }


class CommentListResponse(BaseModel):
    """Schema for comment list"""
    
    comments: List[CommentResponse]
    total: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "comments": [],
                "total": 5
            }
        }
    }


class SatisfactionRatingRequest(BaseModel):
    """Request body for POST /complaints/{id}/rate"""
    rating: int = Field(..., ge=1, le=5, description="Rating 1 (worst) to 5 (best)")
    feedback: Optional[str] = Field(None, max_length=1000, description="Optional free-text feedback")


class SatisfactionRatingResponse(BaseModel):
    """Response for satisfaction rating submission"""
    complaint_id: UUID
    rating: int
    feedback: Optional[str] = None
    message: str


class DuplicateCheckRequest(BaseModel):
    """Request body for POST /complaints/check-duplicate"""
    text: str = Field(..., min_length=10, max_length=2000)
    category_hint: Optional[str] = None


class DuplicateCandidate(BaseModel):
    """A potential duplicate complaint"""
    id: UUID
    rephrased_text: str
    status: str
    upvotes: int
    submitted_at: datetime
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    is_own: bool = False  # True when this complaint was submitted by the requesting student


class DuplicateCheckResponse(BaseModel):
    """Response for duplicate check"""
    is_likely_duplicate: bool
    duplicates: List[DuplicateCandidate]
    message: str


class ChangelogEntry(BaseModel):
    """Single resolved complaint for the What's Fixed feed"""
    id: UUID
    rephrased_text: str
    resolution_note: Optional[str] = None
    category_name: Optional[str] = None
    resolved_at: Optional[datetime] = None
    upvotes: int
    satisfaction_avg: Optional[float] = None
    win_score: int = 0
    resolution_hours: Optional[float] = None

    model_config = {"from_attributes": True}


class ChangelogResponse(BaseModel):
    """Response for GET /complaints/changelog"""
    entries: List[ChangelogEntry]
    total: int
    page: int
    page_size: int


__all__ = [
    "ComplaintCreate",
    "ComplaintUpdate",
    "ComplaintResponse",
    "ComplaintDetailResponse",
    "ComplaintSubmitResponse",
    "ComplaintListResponse",
    "ComplaintFilter",
    "SpamFlag",
    "ImageVerificationResult",
    "ImageUploadResponse",
    "ComplaintImageResponse",
    "CommentCreate",
    "CommentResponse",
    "CommentListResponse",
    "SatisfactionRatingRequest",
    "SatisfactionRatingResponse",
    "DuplicateCheckRequest",
    "DuplicateCheckResponse",
    "DuplicateCandidate",
    "ChangelogEntry",
    "ChangelogResponse",
]
