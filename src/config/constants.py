"""
Fixed constants for CampusVoice application.
Department codes, categories, authority levels, status transitions, etc.
"""

from typing import Dict, List, Any
from enum import Enum
import re


# ==================== DEPARTMENTS ====================

class DepartmentCode(str, Enum):
    """Department code enums"""
    CSE = "CSE"
    ECE = "ECE"
    MECH = "MECH"
    CIVIL = "CIVIL"
    EEE = "EEE"
    IT = "IT"
    BIO = "BIO"
    AERO = "AERO"
    RAA = "RAA"
    EIE = "EIE"
    MBA = "MBA"
    AIDS = "AIDS"
    MTECH_CSE = "MTECH_CSE"
    ENG = "ENG"
    PHY = "PHY"
    CHEM = "CHEM"
    MATH = "MATH"


DEPARTMENTS: List[Dict[str, Any]] = [
    {"code": "CSE", "name": "Computer Science & Engineering", "hod_name": None, "hod_email": None},
    {"code": "ECE", "name": "Electronics & Communication Engineering", "hod_name": None, "hod_email": None},
    {"code": "RAA", "name": "Robotics and Automation", "hod_name": None, "hod_email": None},
    {"code": "MECH", "name": "Mechanical Engineering", "hod_name": None, "hod_email": None},
    {"code": "EEE", "name": "Electrical & Electronics Engineering", "hod_name": None, "hod_email": None},
    {"code": "EIE", "name": "Electronics & Instrumentation Engineering", "hod_name": None, "hod_email": None},
    {"code": "BIO", "name": "Biomedical Engineering", "hod_name": None, "hod_email": None},
    {"code": "AERO", "name": "Aeronautical Engineering", "hod_name": None, "hod_email": None},
    {"code": "CIVIL", "name": "Civil Engineering", "hod_name": None, "hod_email": None},
    {"code": "IT", "name": "Information Technology", "hod_name": None, "hod_email": None},
    {"code": "MBA", "name": "Management Studies", "hod_name": None, "hod_email": None},
    {"code": "AIDS", "name": "Artificial Intelligence and Data Science", "hod_name": None, "hod_email": None},
    {"code": "MTECH_CSE", "name": "M.Tech in Computer Science and Engineering", "hod_name": None, "hod_email": None},
    {"code": "ENG", "name": "English", "hod_name": None, "hod_email": None},
    {"code": "PHY", "name": "Physics", "hod_name": None, "hod_email": None},
    {"code": "CHEM", "name": "Chemistry", "hod_name": None, "hod_email": None},
    {"code": "MATH", "name": "Mathematics", "hod_name": None, "hod_email": None},
]


# ==================== COMPLAINT CATEGORIES ====================

class CategoryName(str, Enum):
    """Complaint category enums"""
    MENS_HOSTEL = "Men's Hostel"
    WOMENS_HOSTEL = "Women's Hostel"
    GENERAL = "General"
    DEPARTMENT = "Department"
    DISCIPLINARY = "Disciplinary Committee"


CATEGORIES: List[Dict[str, Any]] = [
    {
        "name": "Men's Hostel",
        "description": "Men's hostel facilities, cleanliness, room issues, mess complaints, amenities",
        "keywords": ["room", "hostel", "warden", "bed", "hall", "mess", "food", "water", "bathroom", "toilet", "shower", "ac", "fan", "electricity", "men", "boys"],
    },
    {
        "name": "Women's Hostel",
        "description": "Women's hostel facilities, cleanliness, room issues, mess complaints, amenities",
        "keywords": ["room", "hostel", "warden", "bed", "hall", "mess", "food", "water", "bathroom", "toilet", "shower", "ac", "fan", "electricity", "women", "girls", "ladies"],
    },
    {
        "name": "General",
        "description": "Canteen, library, playground, common areas, campus facilities",
        "keywords": ["canteen", "library", "playground", "gate", "parking", "wifi", "common area", "ground", "gym", "cafeteria", "auditorium"],
    },
    {
        "name": "Department",
        "description": "Academic issues, lab facilities, department infrastructure, faculty concerns",
        "keywords": ["lab", "class", "classroom", "exam", "faculty", "professor", "teacher", "assignment", "project", "department", "lecture", "practical"],
    },
    {
        "name": "Disciplinary Committee",
        "description": "Ragging, harassment, bullying, serious violations, safety concerns",
        "keywords": ["ragging", "harassment", "bully", "bullying", "fight", "safety", "threat", "violence", "abuse", "assault", "misbehavior"],
    },
]


