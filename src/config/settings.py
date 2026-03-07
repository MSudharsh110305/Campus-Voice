"""
Application settings using Pydantic Settings.
Loads configuration from environment variables with full validation.
"""

from typing import List, Optional, Dict
from pydantic import Field, field_validator, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ==================== APPLICATION ====================
    ENVIRONMENT: str = Field(default="development", description="Application environment")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    APP_NAME: str = Field(default="CampusVoice", description="Application name")
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, ge=1000, le=65535, description="Server port")
    WORKERS: int = Field(default=4, ge=1, description="Number of workers")
    
    # ==================== DATABASE ====================
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string (asyncpg)")
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries")
    DB_POOL_SIZE: int = Field(default=20, ge=1, description="Connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0, description="Max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1, description="Pool timeout (seconds)")
    DB_POOL_RECYCLE: int = Field(default=3600, ge=300, description="Pool recycle time")
    
    # ==================== JWT & SECURITY ====================
    JWT_SECRET_KEY: str = Field(..., min_length=32, description="JWT secret key")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRATION_DAYS: int = Field(default=7, ge=1, description="Token expiration (days) — kept for backward compat")
    PASSWORD_MIN_LENGTH: int = Field(default=8, ge=6, description="Min password length")

    # Role-specific token expiry
    ACCESS_TOKEN_EXPIRE_MINUTES_STUDENT: int = Field(default=30, ge=1, description="Student access token expiry (minutes)")
    REFRESH_TOKEN_EXPIRE_DAYS_STUDENT: int = Field(default=7, ge=1, description="Student refresh token expiry (days)")
    ACCESS_TOKEN_EXPIRE_MINUTES_AUTHORITY: int = Field(default=15, ge=1, description="Authority/Admin access token expiry (minutes)")
    REFRESH_TOKEN_EXPIRE_DAYS_AUTHORITY: int = Field(default=1, ge=1, description="Authority/Admin refresh token expiry (days)")
    
    # ==================== GROQ LLM ====================
    GROQ_API_KEY: str = Field(default="", description="Groq API key (optional; LLM features use fallback logic when empty)")
    LLM_MODEL: str = Field(default="llama-3.1-8b-instant", description="Primary LLM model")
    LLM_FALLBACK_MODEL: Optional[str] = Field(
        default="mixtral-8x7b-32768",
        description="Fallback LLM model"
    )
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI fallback key")
    LLM_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=2.0, description="LLM temperature")
    LLM_MAX_TOKENS: int = Field(default=500, ge=50, le=4000, description="Max tokens")
    LLM_TIMEOUT: int = Field(default=30, ge=5, description="LLM timeout (seconds)")
    LLM_MAX_RETRIES: int = Field(default=3, ge=1, le=10, description="Max retry attempts")
    
    # ==================== CORS ====================
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"], description="CORS origins")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow credentials")
    CORS_ALLOW_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        description="Allowed methods"
    )
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"], description="Allowed headers")
    
    # ==================== RATE LIMITING ====================
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_STUDENT_COMPLAINTS_PER_DAY: int = Field(
        default=5, ge=1, description="Max complaints/day"
    )
    RATE_LIMIT_STUDENT_API_PER_HOUR: int = Field(
        default=100, ge=10, description="Student API calls/hour"
    )
    RATE_LIMIT_AUTHORITY_API_PER_HOUR: int = Field(
        default=500, ge=100, description="Authority API calls/hour"
    )
    RATE_LIMIT_AUTHORITY_UPDATES_PER_DAY: int = Field(
        default=10, ge=1, description="Authority updates/day"
    )
    RATE_LIMIT_GLOBAL_PER_MINUTE: int = Field(
        default=60, ge=10, description="Global rate limit/min"
    )
    
    # ==================== VOTING SYSTEM ====================
    MAX_VOTES_PER_COMPLAINT: int = Field(default=100, ge=10, description="Max votes per complaint")
    VOTE_IMPACT_MULTIPLIER: float = Field(default=2.0, ge=0.1, le=10.0, description="Vote multiplier")
    UPVOTE_POINTS: int = Field(default=5, ge=1, description="Upvote points")
    DOWNVOTE_POINTS: int = Field(default=-3, le=-1, description="Downvote points")
    
    # ==================== PRIORITY CALCULATION ====================
    PRIORITY_LOW_MIN: int = Field(default=0, description="Low priority threshold")
    PRIORITY_MEDIUM_MIN: int = Field(default=50, ge=1, description="Medium priority threshold")
    PRIORITY_HIGH_MIN: int = Field(default=100, ge=50, description="High priority threshold")
    PRIORITY_CRITICAL_MIN: int = Field(default=200, ge=100, description="Critical priority threshold")
    
    # ==================== FILE UPLOAD & STORAGE ====================
    UPLOAD_DIR: str = Field(default="./uploads", description="Upload directory")
    MAX_FILE_SIZE: int = Field(default=5242880, ge=1024, description="Max file size (bytes)")
    ALLOWED_IMAGE_EXTENSIONS: List[str] = Field(
        default=["jpg", "jpeg", "png", "gif", "webp"],
        description="Allowed extensions"
    )
    
    # ✅ NEW: Image storage configuration
    IMAGE_STORAGE_MODE: str = Field(
        default="database",
        description="Storage mode: database, filesystem, or s3"
    )
    IMAGE_ENCODING: str = Field(default="base64", description="Image encoding for DB storage")
    STORE_ORIGINAL_AND_THUMBNAIL: bool = Field(
        default=True,
        description="Store both original and thumbnail"
    )
    MAX_IMAGE_WIDTH: int = Field(default=4096, ge=100, description="Max image width (px)")
    MAX_IMAGE_HEIGHT: int = Field(default=4096, ge=100, description="Max image height (px)")
    IMAGE_QUALITY: int = Field(default=85, ge=1, le=100, description="JPEG quality")
    THUMBNAIL_WIDTH: int = Field(default=300, ge=50, description="Thumbnail width")
    THUMBNAIL_HEIGHT: int = Field(default=300, ge=50, description="Thumbnail height")
    
    # ==================== LOGGING ====================
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="text", description="Log format: json or text")
    LOG_FILE: str = Field(default="./logs/campusvoice.log", description="Log file path")
    
    # ==================== WEBSOCKET ====================
    WEBSOCKET_PING_INTERVAL: int = Field(default=30, ge=10, description="Ping interval (sec)")
    WEBSOCKET_PING_TIMEOUT: int = Field(default=10, ge=5, description="Ping timeout (sec)")
    MAX_WEBSOCKET_CONNECTIONS: int = Field(default=100, ge=10, description="Max WS connections")
    
    # ==================== DATA RETENTION ====================
    DATA_RETENTION_MONTHS: int = Field(default=6, ge=1, description="Data retention (months)")
    AUTO_DELETE_OLD_COMPLAINTS: bool = Field(default=False, description="Auto-delete old complaints")
    
    # ==================== PUSH NOTIFICATIONS (VAPID) ====================
    VAPID_PUBLIC_KEY: str = Field(default="", description="VAPID public key for Web Push")
    VAPID_PRIVATE_KEY: str = Field(default="", description="VAPID private key for Web Push")
    VAPID_CLAIMS_EMAIL: str = Field(default="admin@srec.ac.in", description="VAPID claims email")
    ENABLE_PUSH_NOTIFICATIONS: bool = Field(default=True, description="Enable Web Push notifications")

    # ==================== FEATURE FLAGS ====================
    ENABLE_EMAIL_VERIFICATION: bool = Field(default=False, description="Enable email verification")
    ENABLE_IMAGE_VERIFICATION: bool = Field(default=True, description="Enable image verification")
    ENABLE_SPAM_DETECTION: bool = Field(default=True, description="Enable spam detection")
    ENABLE_AUTO_ESCALATION: bool = Field(default=True, description="Enable auto-escalation")
    ENABLE_WEBSOCKET: bool = Field(default=False, description="Enable WebSocket")
    ENABLE_AUTHORITY_UPDATES: bool = Field(default=True, description="Enable authority updates")
    
    # ==================== EMAIL SETTINGS ====================
    SMTP_HOST: str = Field(default="smtp.gmail.com", description="SMTP host")
    SMTP_PORT: int = Field(default=587, ge=1, le=65535, description="SMTP port")
    SMTP_USER: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP password")
    SMTP_FROM_EMAIL: str = Field(default="noreply@campusvoice.edu", description="From email")
    SMTP_FROM_NAME: str = Field(default="CampusVoice", description="From name")
    
    # ==================== FRONTEND ====================
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend URL")
    
    # ==================== ADMIN SETTINGS ====================
    ADMIN_EMAIL: str = Field(default="admin@srec.ac.in", description="Admin email")
    ADMIN_PASSWORD: str = Field(default="Admin@123456", min_length=8, description="Admin password")
    ADMIN_NAME: str = Field(default="System Administrator", description="Admin name")
    
    # ==================== COMPLAINT SETTINGS ====================
    MIN_COMPLAINT_LENGTH: int = Field(default=10, ge=5, description="Min complaint length")
    MAX_COMPLAINT_LENGTH: int = Field(default=2000, ge=100, description="Max complaint length")
    ESCALATION_THRESHOLD_HOURS: int = Field(default=48, ge=1, description="Auto-escalation hours")
    
    # ==================== SPAM DETECTION ====================
    SPAM_KEYWORDS: List[str] = Field(
        default=["test", "dummy", "fake", "spam"],
        description="Spam keywords"
    )
    MAX_COMPLAINTS_PER_HOUR: int = Field(default=5, ge=1, description="Max complaints/hour")
    SPAM_THRESHOLD_SCORE: float = Field(default=0.7, ge=0.0, le=1.0, description="Spam threshold")
    
    # ==================== PUBLIC FEED SETTINGS ====================
    PUBLIC_FEED_PAGE_SIZE: int = Field(default=20, ge=10, le=100, description="Feed page size")
    PUBLIC_FEED_MAX_AGE_DAYS: int = Field(default=30, ge=1, description="Max feed age (days)")
    SHOW_RESOLVED_IN_FEED: bool = Field(default=True, description="Show resolved in feed")
    SHOW_CLOSED_IN_FEED: bool = Field(default=False, description="Show closed in feed")
    
    # ==================== AUTHORITY UPDATE SETTINGS ====================
    MIN_UPDATE_LENGTH: int = Field(default=10, ge=5, description="Min update length")
    MAX_UPDATE_LENGTH: int = Field(default=5000, ge=100, description="Max update length")
    UPDATE_EXPIRY_DAYS: int = Field(default=30, ge=1, description="Update expiry (days)")
    HIGHLIGHT_URGENT_UPDATES: bool = Field(default=True, description="Highlight urgent updates")
    
    # ==================== REDIS & CACHING ====================
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis URL (required for distributed rate limiting)"
    )
    CACHE_ENABLED: bool = Field(default=False, description="Enable caching")
    CACHE_TTL: int = Field(default=3600, ge=60, description="Cache TTL (seconds)")
    
    # ==================== FIELD VALIDATORS ====================
    
    @field_validator('CORS_ORIGINS', 'CORS_ALLOW_METHODS', 'CORS_ALLOW_HEADERS', 
                     'ALLOWED_IMAGE_EXTENSIONS', 'SPAM_KEYWORDS', mode='before')
    @classmethod
    def parse_list_from_string(cls, v):
        """Parse list from JSON string or comma-separated string"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [item.strip() for item in v.split(',') if item.strip()]
        return v
    
    @field_validator('DATABASE_URL')
    @classmethod
    def validate_database_url(cls, v):
        """Ensure database URL uses asyncpg driver"""
        v = v.strip()
        
        if v.startswith('postgresql+asyncpg://'):
            return v
        if v.startswith('postgresql://'):
            return v.replace('postgresql://', 'postgresql+asyncpg://', 1)
        if v.startswith('postgres://'):
            return v.replace('postgres://', 'postgresql+asyncpg://', 1)
        
        raise ValueError(
            "DATABASE_URL must use PostgreSQL format. "
            "Supported: postgresql+asyncpg://, postgresql://, or postgres://"
        )
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v_upper
    
    @field_validator('LOG_FORMAT')
    @classmethod
    def validate_log_format(cls, v):
        """Validate log format"""
        allowed = ['json', 'text']
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"LOG_FORMAT must be one of {allowed}")
        return v_lower
    
    @field_validator('ENVIRONMENT')
    @classmethod
    def validate_environment(cls, v):
        """Validate environment"""
        allowed = ['development', 'staging', 'production', 'test']
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v_lower
    
    @field_validator('JWT_ALGORITHM')
    @classmethod
    def validate_jwt_algorithm(cls, v):
        """Validate JWT algorithm"""
        allowed = ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"JWT_ALGORITHM must be one of {allowed}")
        return v_upper
    
    @field_validator('IMAGE_STORAGE_MODE')
    @classmethod
    def validate_storage_mode(cls, v):
        """Validate image storage mode"""
        allowed = ['database', 'filesystem', 's3']
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"IMAGE_STORAGE_MODE must be one of {allowed}")
        return v_lower
    
    # ==================== MODEL VALIDATORS ====================
    
    @model_validator(mode='after')
    def validate_cross_field_constraints(self):
        """Validate constraints that depend on multiple fields"""
        
        # Complaint length
        if self.MAX_COMPLAINT_LENGTH <= self.MIN_COMPLAINT_LENGTH:
            raise ValueError(
                f"MAX_COMPLAINT_LENGTH ({self.MAX_COMPLAINT_LENGTH}) must be > "
                f"MIN_COMPLAINT_LENGTH ({self.MIN_COMPLAINT_LENGTH})"
            )
        
        # Update length
        if self.MAX_UPDATE_LENGTH <= self.MIN_UPDATE_LENGTH:
            raise ValueError(
                f"MAX_UPDATE_LENGTH ({self.MAX_UPDATE_LENGTH}) must be > "
                f"MIN_UPDATE_LENGTH ({self.MIN_UPDATE_LENGTH})"
            )
        
        # Priority thresholds ascending
        if not (self.PRIORITY_LOW_MIN < self.PRIORITY_MEDIUM_MIN < 
                self.PRIORITY_HIGH_MIN < self.PRIORITY_CRITICAL_MIN):
            raise ValueError("Priority thresholds must be ascending: LOW < MEDIUM < HIGH < CRITICAL")
        
        # WebSocket timeout < ping interval
        if self.WEBSOCKET_PING_TIMEOUT >= self.WEBSOCKET_PING_INTERVAL:
            raise ValueError(
                f"WEBSOCKET_PING_TIMEOUT ({self.WEBSOCKET_PING_TIMEOUT}) must be < "
                f"WEBSOCKET_PING_INTERVAL ({self.WEBSOCKET_PING_INTERVAL})"
            )
        
        # Pool size warning
        total_connections = self.DB_POOL_SIZE + self.DB_MAX_OVERFLOW
        if total_connections > 100:
            import warnings
            warnings.warn(
                f"Total DB connections ({total_connections}) exceeds 100. "
                "Consider reducing pool_size or max_overflow."
            )
        
        # ✅ NEW: Redis required for production rate limiting
        if self.is_production and self.RATE_LIMIT_ENABLED and not self.REDIS_URL:
            import warnings
            warnings.warn(
                "REDIS_URL not set in production. Rate limiting will use in-memory storage "
                "(not suitable for multi-worker deployments)."
            )
        
        # Thumbnail size validation
        if self.THUMBNAIL_WIDTH > self.MAX_IMAGE_WIDTH or self.THUMBNAIL_HEIGHT > self.MAX_IMAGE_HEIGHT:
            raise ValueError("Thumbnail dimensions must be <= max image dimensions")
        
        return self
    
    # ==================== COMPUTED PROPERTIES ====================
    
    @computed_field
    @property
    def database_config(self) -> Dict:
        """Get database configuration dict"""
        return {
            "url": self.DATABASE_URL,
            "echo": self.DB_ECHO,
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "pool_timeout": self.DB_POOL_TIMEOUT,
            "pool_recycle": self.DB_POOL_RECYCLE,
            "pool_pre_ping": True,
        }
    
    @computed_field
    @property
    def jwt_config(self) -> Dict:
        """Get JWT configuration dict"""
        return {
            "secret_key": self.JWT_SECRET_KEY,
            "algorithm": self.JWT_ALGORITHM,
            "expiration_days": self.JWT_EXPIRATION_DAYS,
        }
    
    @computed_field
    @property
    def llm_config(self) -> Dict:
        """Get LLM configuration dict"""
        return {
            "api_key": self.GROQ_API_KEY,
            "model": self.LLM_MODEL,
            "fallback_model": self.LLM_FALLBACK_MODEL,
            "openai_key": self.OPENAI_API_KEY,
            "temperature": self.LLM_TEMPERATURE,
            "max_tokens": self.LLM_MAX_TOKENS,
            "timeout": self.LLM_TIMEOUT,
            "max_retries": self.LLM_MAX_RETRIES,
        }
    
    @computed_field
    @property
    def priority_scores(self) -> Dict[str, int]:
        """Get priority score thresholds"""
        return {
            "Low": self.PRIORITY_LOW_MIN,
            "Medium": self.PRIORITY_MEDIUM_MIN,
            "High": self.PRIORITY_HIGH_MIN,
            "Critical": self.PRIORITY_CRITICAL_MIN,
        }
    
    @computed_field
    @property
    def rate_limit_config(self) -> Dict:
        """Get rate limit configuration dict"""
        return {
            "enabled": self.RATE_LIMIT_ENABLED,
            "student_complaints_per_day": self.RATE_LIMIT_STUDENT_COMPLAINTS_PER_DAY,
            "student_api_per_hour": self.RATE_LIMIT_STUDENT_API_PER_HOUR,
            "authority_api_per_hour": self.RATE_LIMIT_AUTHORITY_API_PER_HOUR,
            "authority_updates_per_day": self.RATE_LIMIT_AUTHORITY_UPDATES_PER_DAY,
            "global_per_minute": self.RATE_LIMIT_GLOBAL_PER_MINUTE,
        }
    
    @computed_field
    @property
    def public_feed_config(self) -> Dict:
        """Get public feed configuration dict"""
        return {
            "page_size": self.PUBLIC_FEED_PAGE_SIZE,
            "max_age_days": self.PUBLIC_FEED_MAX_AGE_DAYS,
            "show_resolved": self.SHOW_RESOLVED_IN_FEED,
            "show_closed": self.SHOW_CLOSED_IN_FEED,
        }
    
    @computed_field
    @property
    def authority_update_config(self) -> Dict:
        """Get authority update configuration dict"""
        return {
            "min_length": self.MIN_UPDATE_LENGTH,
            "max_length": self.MAX_UPDATE_LENGTH,
            "expiry_days": self.UPDATE_EXPIRY_DAYS,
            "highlight_urgent": self.HIGHLIGHT_URGENT_UPDATES,
        }
    
    @computed_field
    @property
    def image_storage_config(self) -> Dict:
        """Get image storage configuration dict"""
        return {
            "mode": self.IMAGE_STORAGE_MODE,
            "encoding": self.IMAGE_ENCODING,
            "store_thumbnail": self.STORE_ORIGINAL_AND_THUMBNAIL,
            "max_width": self.MAX_IMAGE_WIDTH,
            "max_height": self.MAX_IMAGE_HEIGHT,
            "quality": self.IMAGE_QUALITY,
            "thumbnail_width": self.THUMBNAIL_WIDTH,
            "thumbnail_height": self.THUMBNAIL_HEIGHT,
        }
    
    @computed_field
    @property
    def cors_config(self) -> Dict:
        """Get CORS configuration dict"""
        return {
            "allow_origins": self.CORS_ORIGINS,
            "allow_credentials": self.CORS_ALLOW_CREDENTIALS,
            "allow_methods": self.CORS_ALLOW_METHODS,
            "allow_headers": self.CORS_ALLOW_HEADERS,
        }
    
    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"
    
    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"
    
    @computed_field
    @property
    def is_test(self) -> bool:
        """Check if running in test mode"""
        return self.ENVIRONMENT == "test"
    
    @computed_field
    @property
    def max_file_size_mb(self) -> float:
        """Get max file size in MB"""
        return self.MAX_FILE_SIZE / (1024 * 1024)
    
    # ==================== MODEL CONFIG ====================
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        validate_default=True,
    )


# ==================== GLOBAL INSTANCE ====================

settings = Settings()


# ==================== HELPER FUNCTIONS ====================

def get_settings() -> Settings:
    """Get settings instance (for FastAPI dependency injection)"""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)"""
    return Settings()


__all__ = ["settings", "Settings", "get_settings", "reload_settings"]
