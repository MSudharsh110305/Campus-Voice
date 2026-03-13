"""
Pydantic schemas for Vote endpoints.
"""

from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID
from src.config.constants import VoteType


class VoteCreate(BaseModel):
    """Schema for creating a vote"""
    
    vote_type: VoteType = Field(
        ...,
        description="Vote type: Upvote or Downvote"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "vote_type": "Upvote"
            }
        }
    }


class VoteResponse(BaseModel):
    """Schema for vote response"""
    
    complaint_id: UUID
    upvotes: int = Field(..., ge=0)
    downvotes: int = Field(..., ge=0)
    priority_score: float = Field(..., ge=0.0)
    priority: str
    user_vote: Optional[Literal["Upvote", "Downvote"]] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "complaint_id": "123e4567-e89b-12d3-a456-426614174000",
                "upvotes": 15,
                "downvotes": 2,
                "priority_score": 51.3,
                "priority": "Medium",
                "user_vote": "Upvote"
            }
        }
    }


class VoteStats(BaseModel):
    """Schema for vote statistics"""
    
    total_votes: int = Field(..., ge=0)
    upvotes: int = Field(..., ge=0)
    downvotes: int = Field(..., ge=0)
    net_votes: int
    vote_ratio: float = Field(..., ge=0.0, le=1.0)
    
    @field_validator('vote_ratio')
    @classmethod
    def validate_vote_ratio(cls, v: float, info: ValidationInfo) -> float:
        """Calculate and validate vote ratio"""
        if 'total_votes' in info.data and 'upvotes' in info.data:
            total = info.data['total_votes']
            upvotes = info.data['upvotes']
            
            if total == 0:
                return 0.0
            
            expected_ratio = upvotes / total
            if abs(v - expected_ratio) > 0.01:
                return expected_ratio
        
        return v
    
    @field_validator('total_votes')
    @classmethod
    def validate_total_votes(cls, v: int, info: ValidationInfo) -> int:
        """Validate total votes equals upvotes plus downvotes"""
        if 'upvotes' in info.data and 'downvotes' in info.data:
            expected_total = info.data['upvotes'] + info.data['downvotes']
            if v != expected_total:
                return expected_total
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_votes": 20,
                "upvotes": 15,
                "downvotes": 5,
                "net_votes": 10,
                "vote_ratio": 0.75
            }
        }
    }


class VoteDeleteResponse(BaseModel):
    """Schema for vote deletion response"""
    
    message: str
    complaint_id: UUID
    upvotes: int = Field(..., ge=0)
    downvotes: int = Field(..., ge=0)
    priority_score: float = Field(..., ge=0.0)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Vote removed successfully",
                "complaint_id": "123e4567-e89b-12d3-a456-426614174000",
                "upvotes": 14,
                "downvotes": 2,
                "priority_score": 51.2
            }
        }
    }


__all__ = [
    "VoteCreate",
    "VoteResponse",
    "VoteStats",
    "VoteDeleteResponse",
]
