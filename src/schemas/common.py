"""
Common Pydantic schemas used across the application.
"""


from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import Optional, Any, Dict, List, Generic, TypeVar
from datetime import datetime, timezone
import math


T = TypeVar('T')


class SuccessResponse(BaseModel):
    """Generic success response"""
    
    success: bool = True
    message: str
    data: Optional[Any] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": None
            }
        }
    }


class ErrorResponse(BaseModel):
    """Generic error response"""
    
    success: bool = False
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "error": "Invalid credentials",
                "detail": "Email or password is incorrect",
                "error_code": "AUTH_FAILED",
                "timestamp": "2026-02-02T10:00:00Z"
            }
        }
    }


class PaginationParams(BaseModel):
    """Schema for pagination parameters"""
    
    page: int = Field(
        default=1,
        ge=1,
        description="Page number (starts at 1)"
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page"
    )
    
    @property
    def skip(self) -> int:
        """Calculate skip value for database query"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit value for database query"""
        return self.page_size
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "page": 1,
                "page_size": 20
            }
        }
    }


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse[T]":
        """Create paginated response"""
        # ✅ IMPROVED: Handle edge case and use clearer calculation
        if page_size <= 0:
            page_size = 20  # Default fallback
        
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
                "has_next": True,
                "has_previous": False
            }
        }
    }


class HealthCheckResponse(BaseModel):
    """Schema for health check response"""
    
    status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    database: str
    version: str
    uptime_seconds: Optional[float] = None
    environment: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "timestamp": "2026-02-02T10:00:00Z",
                "database": "connected",
                "version": "1.0.0",
                "uptime_seconds": 3600.5,
                "environment": "production"
            }
        }
    }


class TokenResponse(BaseModel):
    """Schema for token response"""
    
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 604800
            }
        }
    }


class SystemStats(BaseModel):
    """Schema for system-wide statistics"""
    
    total_students: int
    total_authorities: int
    total_complaints: int
    total_announcements: int = 0
    complaints_by_status: Dict[str, int]
    complaints_by_priority: Dict[str, int]
    complaints_by_category: Dict[str, int]
    avg_resolution_time_hours: Optional[float] = None
    spam_percentage: Optional[float] = None
    active_students_count: Optional[int] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_students": 1000,
                "total_authorities": 50,
                "total_complaints": 500,
                "total_announcements": 15,
                "complaints_by_status": {
                    "Raised": 50,
                    "In Progress": 100,
                    "Resolved": 300,
                    "Closed": 50
                },
                "complaints_by_priority": {
                    "Low": 100,
                    "Medium": 250,
                    "High": 100,
                    "Critical": 50
                },
                "complaints_by_category": {
                    "Hostel": 200,
                    "General": 150,
                    "Department": 100,
                    "Disciplinary Committee": 50
                },
                "avg_resolution_time_hours": 36.5,
                "spam_percentage": 2.5,
                "active_students_count": 950
            }
        }
    }


class MessageResponse(BaseModel):
    """Simple message response"""
    
    message: str
    success: bool = True
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Operation completed successfully",
                "success": True
            }
        }
    }


class ValidationError(BaseModel):
    """Schema for validation error details"""
    
    field: str
    message: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "field": "email",
                "message": "Invalid email format"
            }
        }
    }


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation response"""
    
    success_count: int
    failure_count: int
    total: int
    errors: Optional[List[Dict[str, Any]]] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total == 0:
            return 0.0
        return (self.success_count / self.total) * 100
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success_count": 8,
                "failure_count": 2,
                "total": 10,
                "errors": [
                    {"index": 3, "error": "Invalid data"},
                    {"index": 7, "error": "Duplicate entry"}
                ]
            }
        }
    }


class DateRangeFilter(BaseModel):
    """Schema for date range filtering"""
    
    date_from: Optional[datetime] = Field(
        None,
        description="Start date (inclusive)"
    )
    date_to: Optional[datetime] = Field(
        None,
        description="End date (inclusive)"
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
                "date_from": "2026-01-01T00:00:00Z",
                "date_to": "2026-02-01T23:59:59Z"
            }
        }
    }


__all__ = [
    "SuccessResponse",
    "ErrorResponse",
    "PaginationParams",
    "PaginatedResponse",
    "HealthCheckResponse",
    "TokenResponse",
    "SystemStats",
    "MessageResponse",
    "ValidationError",
    "BulkOperationResponse",
    "DateRangeFilter",
]
