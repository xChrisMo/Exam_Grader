"""
Secure Session Management System for Exam Grader Application.

This module provides secure session management with encryption, proper
session invalidation, and security features to replace Flask's default
session handling.
"""

import base64
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Import Flask request with fallback
try:
    from flask import request, has_request_context
except ImportError:
    request = None
    has_request_context = lambda: False
from flask import g, request
from sqlalchemy.orm import sessionmaker

# Import logger with fallback
try:
    from utils.logger import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

# Import database models with fallback
try:
    from src.database.models import Session as SessionModel
    from src.database.models import User, db
except ImportError:
    # Fallback for when models aren't available yet
    db = None
    SessionModel = None
    User = None


class SessionEncryption:
    """Handles session data encryption and decryption."""

    def __init__(self, secret_key: str):
        """Initialize encryption with secret key."""
        self.secret_key = secret_key.encode()
        self._fernet = None

    def _get_fernet(self) -> Fernet:
        """Get or create Fernet instance for encryption."""
        if self._fernet is None:
            # Derive key from secret
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"exam_grader_salt",  # In production, use random salt per session
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.secret_key))
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt_data(self, data: Dict[str, Any]) -> bytes:
        """Encrypt session data."""
        try:
            json_data = json.dumps(data, default=str).encode()
            return self._get_fernet().encrypt(json_data)
        except Exception as e:
            logger.error(f"Failed to encrypt session data: {str(e)}")
            raise

    def decrypt_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt session data."""
        try:
            decrypted_data = self._get_fernet().decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt session data: {str(e)}")
            return {}


class SecureSessionManager:
    """
    Secure session manager with database storage and encryption.

    Features:
    - Encrypted session data storage
    - Automatic session expiration
    - Session invalidation
    - IP address validation
    - User agent validation
    - Session hijacking protection
    """

    def __init__(self, secret_key: str, session_timeout: int = 3600):
        """
        Initialize secure session manager.

        Args:
            secret_key: Secret key for encryption
            session_timeout: Session timeout in seconds
        """
        self.session_timeout = session_timeout
        self.encryption = SessionEncryption(secret_key)
        self._current_session = None

    def create_session(self, user_id: str, session_data: Dict[str, Any] = None, remember_me: bool = False) -> str:
        """
        Create a new secure session.

        Args:
            user_id: User ID to associate with session
            session_data: Initial session data

        Returns:
            Session ID
        """
        try:
            # Generate secure session ID
            session_id = self._generate_session_id()

            # Prepare session data
            if session_data is None:
                session_data = {}

            session_data.update(
                {
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "last_accessed": datetime.utcnow().isoformat(),
                }
            )

            # Encrypt session data
            encrypted_data = self.encryption.encrypt_data(session_data)

            # Get client information
            ip_address = self._get_client_ip()
            user_agent = self._get_user_agent()

            # Create session record
            session = SessionModel(
                id=session_id,
                user_id=user_id,
                data=encrypted_data,
                expires_at=datetime.utcnow() + timedelta(seconds=self.session_timeout if not remember_me else 86400),
                ip_address=ip_address,
                user_agent=user_agent,
                is_active=True,
            )

            db.session.add(session)
            db.session.commit()

            logger.info(f"Created secure session {session_id} for user {user_id}")
            return session_id

        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            db.session.rollback()
            raise

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by session ID with full validation.

        Args:
            session_id: Session ID

        Returns:
            Session data or None if invalid/expired
        """
        try:
            if not session_id:
                return None

            # Get session from database
            session = SessionModel.query.filter_by(
                id=session_id,
                is_active=True
            ).first()

            if not session:
                return None

            # Check expiration
            if session.is_expired():
                self.invalidate_session(session_id)
                return None

            # Validate client information
            if not self._validate_client_info(session):
                self.invalidate_session(session_id)
                return None

            # Return decrypted session data
            return self.encryption.decrypt_data(session.data)
            # Get session from database
            session = SessionModel.query.filter_by(
                id=session_id, is_active=True
            ).first()
            # Get session from database
            session = SessionModel.query.filter_by(
                id=session_id, is_active=True
            ).first()
            # Get session from database
            session = SessionModel.query.filter_by(
                id=session_id, is_active=True
            ).first()

            if not session:
                return None

            # Check if session is expired
            if session.is_expired():
                self.invalidate_session(session_id)
                return None

            # Validate client information
            if not self._validate_client_info(session):
                logger.warning(f"Session {session_id} failed client validation")
                self.invalidate_session(session_id)
                return None

            # Decrypt and return session data
            session_data = self.encryption.decrypt_data(session.data)

            # Update last accessed time
            session.last_accessed = datetime.utcnow()
            db.session.commit()

            self._current_session = session
            return session_data

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {str(e)}")
            return None

    def update_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """
        Update session data.

        Args:
            session_id: Session ID
            session_data: Updated session data

        Returns:
            True if successful
        """
        try:
            session = SessionModel.query.filter_by(
                id=session_id, is_active=True
            ).first()

            if not session or session.is_expired():
                return False

            # Update session data
            session_data["last_accessed"] = datetime.utcnow().isoformat()
            encrypted_data = self.encryption.encrypt_data(session_data)

            session.data = encrypted_data
            session.last_accessed = datetime.utcnow()

            db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {str(e)}")
            db.session.rollback()
            return False

    def extend_session(self, session_id: str, duration_seconds: int = None) -> bool:
        """
        Extend session expiration time.

        Args:
            session_id: Session ID
            duration_seconds: Extension duration (uses default timeout if None)

        Returns:
            True if successful
        """
        try:
            session = SessionModel.query.filter_by(
                id=session_id, is_active=True
            ).first()

            if not session:
                return False

            if duration_seconds is None:
                duration_seconds = self.session_timeout

            session.extend_session(duration_seconds)
            db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to extend session {session_id}: {str(e)}")
            db.session.rollback()
            return False

    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a session.

        Args:
            session_id: Session ID to invalidate

        Returns:
            True if successful
        """
        try:
            session = SessionModel.query.filter_by(id=session_id).first()

            if session:
                session.invalidate()
                db.session.commit()
                logger.info(f"Invalidated session {session_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to invalidate session {session_id}: {str(e)}")
            db.session.rollback()
            return False

    def invalidate_user_sessions(
        self, user_id: str, except_session_id: str = None
    ) -> int:
        """
        Invalidate all sessions for a user.

        Args:
            user_id: User ID
            except_session_id: Session ID to keep active

        Returns:
            Number of sessions invalidated
        """
        try:
            query = SessionModel.query.filter_by(user_id=user_id, is_active=True)

            if except_session_id:
                query = query.filter(SessionModel.id != except_session_id)

            sessions = query.all()
            count = 0

            for session in sessions:
                session.invalidate()
                count += 1

            db.session.commit()

            if count > 0:
                logger.info(f"Invalidated {count} sessions for user {user_id}")

            return count

        except Exception as e:
            logger.error(f"Failed to invalidate user sessions for {user_id}: {str(e)}")
            db.session.rollback()
            return 0

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        try:
            expired_sessions = SessionModel.query.filter(
                SessionModel.expires_at < datetime.utcnow()
            ).all()

            count = 0
            for session in expired_sessions:
                db.session.delete(session)
                count += 1

            db.session.commit()

            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")

            return count

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {str(e)}")
            db.session.rollback()
            return 0

    def _generate_session_id(self) -> str:
        """Generate a cryptographically secure session ID."""
        return secrets.token_urlsafe(32)

    def _get_client_ip(self) -> str:
        """Get client IP address."""
        try:
            if request and has_request_context():
                # Handle proxy headers
                if request.headers.get("X-Forwarded-For"):
                    return request.headers.get("X-Forwarded-For").split(",")[0].strip()
                elif request.headers.get("X-Real-IP"):
                    return request.headers.get("X-Real-IP")
                else:
                    return request.remote_addr or "unknown"
        except Exception as e:
            logger.warning(f"Error getting client IP: {str(e)}")
        return "unknown"

    def _get_user_agent(self) -> str:
        """Get client user agent."""
        try:
            if request and has_request_context():
                return request.headers.get("User-Agent", "unknown")[:500]  # Limit length
        except Exception as e:
            logger.warning(f"Error getting user agent: {str(e)}")
        return "unknown"

    def _validate_client_info(self, session: SessionModel) -> bool:
        """
        Validate client information against session.

        Args:
            session: Session model instance

        Returns:
            True if client info matches
        """
        current_ip = self._get_client_ip()
        current_user_agent = self._get_user_agent()

        # Allow IP changes for mobile users but log them
        if session.ip_address != current_ip:
            logger.info(
                f"IP change detected for session {session.id}: {session.ip_address} -> {current_ip}"
            )

        # User agent should remain consistent
        if session.user_agent != current_user_agent:
            logger.warning(f"User agent change detected for session {session.id}")
            return False

        return True

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information without decrypting data.

        Args:
            session_id: Session ID

        Returns:
            Session information
        """
        try:
            session = SessionModel.query.filter_by(id=session_id).first()

            if not session:
                return None

            return {
                "session_id": session.id,
                "user_id": session.user_id,
                "created_at": session.created_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "ip_address": session.ip_address,
                "is_active": session.is_active,
                "is_expired": session.is_expired(),
            }

        except Exception as e:
            logger.error(f"Failed to get session info for {session_id}: {str(e)}")
            return None
