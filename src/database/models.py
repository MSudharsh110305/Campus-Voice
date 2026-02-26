"""
SQLAlchemy ORM models for CampusVoice.
All database tables with relationships, constraints, and indexes.

✅ FIXED: Image storage using binary columns
✅ FIXED: ImageVerificationLog - removed image_url, added llm_response
✅ ADDED: Proper indexes for image queries
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, BigInteger, CheckConstraint, Index, UniqueConstraint,
    LargeBinary
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func


Base = declarative_base()


# ==================== CORE TABLES ====================


class Department(Base):
    """Department model - 13 engineering departments"""
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hod_name = Column(String(255), nullable=True)
    hod_email = Column(String(255), nullable=True)
    hod_phone = Column(String(20), nullable=True)
    total_students = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    students = relationship("Student", back_populates="department")
    authorities = relationship("Authority", back_populates="department")
    complaints = relationship("Complaint", back_populates="complaint_department")
    
    def __repr__(self):
        return f"<Department(code={self.code}, name={self.name})>"


class ComplaintCategory(Base):
    """Complaint category model - 4 fixed categories"""
    __tablename__ = "complaint_categories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    keywords = Column(ARRAY(String), nullable=True)
    
    default_authority_id = Column(
        BigInteger,
        ForeignKey("authorities.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    complaints = relationship("Complaint", back_populates="category")
    routing_rules = relationship("AuthorityRoutingRule", back_populates="category")
    
    def __repr__(self):
        return f"<ComplaintCategory(name={self.name})>"


class Student(Base):
    """Student model - registered students who submit complaints"""
    __tablename__ = "students"
    
    roll_no = Column(String(20), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    gender = Column(String(10), nullable=False)
    stay_type = Column(String(20), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    department = relationship("Department", back_populates="students")
    complaints = relationship("Complaint", back_populates="student", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="student", cascade="all, delete-orphan")
    spam_entries = relationship("SpamBlacklist", back_populates="student", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("gender IN ('Male', 'Female', 'Other')", name="check_gender"),
        CheckConstraint("stay_type IN ('Hostel', 'Day Scholar')", name="check_stay_type"),
        CheckConstraint("year >= 1 AND year <= 10", name="check_year"),
        Index("idx_student_dept_year_stay", "department_id", "year", "stay_type"),
        Index("idx_student_year_stay", "year", "stay_type", "is_active"),
        Index("idx_student_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<Student(roll_no={self.roll_no}, name={self.name}, year={self.year})>"


class Authority(Base):
    """Authority model - wardens, HODs, admin officers, etc."""
    __tablename__ = "authorities"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    authority_type = Column(String(100), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    designation = Column(String(255), nullable=True)
    authority_level = Column(Integer, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    department = relationship("Department", back_populates="authorities")
    assigned_complaints = relationship(
        "Complaint",
        foreign_keys="Complaint.assigned_authority_id",
        back_populates="assigned_authority"
    )
    status_updates = relationship("StatusUpdate", back_populates="updated_by_authority")
    spam_flags = relationship(
        "Complaint",
        foreign_keys="Complaint.spam_flagged_by",
        back_populates="spam_flagged_by_authority"
    )
    authority_updates = relationship("AuthorityUpdate", back_populates="authority", cascade="all, delete-orphan")
    spam_blacklist_entries = relationship("SpamBlacklist", back_populates="blacklisted_by_authority")
    admin_audit_logs = relationship("AdminAuditLog", back_populates="admin")
    
    def __repr__(self):
        return f"<Authority(name={self.name}, type={self.authority_type}, level={self.authority_level})>"


class Complaint(Base):
    """Complaint model - main table for student complaints
    
    ✅ FIXED: Image storage using binary columns for database storage
    ✅ REMOVED: image_url column (legacy, not needed)
    ✅ ADDED: image_verified and image_verification_status columns
    """
    __tablename__ = "complaints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_roll_no = Column(String(20), ForeignKey("students.roll_no", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("complaint_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    original_text = Column(Text, nullable=False)
    rephrased_text = Column(Text, nullable=True)
    visibility = Column(String(50), default="Private", nullable=False, index=True)
    upvotes = Column(Integer, default=0, nullable=False)
    downvotes = Column(Integer, default=0, nullable=False)
    priority_score = Column(Float, default=0.0, nullable=False, index=True)
    priority = Column(String(20), default="Medium", nullable=False, index=True)
    assigned_authority_id = Column(BigInteger, ForeignKey("authorities.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    original_assigned_authority_id = Column(BigInteger, nullable=True)
    status = Column(String(50), default="Raised", nullable=False, index=True)
    is_marked_as_spam = Column(Boolean, default=False, nullable=False, index=True)
    spam_reason = Column(Text, nullable=True)
    spam_flagged_by = Column(BigInteger, ForeignKey("authorities.id", ondelete="SET NULL"), nullable=True)
    spam_flagged_at = Column(DateTime(timezone=True), nullable=True)
    
    # ✅ IMAGE STORAGE - Binary columns for database storage
    image_data = Column(LargeBinary, nullable=True)  # Original image binary
    image_filename = Column(String(255), nullable=True)  # Original filename
    image_mimetype = Column(String(100), nullable=True)  # MIME type (image/jpeg, image/png)
    image_size = Column(Integer, nullable=True)  # Size in bytes
    
    # ✅ THUMBNAIL - Optimized smaller version
    thumbnail_data = Column(LargeBinary, nullable=True)  # Thumbnail binary (200x200)
    thumbnail_size = Column(Integer, nullable=True)  # Thumbnail size in bytes
    
    # ✅ IMAGE VERIFICATION - Status tracking
    image_verified = Column(Boolean, default=False, nullable=False, index=True)
    image_verification_status = Column(String(50), nullable=True, index=True)
    # Status values: 'Pending', 'Verified', 'Rejected', 'Error'
    
    # Cross-department tracking
    complaint_department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    is_cross_department = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    submitted_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    student = relationship("Student", back_populates="complaints")
    category = relationship("ComplaintCategory", back_populates="complaints")
    assigned_authority = relationship("Authority", foreign_keys=[assigned_authority_id], back_populates="assigned_complaints")
    spam_flagged_by_authority = relationship("Authority", foreign_keys=[spam_flagged_by], back_populates="spam_flags")
    complaint_department = relationship("Department", back_populates="complaints")
    votes = relationship("Vote", back_populates="complaint", cascade="all, delete-orphan")
    status_updates = relationship("StatusUpdate", back_populates="complaint", cascade="all, delete-orphan")
    image_verification_logs = relationship("ImageVerificationLog", back_populates="complaint", cascade="all, delete-orphan")
    llm_logs = relationship("LLMProcessingLog", back_populates="complaint", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="complaint", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="complaint", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("visibility IN ('Private', 'Department', 'Public')", name="check_visibility"),
        CheckConstraint("status IN ('Raised', 'In Progress', 'Resolved', 'Closed', 'Spam')", name="check_status"),
        CheckConstraint("priority IN ('Low', 'Medium', 'High', 'Critical')", name="check_priority"),
        CheckConstraint("upvotes >= 0", name="check_upvotes"),
        CheckConstraint("downvotes >= 0", name="check_downvotes"),
        CheckConstraint("image_size >= 0", name="check_image_size"),
        CheckConstraint("thumbnail_size >= 0", name="check_thumbnail_size"),
        CheckConstraint(
            "image_verification_status IN ('Pending', 'Verified', 'Rejected', 'Error')",
            name="check_image_verification_status"
        ),
        # Performance indexes
        Index("idx_complaint_status_priority", "status", "priority_score"),
        Index("idx_complaint_student_status", "student_roll_no", "status"),
        Index("idx_complaint_visibility_status", "visibility", "status", "submitted_at"),
        # ✅ NEW: Image-specific indexes
        Index("idx_complaint_has_image", "image_verified", postgresql_where=(Column("image_data").isnot(None))),
        Index("idx_complaint_image_pending", "image_verification_status", postgresql_where=(Column("image_verification_status") == "Pending")),
    )
    
    def __repr__(self):
        return f"<Complaint(id={str(self.id)[:8]}, status={self.status}, priority={self.priority})>"
    
    @property
    def has_image(self) -> bool:
        """Check if complaint has an image attached"""
        return self.image_data is not None

    @property
    def assigned_authority_name(self) -> str | None:
        """Return the name of the assigned authority if loaded"""
        try:
            auth = object.__getattribute__(self, 'assigned_authority')
            return auth.name if auth is not None else None
        except Exception:
            return None


class AuthorityUpdate(Base):
    """Authority update model - announcements and updates from authorities"""
    __tablename__ = "authority_updates"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    authority_id = Column(BigInteger, ForeignKey("authorities.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    priority = Column(String(20), nullable=False, index=True)
    visibility = Column(String(50), nullable=False, index=True)
    target_departments = Column(ARRAY(String), nullable=True)
    target_years = Column(ARRAY(String), nullable=True)
    target_stay_types = Column(ARRAY(String), nullable=True)
    target_gender = Column(ARRAY(String), nullable=True)  # ["Male", "Female", "Other"] or null = all
    is_highlighted = Column(Boolean, default=False, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    authority = relationship("Authority", back_populates="authority_updates")
    
    __table_args__ = (
        CheckConstraint(
            "category IN ('Announcement', 'Policy Change', 'Event', 'Maintenance', 'Emergency', 'General')",
            name="check_update_category"
        ),
        CheckConstraint("priority IN ('Low', 'Medium', 'High', 'Urgent')", name="check_update_priority"),
        CheckConstraint(
            "visibility IN ('Department', 'Year', 'Hostel', 'Day Scholar', 'All Students')",
            name="check_update_visibility"
        ),
        Index("idx_authority_update_feed_query", "is_active", "expires_at", "is_pinned", "priority", "created_at"),
        Index("idx_authority_update_visibility", "visibility", "is_active"),
        Index("idx_authority_update_authority", "authority_id", "is_active"),
    )
    
    def __repr__(self):
        return f"<AuthorityUpdate(id={self.id}, title={self.title[:30]}, priority={self.priority})>"


class Vote(Base):
    """Vote model - upvotes/downvotes on complaints"""
    __tablename__ = "votes"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    student_roll_no = Column(String(20), ForeignKey("students.roll_no", ondelete="CASCADE"), nullable=False, index=True)
    vote_type = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    complaint = relationship("Complaint", back_populates="votes")
    student = relationship("Student", back_populates="votes")
    
    __table_args__ = (
        UniqueConstraint("complaint_id", "student_roll_no", name="unique_vote_per_student"),
        CheckConstraint("vote_type IN ('Upvote', 'Downvote')", name="check_vote_type"),
    )
    
    def __repr__(self):
        return f"<Vote(complaint_id={str(self.complaint_id)[:8]}, type={self.vote_type})>"


class StatusUpdate(Base):
    """Status update model - audit trail for complaint status changes"""
    __tablename__ = "status_updates"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    updated_by = Column(BigInteger, ForeignKey("authorities.id", ondelete="SET NULL"), nullable=True)
    old_status = Column(String(50), nullable=False)
    new_status = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    
    # Relationships
    complaint = relationship("Complaint", back_populates="status_updates")
    updated_by_authority = relationship("Authority", back_populates="status_updates")
    
    def __repr__(self):
        return f"<StatusUpdate({self.old_status} → {self.new_status})>"


# ==================== SUPPORT TABLES ====================


class AuthorityRoutingRule(Base):
    """Authority routing rules - complaint routing configuration"""
    __tablename__ = "authority_routing_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("complaint_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=True, index=True)
    authority_id = Column(BigInteger, ForeignKey("authorities.id", ondelete="CASCADE"), nullable=False, index=True)
    priority_level = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    category = relationship("ComplaintCategory", back_populates="routing_rules")
    
    __table_args__ = (
        Index("idx_routing_category_dept", "category_id", "department_id", "is_active"),
    )
    
    def __repr__(self):
        return f"<AuthorityRoutingRule(category_id={self.category_id}, dept_id={self.department_id})>"


class ImageVerificationLog(Base):
    """Image verification log - LLM image relevance check
    
    ✅ FIXED: Removed image_url column (image is in Complaint table)
    ✅ ADDED: llm_response JSONB column for full verification result
    """
    __tablename__ = "image_verification_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # ✅ REMOVED: image_url column (redundant - image is in complaints.image_data)
    
    # Verification results
    is_relevant = Column(Boolean, nullable=False, index=True)
    confidence_score = Column(Float, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # ✅ NEW: Store full LLM response for debugging/analysis
    llm_response = Column(JSONB, nullable=True)
    # Contains: {
    #   "is_relevant": bool,
    #   "confidence": float,
    #   "reason": str,
    #   "detected_objects": [...],
    #   "visible_issues": [...],
    #   "quality_rating": str,
    #   "is_appropriate": bool
    # }
    
    verified_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    
    # Relationships
    complaint = relationship("Complaint", back_populates="image_verification_logs")
    
    __table_args__ = (
        # Index for querying rejected images
        Index("idx_image_verification_rejected", "is_relevant", "verified_at", postgresql_where=(Column("is_relevant") == False)),
    )
    
    def __repr__(self):
        return f"<ImageVerificationLog(relevant={self.is_relevant}, confidence={self.confidence_score})>"


class SpamBlacklist(Base):
    """Spam blacklist - tracks students flagged for spam"""
    __tablename__ = "spam_blacklist"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    student_roll_no = Column(String(20), ForeignKey("students.roll_no", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    spam_count = Column(Integer, default=1, nullable=False)
    is_permanent = Column(Boolean, default=False, nullable=False)
    blacklisted_by = Column(BigInteger, ForeignKey("authorities.id", ondelete="SET NULL"), nullable=True)
    blacklisted_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    student = relationship("Student", back_populates="spam_entries")
    blacklisted_by_authority = relationship("Authority", back_populates="spam_blacklist_entries")
    
    __table_args__ = (
        Index("idx_spam_active", "student_roll_no", "is_permanent", "expires_at"),
    )
    
    def __repr__(self):
        return f"<SpamBlacklist(student={self.student_roll_no}, count={self.spam_count})>"


class LLMProcessingLog(Base):
    """LLM processing log - tracks all LLM API calls"""
    __tablename__ = "llm_processing_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_type = Column(String(100), nullable=False, index=True)
    prompt_used = Column(Text, nullable=True)
    llm_response = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    status = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    
    # Relationships
    complaint = relationship("Complaint", back_populates="llm_logs")
    
    __table_args__ = (
        CheckConstraint("status IN ('Success', 'Failed', 'Timeout')", name="check_status_log"),
        Index("idx_llm_operation_status", "operation_type", "status"),
    )
    
    def __repr__(self):
        return f"<LLMProcessingLog(operation={self.operation_type}, status={self.status})>"


class Notification(Base):
    """Notification model - real-time alerts"""
    __tablename__ = "notifications"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    recipient_type = Column(String(50), nullable=False, index=True)
    recipient_id = Column(String(255), nullable=False, index=True)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=True, index=True)
    notification_type = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    complaint = relationship("Complaint", back_populates="notifications")
    
    __table_args__ = (
        CheckConstraint("recipient_type IN ('Student', 'Authority')", name="check_recipient_type"),
        Index("idx_notification_recipient_unread", "recipient_id", "is_read", "created_at"),
    )
    
    def __repr__(self):
        return f"<Notification(type={self.notification_type}, read={self.is_read})>"


class Comment(Base):
    """Comment model - comments on complaints"""
    __tablename__ = "comments"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    complaint_id = Column(UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(String(255), nullable=False, index=True)
    author_type = Column(String(50), nullable=False)
    comment_text = Column(Text, nullable=False)
    is_anonymous = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    complaint = relationship("Complaint", back_populates="comments")
    
    __table_args__ = (
        CheckConstraint("author_type IN ('Student', 'Authority')", name="check_author_type"),
        Index("idx_comment_complaint_created", "complaint_id", "created_at"),
    )
    
    def __repr__(self):
        return f"<Comment(author={self.author_id}, anonymous={self.is_anonymous})>"


class AdminAuditLog(Base):
    """Admin audit log - tracks all admin actions"""
    __tablename__ = "admin_audit_log"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    admin_id = Column(BigInteger, ForeignKey("authorities.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(255), nullable=False, index=True)
    target_type = Column(String(100), nullable=True)
    target_id = Column(String(255), nullable=True)
    changes = Column(JSONB, nullable=True)
    action_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    
    # Relationships
    admin = relationship("Authority", back_populates="admin_audit_logs")
    
    def __repr__(self):
        return f"<AdminAuditLog(action={self.action}, target={self.target_type})>"


# ==================== EXPORT ====================

__all__ = [
    "Base",
    "Department",
    "ComplaintCategory",
    "Student",
    "Authority",
    "Complaint",
    "AuthorityUpdate",
    "Vote",
    "StatusUpdate",
    "AuthorityRoutingRule",
    "ImageVerificationLog",
    "SpamBlacklist",
    "LLMProcessingLog",
    "Notification",
    "Comment",
    "AdminAuditLog",
]
