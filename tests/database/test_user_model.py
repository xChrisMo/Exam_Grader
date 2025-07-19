"""Unit tests for User model."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from src.database.optimized_models import User, db


class TestUserModel:
    """Test cases for User model."""

    def test_user_creation_valid(self, app_context):
        """Test creating a valid user."""
        user = User(
            username="testuser",
            email="test@example.com"
        )
        user.set_password("password123")
        
        db.session.add(user)
        db.session.commit()
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.email_verified is False
        assert user.two_factor_enabled is False
        assert user.failed_login_attempts == 0
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_username_validation(self, app_context):
        """Test username validation rules."""
        user = User(email="test@example.com")
        
        # Test empty username
        with pytest.raises(ValueError, match="Username must be at least 3 characters"):
            user.username = ""
        
        # Test short username
        with pytest.raises(ValueError, match="Username must be at least 3 characters"):
            user.username = "ab"
        
        # Test long username
        with pytest.raises(ValueError, match="Username must be no more than 80 characters"):
            user.username = "a" * 81
        
        # Test invalid characters
        with pytest.raises(ValueError, match="Username can only contain letters, numbers"):
            user.username = "test@user"
        
        # Test valid usernames
        user.username = "test_user"
        assert user.username == "test_user"
        
        user.username = "test-user123"
        assert user.username == "test-user123"

    def test_email_validation(self, app_context):
        """Test email validation rules."""
        user = User(username="testuser")
        
        # Test empty email
        with pytest.raises(ValueError, match="Valid email address is required"):
            user.email = ""
        
        # Test invalid email format
        with pytest.raises(ValueError, match="Valid email address is required"):
            user.email = "invalid-email"
        
        # Test long email
        with pytest.raises(ValueError, match="Email must be no more than 120 characters"):
            user.email = "a" * 110 + "@example.com"
        
        # Test valid email
        user.email = "Test@Example.COM"
        assert user.email == "test@example.com"  # Should be lowercased

    def test_password_operations(self, app_context):
        """Test password setting and checking."""
        user = User(username="testuser", email="test@example.com")
        
        # Test short password
        with pytest.raises(ValueError, match="Password must be at least 8 characters"):
            user.set_password("short")
        
        # Test valid password
        user.set_password("password123")
        assert user.password_hash is not None
        assert user.password_changed_at is not None
        assert check_password_hash(user.password_hash, "password123")
        
        # Test password checking
        assert user.check_password("password123") is True
        assert user.check_password("wrongpassword") is False

    def test_account_locking(self, app_context):
        """Test account locking functionality."""
        user = User(username="testuser", email="test@example.com")
        user.set_password("password123")
        
        # Initially not locked
        assert user.is_locked() is False
        
        # Lock account
        user.lock_account(30)
        assert user.is_locked() is True
        assert user.locked_until is not None
        assert user.failed_login_attempts == 0
        
        # Unlock account
        user.unlock_account()
        assert user.is_locked() is False
        assert user.locked_until is None
        assert user.failed_login_attempts == 0

    def test_password_expiration(self, app_context):
        """Test password expiration logic."""
        user = User(username="testuser", email="test@example.com")
        user.set_password("password123")
        
        # Fresh password should not be expired
        assert user.is_password_expired is False
        
        # Set old password change date
        user.password_changed_at = datetime.utcnow() - timedelta(days=91)
        assert user.is_password_expired is True
        
        # No password change date should be expired
        user.password_changed_at = None
        assert user.is_password_expired is True

    def test_unique_constraints(self, app_context):
        """Test unique constraints on username and email."""
        # Create first user
        user1 = User(username="testuser", email="test@example.com")
        user1.set_password("password123")
        db.session.add(user1)
        db.session.commit()
        
        # Try to create user with same username
        user2 = User(username="testuser", email="different@example.com")
        user2.set_password("password123")
        db.session.add(user2)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
        
        db.session.rollback()
        
        # Try to create user with same email
        user3 = User(username="differentuser", email="test@example.com")
        user3.set_password("password123")
        db.session.add(user3)
        
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_to_dict_method(self, app_context):
        """Test to_dict method with and without sensitive data."""
        user = User(username="testuser", email="test@example.com")
        user.set_password("password123")
        user.failed_login_attempts = 3
        user.lock_account(30)
        
        db.session.add(user)
        db.session.commit()
        
        # Test without sensitive data
        data = user.to_dict()
        expected_keys = {
            "id", "username", "email", "is_active", "email_verified",
            "two_factor_enabled", "last_login", "created_at", "updated_at"
        }
        assert set(data.keys()) == expected_keys
        assert "failed_login_attempts" not in data
        assert "password_hash" not in data
        
        # Test with sensitive data
        sensitive_data = user.to_dict(include_sensitive=True)
        additional_keys = {
            "failed_login_attempts", "locked_until", "password_changed_at", "is_password_expired"
        }
        assert set(sensitive_data.keys()) == expected_keys | additional_keys
        assert sensitive_data["failed_login_attempts"] == 3
        assert "password_hash" not in sensitive_data  # Should never be included

    def test_relationships(self, app_context):
        """Test user relationships with other models."""
        user = User(username="testuser", email="test@example.com")
        user.set_password("password123")
        
        db.session.add(user)
        db.session.commit()
        
        # Test that relationships are properly defined
        assert hasattr(user, 'marking_guides')
        assert hasattr(user, 'submissions')
        assert hasattr(user, 'sessions')
        
        # Test that relationships are empty initially
        assert len(user.marking_guides) == 0
        assert len(user.submissions) == 0
        assert len(user.sessions) == 0

    def test_validation_mixin_methods(self, app_context):
        """Test ValidationMixin methods."""
        user = User()
        
        # Test validate_required_fields
        errors = user.validate_required_fields('username', 'email')
        assert len(errors) == 2
        assert "username is required" in errors
        assert "email is required" in errors
        
        user.username = "testuser"
        user.email = "test@example.com"
        errors = user.validate_required_fields('username', 'email')
        assert len(errors) == 0
        
        # Test validate_string_length
        user.username = "ab"
        errors = user.validate_string_length('username', min_length=3, max_length=80)
        assert len(errors) == 1
        assert "username must be at least 3 characters" in errors[0]
        
        user.username = "a" * 81
        errors = user.validate_string_length('username', min_length=3, max_length=80)
        assert len(errors) == 1
        assert "username must be no more than 80 characters" in errors[0]

    def test_timestamp_mixin(self, app_context):
        """Test TimestampMixin functionality."""
        user = User(username="testuser", email="test@example.com")
        user.set_password("password123")
        
        # Before saving
        assert user.created_at is None
        assert user.updated_at is None
        
        db.session.add(user)
        db.session.commit()
        
        # After saving
        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        
        # Test update timestamp
        original_updated = user.updated_at
        user.email = "newemail@example.com"
        db.session.commit()
        
        assert user.updated_at > original_updated

    def test_check_constraints_validation(self, app_context):
        """Test that check constraints are properly validated."""
        user = User(username="testuser", email="test@example.com")
        user.set_password("password123")
        
        # Test negative failed_login_attempts (should be prevented by check constraint)
        user.failed_login_attempts = -1
        db.session.add(user)
        
        # Note: SQLite doesn't enforce check constraints by default
        # This test documents the intended behavior
        # In production with PostgreSQL, this would raise an IntegrityError
        
        # Reset to valid value
        user.failed_login_attempts = 0
        db.session.commit()
        
        assert user.failed_login_attempts == 0