# ==================== AUTHORITY TYPES ====================

class AuthorityType(str, Enum):
    """Authority type enums"""
    ADMIN = "Admin"
    ADMIN_OFFICER = "Admin Officer"
    MENS_HOSTEL_WARDEN = "Men's Hostel Warden"
    WOMENS_HOSTEL_WARDEN = "Women's Hostel Warden"
    MENS_HOSTEL_DEPUTY_WARDEN = "Men's Hostel Deputy Warden"
    WOMENS_HOSTEL_DEPUTY_WARDEN = "Women's Hostel Deputy Warden"
    SENIOR_DEPUTY_WARDEN = "Senior Deputy Warden"
    HOD = "HOD"
    DISCIPLINARY_COMMITTEE = "Disciplinary Committee"


AUTHORITY_LEVELS: Dict[str, int] = {
    "Admin": 100,
    "Admin Officer": 50,
    "Disciplinary Committee": 20,
    "Senior Deputy Warden": 15,
    "Men's Hostel Deputy Warden": 10,
    "Women's Hostel Deputy Warden": 10,
    "HOD": 8,
    "Men's Hostel Warden": 5,
    "Women's Hostel Warden": 5,
}

LEVEL_TO_AUTHORITY: Dict[int, str] = {v: k for k, v in AUTHORITY_LEVELS.items()}


# ==================== COMPLAINT STATUS ====================

class ComplaintStatus(str, Enum):
    """Complaint status enums"""
    RAISED = "Raised"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    SPAM = "Spam"


VALID_STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "Raised": ["In Progress", "Resolved", "Spam"],
    "In Progress": ["Resolved", "Spam"],
    "Resolved": ["Closed"],
    "Closed": [],
    "Spam": ["Raised", "In Progress", "Closed"],
}


# ==================== PRIORITY LEVELS ====================

class PriorityLevel(str, Enum):
    """Priority level enums"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


PRIORITY_SCORES: Dict[str, float] = {
    "Low": 10.0,
    "Medium": 50.0,
    "High": 100.0,
    "Critical": 200.0,
}

VOTE_IMPACT_MULTIPLIER: float = 2.0
PRIORITY_AUTO_ESCALATE_THRESHOLD: float = 150.0


# ==================== VISIBILITY LEVELS ====================

class VisibilityLevel(str, Enum):
    """Complaint visibility enums (✅ UPDATED: Department removed)"""
    PRIVATE = "Private"
    PUBLIC = "Public"
    # ✅ REMOVED: DEPARTMENT = "Department" (no longer supported in fully AI-driven system)


# ==================== STUDENT ENUMS ====================

class Gender(str, Enum):
    """Gender enums"""
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class StayType(str, Enum):
    """Stay type enums"""
    HOSTEL = "Hostel"
    DAY_SCHOLAR = "Day Scholar"


class StudentYear(str, Enum):
    """Student year/grade enums"""
    FIRST = "1st Year"
    SECOND = "2nd Year"
    THIRD = "3rd Year"
    FOURTH = "4th Year"


VALID_YEARS: List[str] = ["1st Year", "2nd Year", "3rd Year", "4th Year"]


# ==================== VOTE TYPES ====================

class VoteType(str, Enum):
    """Vote type enums"""
    UPVOTE = "Upvote"
    DOWNVOTE = "Downvote"


# ==================== NOTIFICATION TYPES ====================

class NotificationType(str, Enum):
    """Notification type enums"""
    STATUS_UPDATE = "status_update"
    COMPLAINT_ASSIGNED = "complaint_assigned"
    ESCALATION = "escalation"
    SPAM_ALERT = "spam_alert"
    COMMENT_ADDED = "comment_added"
    VOTE_MILESTONE = "vote_milestone"
    COMPLAINT_RESOLVED = "complaint_resolved"
    COMPLAINT_CLOSED = "complaint_closed"
    AUTHORITY_UPDATE_POSTED = "authority_update_posted"
    URGENT_UPDATE = "urgent_update"


# ==================== LLM OPERATION TYPES ====================

class LLMOperationType(str, Enum):
    """LLM operation type enums"""
    CATEGORIZATION = "categorization"
    REPHRASING = "rephrasing"
    IMAGE_VERIFICATION = "image_verification"
    SPAM_DETECTION = "spam_detection"


# ==================== IMAGE VERIFICATION STATUS ====================

class ImageVerificationStatus(str, Enum):
    """Image verification status enums"""
    PENDING = "Pending"
    VERIFIED = "Verified"
    REJECTED = "Rejected"


# ==================== AUTHORITY ANNOUNCEMENTS ====================

class AnnouncementCategory(str, Enum):
    """Authority announcement category enums"""
    ANNOUNCEMENT = "Announcement"
    NOTICE = "Notice"
    ALERT = "Alert"
    MAINTENANCE = "Maintenance"
    EVENT = "Event"


class AnnouncementPriority(str, Enum):
    """Authority announcement priority enums"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


