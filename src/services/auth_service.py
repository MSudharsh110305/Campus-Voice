"""
Authentication service for JWT tokens and password hashing.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
        
        Returns:
            Hashed password
        """
        try:
            hashed = pwd_context.hash(password)
            logger.debug("Password hashed successfully")
            return hashed
        except Exception as e:
            logger.error(f"Password hashing error: {e}")
            raise ValueError("Failed to hash password")
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database
        
        Returns:
            True if password matches
        """
        try:
            is_valid = pwd_context.verify(plain_password, hashed_password)
            if is_valid:
                logger.debug("Password verification successful")
            else:
                logger.warning("Password verification failed - incorrect password")
            return is_valid
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    @staticmethod
    def _access_token_expiry(role: str) -> timedelta:
        """Return role-specific access token expiry."""
        if role == "Student":
            return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES_STUDENT)
        else:  # Authority / Admin
            return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES_AUTHORITY)

    @staticmethod
    def _refresh_token_expiry(role: str) -> timedelta:
        """Return role-specific refresh token expiry."""
        if role == "Student":
            return timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS_STUDENT)
        else:  # Authority / Admin
            return timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS_AUTHORITY)

    @staticmethod
    def create_access_token(
        subject: str,
        role: str,
        additional_claims: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.

        Args:
            subject: Token subject (roll_no or authority_id)
            role: User role (Student, Authority, Admin)
            additional_claims: Additional JWT claims
            expires_delta: Token expiration duration (defaults to role-specific short expiry)

        Returns:
            Encoded JWT token
        """
        if expires_delta is None:
            expires_delta = AuthService._access_token_expiry(role)
        
        # ✅ FIXED: Use timezone-aware datetime
        now = datetime.now(timezone.utc)
        expire = now + expires_delta
        
        to_encode = {
            "sub": subject,
            "role": role,
            "exp": expire,
            "iat": now,
            "type": "access"
        }
        
        # Add additional claims
        if additional_claims:
            to_encode.update(additional_claims)
        
        try:
            encoded_jwt = jwt.encode(
                to_encode,
                settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM
            )
            logger.info(f"Access token created for {subject} ({role}), expires in {expires_delta}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Token creation error: {e}")
            raise ValueError(f"Failed to create access token: {str(e)}")
    
    @staticmethod
    def create_refresh_token(
        subject: str,
        role: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token (longer expiration).

        Args:
            subject: Token subject (roll_no or authority_id)
            role: User role (Student, Authority, Admin)
            expires_delta: Token expiration duration (defaults to role-specific long expiry)

        Returns:
            Encoded JWT refresh token
        """
        if expires_delta is None:
            expires_delta = AuthService._refresh_token_expiry(role)
        
        # ✅ Use timezone-aware datetime
        now = datetime.now(timezone.utc)
        expire = now + expires_delta
        
        to_encode = {
            "sub": subject,
            "role": role,
            "exp": expire,
            "iat": now,
            "type": "refresh"
        }
        
        try:
            encoded_jwt = jwt.encode(
                to_encode,
                settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM
            )
            logger.info(f"Refresh token created for {subject} ({role})")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Refresh token creation error: {e}")
            raise ValueError(f"Failed to create refresh token: {str(e)}")
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and verify JWT token.
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            logger.debug(f"Token decoded successfully for subject: {payload.get('sub')}")
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token decode error: Token has expired")
            return None
        except jwt.JWTClaimsError as e:
            logger.warning(f"Token decode error: Invalid claims - {e}")
            return None
        except JWTError as e:
            logger.warning(f"Token decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected token decode error: {e}")
            return None
    
    @staticmethod
    def verify_token_type(token: str, expected_type: str = "access") -> bool:
        """
        Verify token type (access or refresh).
        
        Args:
            token: JWT token string
            expected_type: Expected token type (access or refresh)
        
        Returns:
            True if token type matches
        """
        payload = AuthService.decode_token(token)
        if not payload:
            return False
        
        token_type = payload.get("type", "access")
        return token_type == expected_type
    
    @staticmethod
    def extract_user_info(token: str) -> Optional[Dict[str, Any]]:
        """
        Extract user information from token.
        
        Args:
            token: JWT token string
        
        Returns:
            Dictionary with user info or None if invalid
        """
        payload = AuthService.decode_token(token)
        if not payload:
            return None
        
        return {
            "subject": payload.get("sub"),
            "role": payload.get("role"),
            "issued_at": datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc).isoformat() if payload.get("iat") else None,
            "expires_at": datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc).isoformat() if payload.get("exp") else None,
            "token_type": payload.get("type", "access")
        }
    
    @staticmethod
    def is_token_expired(token: str) -> bool:
        """
        Check if token is expired.
        
        Args:
            token: JWT token string
        
        Returns:
            True if token is expired or invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            exp = payload.get("exp")
            if not exp:
                return True
            
            # ✅ Use timezone-aware datetime
            expiration_time = datetime.fromtimestamp(exp, tz=timezone.utc)
            return datetime.now(timezone.utc) >= expiration_time
            
        except jwt.ExpiredSignatureError:
            return True
        except Exception:
            return True
    
    @staticmethod
    def get_token_expiration_seconds() -> int:
        """
        Get token expiration duration in seconds.
        
        Returns:
            Expiration duration in seconds
        """
        return settings.JWT_EXPIRATION_DAYS * 24 * 60 * 60
    
    @staticmethod
    def get_token_expiration_datetime(token: str) -> Optional[datetime]:
        """
        Get token expiration datetime.
        
        Args:
            token: JWT token string
        
        Returns:
            Expiration datetime or None if invalid
        """
        payload = AuthService.decode_token(token)
        if not payload:
            return None
        
        exp = payload.get("exp")
        if not exp:
            return None
        
        # ✅ Return timezone-aware datetime
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password cannot be empty"
        
        if len(password) < settings.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
        
        if len(password) > 128:
            return False, "Password must not exceed 128 characters"
        
        if not any(char.isdigit() for char in password):
            return False, "Password must contain at least one digit"
        
        if not any(char.isupper() for char in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(char.islower() for char in password):
            return False, "Password must contain at least one lowercase letter"
        
        # Check for spaces (optional - uncomment if needed)
        # if ' ' in password:
        #     return False, "Password cannot contain spaces"
        
        # Optional: Check for special characters
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if hasattr(settings, 'PASSWORD_REQUIRE_SPECIAL') and settings.PASSWORD_REQUIRE_SPECIAL:
            if not any(char in special_chars for char in password):
                return False, "Password must contain at least one special character"
        
        logger.debug("Password strength validation passed")
        return True, None
    
    @staticmethod
    def validate_roll_no_format(roll_no: str) -> Tuple[bool, Optional[str]]:
        """
        Validate roll number format (e.g., 22CS231).
        
        Args:
            roll_no: Roll number to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        import re
        
        if not roll_no:
            return False, "Roll number cannot be empty"
        
        # Expected format: 2 digits (year) + 2 letters (dept) + 3 digits (number)
        # Example: 22CS231, 23EC045
        pattern = r'^[0-9]{2}[A-Z]{2}[0-9]{3}$'
        
        if not re.match(pattern, roll_no.upper()):
            return False, "Invalid roll number format (expected: YYDDnnn, e.g., 22CS231)"
        
        return True, None
    
    @staticmethod
    def validate_email_format(email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email format.
        
        Args:
            email: Email to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        import re
        
        if not email:
            return False, "Email cannot be empty"
        
        # Basic email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            return False, "Invalid email format"
        
        return True, None
    
    @staticmethod
    def generate_temporary_password(length: int = 12) -> str:
        """
        Generate a temporary password for password reset.
        
        Args:
            length: Password length (default: 12)
        
        Returns:
            Random password string
        """
        import secrets
        import string
        
        # Ensure password meets strength requirements
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        
        while True:
            password = ''.join(secrets.choice(alphabet) for _ in range(length))
            
            # Ensure it has at least one of each required character type
            if (any(c.islower() for c in password) and
                any(c.isupper() for c in password) and
                any(c.isdigit() for c in password)):
                
                logger.info("Temporary password generated")
                return password
    
    @staticmethod
    def create_token_pair(
        subject: str,
        role: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Create both access and refresh tokens.
        
        Args:
            subject: Token subject (roll_no or authority_id)
            role: User role (Student, Authority, Admin)
            additional_claims: Additional JWT claims
        
        Returns:
            Dictionary with access_token and refresh_token
        """
        access_token = AuthService.create_access_token(
            subject=subject,
            role=role,
            additional_claims=additional_claims
        )

        refresh_token = AuthService.create_refresh_token(
            subject=subject,
            role=role
        )

        logger.info(f"Token pair created for {subject} ({role})")

        expiry = AuthService._access_token_expiry(role)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(expiry.total_seconds())
        }


# Create global instance
auth_service = AuthService()

__all__ = ["AuthService", "auth_service"]
