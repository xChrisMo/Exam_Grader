"""Enhanced Authentication and Authorization System for Exam Grader Application.

This module provides comprehensive user authentication, role-based access control,
and session security management.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from utils.logger import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

try:
    from src.exceptions.application_errors import (
        AuthenticationError,
        AuthorizationError,
    )
except ImportError:

    class AuthenticationError(Exception):
        pass

    class AuthorizationError(Exception):
        pass

try:
    from flask import g, request, session
except ImportError:

    class UserMixin:
        pass

    request = None
    session = {}
    g = type("obj", (object,), {})()

class UserRole(Enum):
    """User roles with hierarchical permissions."""

    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

    @classmethod
    def get_hierarchy(cls) -> Dict[str, int]:
        """Get role hierarchy levels."""
        return {
            cls.STUDENT.value: 1,
            cls.INSTRUCTOR.value: 2,
            cls.ADMIN.value: 3,
            cls.SUPER_ADMIN.value: 4,
        }

    def has_permission_level(self, required_role: "UserRole") -> bool:
        """Check if this role has required permission level."""
        hierarchy = self.get_hierarchy()
        return hierarchy.get(self.value, 0) >= hierarchy.get(required_role.value, 0)

class Permission(Enum):
    """System permissions."""

    # File operations
    UPLOAD_FILE = "upload_file"
    DOWNLOAD_FILE = "download_file"
    DELETE_FILE = "delete_file"

    # Exam operations
    CREATE_EXAM = "create_exam"
    EDIT_EXAM = "edit_exam"
    DELETE_EXAM = "delete_exam"
    GRADE_EXAM = "grade_exam"
    VIEW_GRADES = "view_grades"

    # User management
    CREATE_USER = "create_user"
    EDIT_USER = "edit_user"
    DELETE_USER = "delete_user"
    VIEW_USERS = "view_users"

    # System administration
    VIEW_LOGS = "view_logs"
    SYSTEM_CONFIG = "system_config"
    BACKUP_RESTORE = "backup_restore"

@dataclass
class UserSession:
    """User session information."""

    user_id: str
    username: str
    role: UserRole
    permissions: Set[Permission]
    session_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: str
    user_agent: str
    is_active: bool = True
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session is expired."""
        if not self.is_active:
            return True

        timeout = timedelta(minutes=timeout_minutes)
        return datetime.now(timezone.utc) - self.last_activity > timeout

    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)

