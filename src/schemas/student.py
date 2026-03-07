"""
Pydantic schemas for Student endpoints.
Validation models for registration, login, profile, etc.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationInfo
from typing import Optional
from datetime import datetime
from src.config.constants import Gender, StayType


class StudentRegister(BaseModel):
    """Schema for student registration"""
    
    roll_no: str = Field(
        ...,
        min_length=5,
        max_length=20,
        description="Student roll number",
        examples=["22CS231"]
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Student full name",
        examples=["John Doe"]
    )
    email: EmailStr = Field(
        ...,
        description="Student email address",
        examples=["john.doe@college.edu"]
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 characters)",
        examples=["SecurePass123!"]
    )
    gender: Gender = Field(
        ...,
        description="Gender: Male, Female, Other",
        examples=["Male"]
    )
    stay_type: StayType = Field(
        ...,
        description="Stay type: Hostel or Day Scholar",
        examples=["Hostel"]
    )
    department_id: int = Field(
        ...,
        gt=0,
        description="Department ID",
        examples=[1]
    )
    year: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="Academic year (1-4 for undergrad, 5+ for postgrad)",
        examples=[3]
    )
    
    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        """Validate that email uses @srec.ac.in domain"""
        if not str(v).endswith('@srec.ac.in'):
            raise ValueError("Email must be a valid @srec.ac.in address")
        return str(v)

    @field_validator('roll_no')
    @classmethod
    def validate_roll_no(cls, v: str) -> str:
        """Validate roll number format"""
        v = v.strip().upper()
        if not v:
            raise ValueError("Roll number cannot be empty")
        if not v.replace(" ", "").isalnum():
            raise ValueError("Roll number must be alphanumeric")
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name"""
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if any(char.isdigit() for char in v):
            raise ValueError("Name cannot contain numbers")
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "roll_no": "22CS231",
                "name": "John Doe",
                "email": "john.doe@college.edu",
                "password": "SecurePass123!",
                "gender": "Male",
                "stay_type": "Hostel",
                "department_id": 1,
                "year": 3
            }
        }
    }


class StudentLogin(BaseModel):
    """Schema for student login"""
    
    email_or_roll_no: str = Field(
        ...,
        min_length=3,
        description="Email address or roll number",
        examples=["john.doe@college.edu", "22CS231"]
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Password",
        examples=["SecurePass123!"]
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email_or_roll_no": "john.doe@college.edu",
                "password": "SecurePass123!"
            }
        }
    }


class StudentProfile(BaseModel):
    """Schema for student profile (response)"""
    
    roll_no: str
    name: str
    email: str
    gender: str
    stay_type: str
    department_id: int
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    year: Optional[int] = None
    is_active: bool
    email_verified: bool
    created_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "roll_no": "22CS231",
                "name": "John Doe",
                "email": "john.doe@college.edu",
                "gender": "Male",
                "stay_type": "Hostel",
                "department_id": 1,
                "department_name": "Computer Science & Engineering",
                "department_code": "CSE",
                "year": 3,
                "is_active": True,
                "email_verified": True,
                "created_at": "2025-06-15T10:30:00"
            }
        }
    }


class StudentProfileUpdate(BaseModel):
    """Schema for updating student profile"""
    
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(
        None,
        pattern=r'^[6-9]\d{9}$',
        description="Indian mobile number (10 digits starting with 6-9)"
    )
    year: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="Academic year (1-4 for undergrad, 5+ for postgrad)"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate name"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Name cannot be empty")
            if any(char.isdigit() for char in v):
                raise ValueError("Name cannot contain numbers")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "John Smith",
                "email": "john.smith@college.edu",
                "year": 4
            }
        }
    }


class StudentResponse(BaseModel):
    """Schema for student registration/login response"""

    roll_no: str
    name: str
    email: str
    gender: Optional[str] = None
    stay_type: Optional[str] = None
    year: Optional[int] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "roll_no": "22CS231",
                "name": "John Doe",
                "email": "john.doe@college.edu",
                "year": 3,
                "department_id": 1,
                "department_name": "Computer Science & Engineering",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 604800
            }
        }
    }


class StudentStats(BaseModel):
    """Schema for student statistics"""
    
    total_complaints: int
    raised: int
    in_progress: int
    resolved: int
    closed: int
    spam: int
    total_votes_cast: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_complaints": 10,
                "raised": 2,
                "in_progress": 3,
                "resolved": 4,
                "closed": 1,
                "spam": 0,
                "total_votes_cast": 25
            }
        }
    }


class PasswordChange(BaseModel):
    """Schema for password change"""
    
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str, info: ValidationInfo) -> str:
        """Validate new password strength and difference from old"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if 'old_password' in info.data and v == info.data['old_password']:
            raise ValueError("New password must be different from old password")
        
        return v
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        """Validate passwords match"""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError("Passwords do not match")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "old_password": "OldPass123!",
                "new_password": "NewPass456!",
                "confirm_password": "NewPass456!"
            }
        }
    }


class EmailVerification(BaseModel):
    """Schema for email verification"""
    
    token: str = Field(..., min_length=32)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
            }
        }
    }
class StudentListResponse(BaseModel):
    """
    Schema for student list response (admin endpoint).
    
    Returns paginated list of students with total count.
    """
    
    students: list[StudentProfile] = Field(
        ...,
        description="List of student profiles"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of students matching filter"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "students": [
                    {
                        "roll_no": "22CS231",
                        "name": "John Doe",
                        "email": "john.doe@college.edu",
                        "gender": "Male",
                        "stay_type": "Hostel",
                        "department_id": 1,
                        "department_name": "Computer Science & Engineering",
                        "department_code": "CSE",
                        "year": 3,
                        "is_active": True,
                        "email_verified": True,
                        "created_at": "2025-06-15T10:30:00"
                    }
                ],
                "total": 150
            }
        }
    }
__all__ = [
    # Registration & Authentication
    "StudentRegister",
    "StudentLogin",
    "StudentResponse",
    
    # Profile Management
    "StudentProfile",
    "StudentProfileUpdate",
    "PasswordChange",
    "EmailVerification",
    
    # Statistics & Lists
    "StudentStats",
    "StudentListResponse",  # ✅ ADDED - for admin list students endpoint
]