# ==================== AUTHORITY UPDATES ====================

class UpdatePriority(str, Enum):
    """Authority update priority levels"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


class UpdateVisibility(str, Enum):
    """Authority update visibility levels"""
    DEPARTMENT = "Department"
    YEAR = "Year"
    HOSTEL = "Hostel"
    DAY_SCHOLAR = "Day Scholar"
    ALL_STUDENTS = "All Students"


class UpdateCategory(str, Enum):
    """Authority update categories"""
    ANNOUNCEMENT = "Announcement"
    POLICY_CHANGE = "Policy Change"
    EVENT = "Event"
    MAINTENANCE = "Maintenance"
    EMERGENCY = "Emergency"
    GENERAL = "General"


MAX_UPDATE_LENGTH: int = 5000
MIN_UPDATE_LENGTH: int = 10
UPDATE_EXPIRY_DAYS: int = 30


# ==================== ROUTING RULES ====================

DEFAULT_CATEGORY_ROUTING: Dict[str, str] = {
    "Men's Hostel": "Men's Hostel Warden",
    "Women's Hostel": "Women's Hostel Warden",
    "General": "Admin Officer",
    "Department": "HOD",
    "Disciplinary Committee": "Disciplinary Committee",
}

CROSS_DEPARTMENT_AUTHORITY: str = "Admin Officer"

# Escalation hierarchy:
# Men's Hostel: Warden(s) -> Deputy Warden -> Senior Deputy Warden -> Admin
# Women's Hostel: Warden(s) -> Deputy Warden -> Senior Deputy Warden -> Admin
# Department: HOD -> Admin
# General: Admin Officer -> Admin
ESCALATION_RULES: Dict[str, str] = {
    "Men's Hostel Warden": "Men's Hostel Deputy Warden",
    "Women's Hostel Warden": "Women's Hostel Deputy Warden",
    "Men's Hostel Deputy Warden": "Senior Deputy Warden",
    "Women's Hostel Deputy Warden": "Senior Deputy Warden",
    "Senior Deputy Warden": "Admin",
    "HOD": "Admin",
    "Admin Officer": "Admin",
    "Disciplinary Committee": "Admin",
    "Admin": "Admin",
}


# ==================== RATE LIMITING ====================

RATE_LIMIT_KEYS: Dict[str, str] = {
    "student_complaints": "student:{roll_no}:complaints",
    "student_votes": "student:{roll_no}:votes",
    "student_api": "student:{roll_no}:api",
    "authority_api": "authority:{auth_id}:api",
    "authority_updates": "authority:{auth_id}:updates",
    "global": "global:api",
}


# ==================== SPAM DETECTION ====================

SPAM_KEYWORDS: List[str] = [
    "spam", "test", "testing", "dummy", "fake",
    "xyz", "abc", "123", "asdf", "qwerty",
    "junk", "trash", "nonsense", "gibberish",
]

MIN_COMPLAINT_LENGTH: int = 10
MAX_COMPLAINT_LENGTH: int = 2000

SPAM_DETECTION_THRESHOLDS: Dict[str, int | float] = {
    "repeated_chars": 10,
    "all_caps_threshold": 0.7,
    "word_repetition": 5,
}


# ==================== FILE UPLOAD ====================

MAX_IMAGE_WIDTH: int = 4096
MAX_IMAGE_HEIGHT: int = 4096
IMAGE_QUALITY: int = 85
MAX_IMAGE_SIZE_MB: int = 5
MAX_IMAGES_PER_COMPLAINT: int = 2  # ✅ NEW: Maximum images per complaint

THUMBNAIL_SIZES: Dict[str, tuple] = {
    "small": (150, 150),
    "medium": (300, 300),
    "large": (800, 800),
}

ALLOWED_IMAGE_MIMETYPES: List[str] = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
]


# ==================== PAGINATION ====================

DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100
MIN_PAGE_SIZE: int = 1


# ==================== TIME CONSTANTS ====================

# ✅ FIX: Add the missing constant
ESCALATION_THRESHOLD_DAYS: int = 7  # Auto-escalate after 1 week
AUTO_ESCALATE_HOURS: int = 168  # Same as 7 days in hours

SLA_HOURS: Dict[str, int] = {
    "Low": 168,      # 7 days
    "Medium": 72,    # 3 days
    "High": 24,      # 1 day
    "Critical": 6,   # 6 hours
}

SESSION_TIMEOUT_MINUTES: int = 60
TOKEN_EXPIRATION_SECONDS: int = 604800  # 7 days


# ==================== REGEX PATTERNS ====================

# Email must end with @srec.ac.in for SREC college
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@srec\.ac\.in$')
ROLL_NO_PATTERN = re.compile(r'^\d{11,}$')  # BUG-010: numeric-only, minimum 11 digits (CollegeCode4 + YearJoined2 + DeptCode2 + ClassRoll3+)
PHONE_PATTERN = re.compile(r'^[6-9]\d{9}$')
PASSWORD_PATTERN = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')


# ==================== HTTP STATUS CODES ====================

HTTP_STATUS: Dict[str, int] = {
    "OK": 200,
    "CREATED": 201,
    "ACCEPTED": 202,
    "NO_CONTENT": 204,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "UNPROCESSABLE_ENTITY": 422,
    "TOO_MANY_REQUESTS": 429,
    "INTERNAL_SERVER_ERROR": 500,
    "SERVICE_UNAVAILABLE": 503,
}


# ==================== ERROR CODES ====================

ERROR_CODES: Dict[str, str] = {
    "AUTH_ERROR": "AUTH_001",
    "INVALID_CREDENTIALS": "AUTH_002",
    "TOKEN_EXPIRED": "AUTH_003",
    "INVALID_TOKEN": "AUTH_004",
    "ACCOUNT_INACTIVE": "AUTH_005",
    "UNAUTHORIZED": "AUTHZ_001",
    "INSUFFICIENT_PERMISSIONS": "AUTHZ_002",
    "VALIDATION_ERROR": "VAL_001",
    "DUPLICATE_ENTRY": "VAL_002",
    "RESOURCE_NOT_FOUND": "RES_001",
    "STUDENT_NOT_FOUND": "RES_002",
    "COMPLAINT_NOT_FOUND": "RES_003",
    "AUTHORITY_NOT_FOUND": "RES_004",
    "UPDATE_NOT_FOUND": "RES_005",
    "DEPARTMENT_NOT_FOUND": "RES_006",
    "CATEGORY_NOT_FOUND": "RES_007",
    "INVALID_YEAR": "STUD_006",
    "SPAM_DETECTED": "BIZ_001",
    "BLACKLISTED": "BIZ_002",
    "RATE_LIMIT_EXCEEDED": "BIZ_003",
    "INVALID_STATUS_TRANSITION": "BIZ_004",
    "DUPLICATE_VOTE": "BIZ_005",
    "INVALID_FILE_TYPE": "FILE_001",
    "FILE_TOO_LARGE": "FILE_002",
    "IMAGE_UPLOAD_FAILED": "FILE_003",
    "LLM_SERVICE_ERROR": "EXT_001",
    "DATABASE_ERROR": "EXT_002",
    "INVALID_UPDATE_TYPE": "UPD_001",
    "UPDATE_TOO_LONG": "UPD_002",
    "UPDATE_TOO_SHORT": "UPD_003",
    "UNAUTHORIZED_UPDATE": "UPD_004",
    "UPDATE_EXPIRED": "UPD_005",
}


# ==================== ERROR MESSAGES ====================

ERROR_MESSAGES: Dict[str, str] = {
    "INVALID_CREDENTIALS": "Invalid email or password",
    "STUDENT_NOT_FOUND": "Student not found",
    "AUTHORITY_NOT_FOUND": "Authority not found",
    "COMPLAINT_NOT_FOUND": "Complaint not found",
    "UPDATE_NOT_FOUND": "Authority update not found",
    "DEPARTMENT_NOT_FOUND": "Department not found",
    "CATEGORY_NOT_FOUND": "Category not found",
    "INVALID_YEAR": "Invalid year. Must be one of: 1st Year, 2nd Year, 3rd Year, 4th Year",
    "UNAUTHORIZED": "You are not authorized to perform this action",
    "RATE_LIMIT_EXCEEDED": "Rate limit exceeded. Please try again later",
    "SPAM_DETECTED": "Your complaint has been flagged as spam",
    "BLACKLISTED": "Your account has been temporarily suspended",
    "INVALID_FILE_TYPE": "Invalid file type. Only images are allowed",
    "FILE_TOO_LARGE": f"File size exceeds maximum limit of {MAX_IMAGE_SIZE_MB}MB",
    "IMAGE_UPLOAD_FAILED": "Image upload failed. Please try again",
    "INVALID_STATUS_TRANSITION": "Invalid status transition",
    "DUPLICATE_VOTE": "You have already voted on this complaint",
    "TOKEN_EXPIRED": "Your session has expired. Please login again",
    "INVALID_TOKEN": "Invalid authentication token",
    "ACCOUNT_INACTIVE": "Your account is inactive. Please contact admin",
    "INSUFFICIENT_PERMISSIONS": "You don't have permission to perform this action",
    "VALIDATION_ERROR": "Validation error in submitted data",
    "DUPLICATE_ENTRY": "This entry already exists",
    "LLM_SERVICE_ERROR": "AI service is temporarily unavailable",
    "DATABASE_ERROR": "Database operation failed",
    "INVALID_UPDATE_TYPE": "Invalid update type",
    "UPDATE_TOO_LONG": f"Update text exceeds maximum length of {MAX_UPDATE_LENGTH} characters",
    "UPDATE_TOO_SHORT": f"Update text must be at least {MIN_UPDATE_LENGTH} characters",
    "UNAUTHORIZED_UPDATE": "You are not authorized to post/edit/delete this update",
    "UPDATE_EXPIRED": "This update has expired and cannot be modified",
}


# ==================== SUCCESS MESSAGES ====================

SUCCESS_MESSAGES: Dict[str, str] = {
    "STUDENT_REGISTERED": "Student registered successfully",
    "LOGIN_SUCCESS": "Login successful",
    "COMPLAINT_SUBMITTED": "Complaint submitted successfully",
    "STATUS_UPDATED": "Complaint status updated successfully",
    "VOTE_RECORDED": "Vote recorded successfully",
    "VOTE_REMOVED": "Vote removed successfully",
    "NOTIFICATION_SENT": "Notification sent successfully",
    "PASSWORD_CHANGED": "Password changed successfully",
    "PROFILE_UPDATED": "Profile updated successfully",
    "IMAGE_UPLOADED": "Image uploaded successfully",
    "COMPLAINT_DELETED": "Complaint deleted successfully",
    "AUTHORITY_CREATED": "Authority created successfully",
    "UPDATE_POSTED": "Authority update posted successfully",
    "UPDATE_EDITED": "Authority update edited successfully",
    "UPDATE_DELETED": "Authority update deleted successfully",
}


# ==================== CACHE KEYS ====================

CACHE_KEY_TEMPLATES: Dict[str, str] = {
    "student_profile": "student:profile:{roll_no}",
    "authority_profile": "authority:profile:{id}",
    "complaint": "complaint:{id}",
    "complaint_list": "complaints:list:{filters}",
    "departments": "departments:all",
    "categories": "categories:all",
    "authority_update": "authority_update:{id}",
    "authority_updates_list": "authority_updates:{filters}",
    "student_feed": "student_feed:{roll_no}:{filters}",
    "public_feed": "public_feed:{filters}",
}

CACHE_TTL: Dict[str, int] = {
    "student_profile": 3600,
    "authority_profile": 3600,
    "complaint": 300,
    "complaint_list": 60,
    "departments": 86400,
    "categories": 86400,
    "authority_update": 600,
    "authority_updates_list": 300,
    "student_feed": 180,
    "public_feed": 180,
}


# ==================== WEBSOCKET EVENTS ====================

WS_EVENTS: Dict[str, str] = {
    "CONNECT": "connect",
    "DISCONNECT": "disconnect",
    "COMPLAINT_UPDATE": "complaint_update",
    "NEW_NOTIFICATION": "new_notification",
    "STATUS_CHANGE": "status_change",
    "NEW_COMMENT": "new_comment",
    "VOTE_UPDATE": "vote_update",
    "PING": "ping",
    "PONG": "pong",
    "NEW_AUTHORITY_UPDATE": "new_authority_update",
    "UPDATE_EDITED": "update_edited",
    "UPDATE_DELETED": "update_deleted",
}


# ==================== DATE FORMATS ====================

DATE_FORMATS: Dict[str, str] = {
    "ISO": "%Y-%m-%dT%H:%M:%S",
    "DATE_ONLY": "%Y-%m-%d",
    "TIME_ONLY": "%H:%M:%S",
    "DISPLAY": "%d %b %Y, %I:%M %p",
    "FILENAME": "%Y%m%d_%H%M%S",
}


# ==================== HELPER FUNCTIONS ====================

def get_priority_from_score(score: float) -> str:
    """Get priority level from score"""
    if score >= PRIORITY_SCORES["Critical"]:
        return "Critical"
    elif score >= PRIORITY_SCORES["High"]:
        return "High"
    elif score >= PRIORITY_SCORES["Medium"]:
        return "Medium"
    else:
        return "Low"


def is_valid_status_transition(current: str, new: str) -> bool:
    """Check if status transition is valid"""
    return new in VALID_STATUS_TRANSITIONS.get(current, [])


def is_valid_year(year: str) -> bool:
    """Check if student year is valid"""
    return year in VALID_YEARS


def get_authority_level(authority_type: str) -> int:
    """Get authority level from authority type"""
    return AUTHORITY_LEVELS.get(authority_type, 0)


def can_escalate_to(from_authority: str, to_authority: str) -> bool:
    """Check if complaint can be escalated from one authority to another"""
    from_level = get_authority_level(from_authority)
    to_level = get_authority_level(to_authority)
    return to_level > from_level


# ==================== EXPORT ====================

__all__ = [
    # Enums
    "DepartmentCode",
    "CategoryName",
    "AuthorityType",
    "ComplaintStatus",
    "PriorityLevel",
    "VisibilityLevel",
    "Gender",
    "StayType",
    "StudentYear",
    "VoteType",
    "NotificationType",
    "LLMOperationType",
    "ImageVerificationStatus",
    "AnnouncementCategory",
    "AnnouncementPriority",
    "UpdatePriority",
    "UpdateVisibility",
    "UpdateCategory",
    # Lists
    "DEPARTMENTS",
    "CATEGORIES",
    "SPAM_KEYWORDS",
    "VALID_YEARS",
    "ALLOWED_IMAGE_MIMETYPES",
    # Dicts
    "AUTHORITY_LEVELS",
    "LEVEL_TO_AUTHORITY",
    "VALID_STATUS_TRANSITIONS",
    "PRIORITY_SCORES",
    "DEFAULT_CATEGORY_ROUTING",
    "ESCALATION_RULES",
    "SLA_HOURS",
    "ERROR_MESSAGES",
    "SUCCESS_MESSAGES",
    "ERROR_CODES",
    "HTTP_STATUS",
    "CACHE_KEY_TEMPLATES",
    "CACHE_TTL",
    "WS_EVENTS",
    "DATE_FORMATS",
    "RATE_LIMIT_KEYS",
    "SPAM_DETECTION_THRESHOLDS",
    "THUMBNAIL_SIZES",
    # Constants
    "VOTE_IMPACT_MULTIPLIER",
    "PRIORITY_AUTO_ESCALATE_THRESHOLD",
    "MIN_COMPLAINT_LENGTH",
    "MAX_COMPLAINT_LENGTH",
    "MAX_UPDATE_LENGTH",
    "MIN_UPDATE_LENGTH",
    "UPDATE_EXPIRY_DAYS",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "MIN_PAGE_SIZE",
    "ESCALATION_THRESHOLD_DAYS",  # ✅ ADD THIS
    "AUTO_ESCALATE_HOURS",
    "MAX_IMAGE_WIDTH",
    "MAX_IMAGE_HEIGHT",
    "IMAGE_QUALITY",
    "MAX_IMAGE_SIZE_MB",
    "MAX_IMAGES_PER_COMPLAINT",  # ✅ ADD THIS
    "SESSION_TIMEOUT_MINUTES",
    "TOKEN_EXPIRATION_SECONDS",
    "CROSS_DEPARTMENT_AUTHORITY",
    # Patterns
    "EMAIL_PATTERN",
    "ROLL_NO_PATTERN",
    "PHONE_PATTERN",
    "PASSWORD_PATTERN",
    # Helper Functions
    "get_priority_from_score",
    "is_valid_status_transition",
    "is_valid_year",
    "get_authority_level",
    "can_escalate_to",
]