class PasswordPolicy:
    """Password policy enforcement."""

    MIN_LENGTH = 8
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    @classmethod
    def validate_password(cls, password: str) -> Tuple[bool, List[str]]:
        """Validate password against policy.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Length check
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")

        if len(password) > cls.MAX_LENGTH:
            errors.append(
                f"Password must be no more than {cls.MAX_LENGTH} characters long"
            )

        # Character requirements
        if cls.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")

        if cls.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")

        if cls.REQUIRE_DIGITS and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")

        if cls.REQUIRE_SPECIAL and not any(c in cls.SPECIAL_CHARS for c in password):
            errors.append(
                f"Password must contain at least one special character: {cls.SPECIAL_CHARS}"
            )

        # Common password check
        if cls._is_common_password(password):
            errors.append(
                "Password is too common, please choose a more secure password"
            )

        return len(errors) == 0, errors

    @classmethod
    def _is_common_password(cls, password: str) -> bool:
        """Check if password is in common passwords list."""
        common_passwords = {
            "password",
            "123456",
            "password123",
            "admin",
            "qwerty",
            "letmein",
            "welcome",
            "monkey",
            "1234567890",
            "abc123",
        }
        return password.lower() in common_passwords

class PasswordHasher:
    """Secure password hashing using PBKDF2."""

    ITERATIONS = 100000
    SALT_LENGTH = 32
    HASH_LENGTH = 64

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash password with salt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        salt = secrets.token_bytes(cls.SALT_LENGTH)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            cls.ITERATIONS,
            dklen=cls.HASH_LENGTH,
        )

        # Combine salt and hash
        combined = salt + password_hash
        return combined.hex()

    @classmethod
    def verify_password(cls, password: str, hashed_password: str) -> bool:
        """Verify password against hash.

        Args:
            password: Plain text password
            hashed_password: Stored hash

        Returns:
            True if password matches
        """
        try:
            # Extract salt and hash
            combined = bytes.fromhex(hashed_password)
            salt = combined[: cls.SALT_LENGTH]
            stored_hash = combined[cls.SALT_LENGTH :]

            # Hash provided password with same salt
            password_hash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                cls.ITERATIONS,
                dklen=cls.HASH_LENGTH,
            )

            # Constant-time comparison
            return secrets.compare_digest(password_hash, stored_hash)

        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False

class RolePermissionManager:
    """Manage role-based permissions."""

    # Default role permissions
    DEFAULT_PERMISSIONS = {
        UserRole.STUDENT: {
            Permission.UPLOAD_FILE,
            Permission.DOWNLOAD_FILE,
            Permission.VIEW_GRADES,
        },
        UserRole.INSTRUCTOR: {
            Permission.UPLOAD_FILE,
            Permission.DOWNLOAD_FILE,
            Permission.DELETE_FILE,
            Permission.CREATE_EXAM,
            Permission.EDIT_EXAM,
            Permission.GRADE_EXAM,
            Permission.VIEW_GRADES,
        },
        UserRole.ADMIN: {
            Permission.UPLOAD_FILE,
            Permission.DOWNLOAD_FILE,
            Permission.DELETE_FILE,
            Permission.CREATE_EXAM,
            Permission.EDIT_EXAM,
            Permission.DELETE_EXAM,
            Permission.GRADE_EXAM,
            Permission.VIEW_GRADES,
            Permission.CREATE_USER,
            Permission.EDIT_USER,
            Permission.VIEW_USERS,
            Permission.VIEW_LOGS,
        },
        UserRole.SUPER_ADMIN: set(Permission),  # All permissions
    }

    @classmethod
    def get_role_permissions(cls, role: UserRole) -> Set[Permission]:
        """Get permissions for a role.

        Args:
            role: User role

        Returns:
            Set of permissions
        """
        return cls.DEFAULT_PERMISSIONS.get(role, set())

    @classmethod
    def has_permission(cls, role: UserRole, permission: Permission) -> bool:
        """Check if role has specific permission.

        Args:
            role: User role
            permission: Required permission

        Returns:
            True if role has permission
        """
        role_permissions = cls.get_role_permissions(role)
        return permission in role_permissions

class AuthenticationManager:
    """Manage user authentication and sessions."""

    def __init__(
        self,
        session_timeout_minutes: int = 30,
        max_failed_attempts: int = 5,
        lockout_duration_minutes: int = 15,
    ):
        """Initialize authentication manager.

        Args:
            session_timeout_minutes: Session timeout in minutes
            max_failed_attempts: Maximum failed login attempts
            lockout_duration_minutes: Account lockout duration in minutes
        """
        self.session_timeout = session_timeout_minutes
        self.max_failed_attempts = max_failed_attempts
        self.lockout_duration = lockout_duration_minutes
        self.active_sessions: Dict[str, UserSession] = {}
        self.failed_attempts: Dict[str, List[datetime]] = {}

        logger.info("Authentication manager initialized")

    def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Tuple[bool, Optional[str], Optional[UserSession]]:
        """Authenticate user credentials.

        Args:
            username: Username
            password: Password
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Tuple of (success, error_message, user_session)
        """
        try:
            if self._is_account_locked(username):
                logger.warning(f"Authentication attempt for locked account: {username}")
                return (
                    False,
                    "Account is temporarily locked due to too many failed attempts",
                    None,
                )

            # Validate credentials (this would typically query a database)
            user_data = self._get_user_data(username)
            if not user_data:
                self._record_failed_attempt(username)
                return False, "Invalid username or password", None

            # Verify password
            if not PasswordHasher.verify_password(password, user_data["password_hash"]):
                self._record_failed_attempt(username)
                logger.warning(f"Failed authentication attempt for user: {username}")
                return False, "Invalid username or password", None

            # Clear failed attempts on successful login
            self._clear_failed_attempts(username)

            # Create user session
            session_id = self._generate_session_id()
            user_role = UserRole(user_data["role"])
            permissions = RolePermissionManager.get_role_permissions(user_role)

            user_session = UserSession(
                user_id=user_data["user_id"],
                username=username,
                role=user_role,
                permissions=permissions,
                session_id=session_id,
                created_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                ip_address=ip_address or "unknown",
                user_agent=user_agent or "unknown",
            )

            # Store session
            self.active_sessions[session_id] = user_session

            logger.info(f"User authenticated successfully: {username}")
            return True, None, user_session

        except Exception as e:
            logger.error(f"Error during authentication for {username}: {str(e)}")
            return False, "Authentication failed due to system error", None

    def validate_session(self, session_id: str) -> Tuple[bool, Optional[UserSession]]:
        """Validate user session.

        Args:
            session_id: Session identifier

        Returns:
            Tuple of (is_valid, user_session)
        """
        try:
            user_session = self.active_sessions.get(session_id)
            if not user_session:
                return False, None

            if user_session.is_expired(self.session_timeout):
                self._invalidate_session(session_id)
                return False, None

            if user_session.is_locked():
                self._invalidate_session(session_id)
                return False, None

            # Update activity
            user_session.update_activity()

            return True, user_session

        except Exception as e:
            logger.error(f"Error validating session {session_id}: {str(e)}")
            return False, None

    def logout_user(self, session_id: str) -> bool:
        """Logout user and invalidate session.

        Args:
            session_id: Session identifier

        Returns:
            True if logout successful
        """
        try:
            user_session = self.active_sessions.get(session_id)
            if user_session:
                logger.info(f"User logged out: {user_session.username}")

            return self._invalidate_session(session_id)

        except Exception as e:
            logger.error(f"Error during logout for session {session_id}: {str(e)}")
            return False

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = []

        for session_id, user_session in self.active_sessions.items():
            if user_session.is_expired(self.session_timeout):
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self._invalidate_session(session_id)

        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        return len(expired_sessions)

    def _get_user_data(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user data from storage.

        Args:
            username: Username

        Returns:
            User data dictionary or None
        """
        try:
            from src.database.models import User

            user = User.query.filter_by(username=username).first()

            if user:
                return {
                    "user_id": user.id,
                    "username": user.username,
                    "password_hash": user.password_hash,
                    "role": "admin" if user.username == "admin" else "user",
                    "email": user.email,
                    "is_active": user.is_active,
                    "failed_attempts": user.failed_login_attempts,
                    "locked_until": user.locked_until,
                }

            return None

        except Exception as e:
            logger.error(f"Error retrieving user data: {str(e)}")
            return None

    def _generate_session_id(self) -> str:
        """Generate secure session ID.

        Returns:
            Session ID string
        """
        return secrets.token_urlsafe(32)

    def _invalidate_session(self, session_id: str) -> bool:
        """Invalidate user session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was invalidated
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            return True
        return False

    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts.

        Args:
            username: Username

        Returns:
            True if account is locked
        """
        attempts = self.failed_attempts.get(username, [])
        if len(attempts) < self.max_failed_attempts:
            return False

        latest_attempt = max(attempts)
        lockout_until = latest_attempt + timedelta(minutes=self.lockout_duration)

        if datetime.now(timezone.utc) > lockout_until:
            # Lockout period expired, clear attempts
            self._clear_failed_attempts(username)
            return False

        return True

    def _record_failed_attempt(self, username: str):
        """Record failed authentication attempt.

        Args:
            username: Username
        """
        if username not in self.failed_attempts:
            self.failed_attempts[username] = []

        self.failed_attempts[username].append(datetime.now(timezone.utc))

        # Keep only recent attempts
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        self.failed_attempts[username] = [
            attempt
            for attempt in self.failed_attempts[username]
            if attempt > cutoff_time
        ]

    def _clear_failed_attempts(self, username: str):
        """Clear failed attempts for user.

        Args:
            username: Username
        """
        if username in self.failed_attempts:
            del self.failed_attempts[username]

def require_auth(f):
    """Decorator to require authentication."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = session.get("session_id") or request.headers.get("X-Session-ID")

        if not session_id:
            raise AuthenticationError("Authentication required")

        # Validate session
        auth_manager = get_auth_manager()
        is_valid, user_session = auth_manager.validate_session(session_id)

        if not is_valid:
            raise AuthenticationError("Invalid or expired session")

        # Store user session in Flask g object
        g.current_user = user_session

        return f(*args, **kwargs)

    return decorated_function

def require_permission(permission: Permission):
    """Decorator to require specific permission."""

    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user_session = g.current_user

            if permission not in user_session.permissions:
                raise AuthorizationError(f"Permission required: {permission.value}")

            return f(*args, **kwargs)

        return decorated_function

    return decorator

def require_role(role: UserRole):
    """Decorator to require specific role or higher."""

    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user_session = g.current_user

            if not user_session.role.has_permission_level(role):
                raise AuthorizationError(f"Role required: {role.value} or higher")

            return f(*args, **kwargs)

        return decorated_function

    return decorator

# Global authentication manager instance
auth_manager = None

def init_auth_manager(
    session_timeout: int = 30, max_failed_attempts: int = 5, lockout_duration: int = 15
) -> AuthenticationManager:
    """Initialize global authentication manager.

    Args:
        session_timeout: Session timeout in minutes
        max_failed_attempts: Maximum failed login attempts
        lockout_duration: Account lockout duration in minutes

    Returns:
        AuthenticationManager instance
    """
    global auth_manager
    auth_manager = AuthenticationManager(
        session_timeout, max_failed_attempts, lockout_duration
    )
    return auth_manager

def get_auth_manager() -> Optional[AuthenticationManager]:
    """Get global authentication manager instance.

    Returns:
        AuthenticationManager instance or None
    """
    return auth_manager
