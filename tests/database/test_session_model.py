"""Unit tests for the Session model."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from src.database.optimized_models import db, Session, User


class TestSessionModel:
    """Test cases for the Session model."""
    
    def test_valid_session_creation(self, app_context, db_utils):
        """Test creating a valid session."""
        # Create test user
        user = db_utils.create_test_user()
        
        # Create session
        expires_at = datetime.utcnow() + timedelta(hours=24)
        session = Session(
            user_id=user.id,
            data="encrypted_session_data",
            salt="random_salt_123",
            expires_at=expires_at,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            is_active=True
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Verify session was created
        assert session.id is not None
        assert session.user_id == user.id
        assert session.data == "encrypted_session_data"
        assert session.salt == "random_salt_123"
        assert session.expires_at == expires_at
        assert session.ip_address == "192.168.1.100"
        assert session.is_active is True
    
    def test_session_relationships(self, app_context, db_utils):
        """Test session relationships with user model."""
        user = db_utils.create_test_user()
        
        session = Session(
            user_id=user.id,
            data="test_data",
            salt="test_salt",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Test relationship with user
        assert session.user == user
        assert session in user.sessions
    
    def test_is_expired_method(self, app_context, db_utils):
        """Test the is_expired method."""
        user = db_utils.create_test_user()
        
        # Create expired session
        expired_session = Session(
            user_id=user.id,
            data="expired_data",
            salt="expired_salt",
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
            is_active=True
        )
        
        # Create active session
        active_session = Session(
            user_id=user.id,
            data="active_data",
            salt="active_salt",
            expires_at=datetime.utcnow() + timedelta(hours=1),  # Expires in 1 hour
            is_active=True
        )
        
        db.session.add_all([expired_session, active_session])
        db.session.commit()
        
        # Test expiration check
        assert expired_session.is_expired() is True
        assert active_session.is_expired() is False
    
    def test_extend_session_method(self, app_context, db_utils):
        """Test the extend_session method."""
        user = db_utils.create_test_user()
        
        original_expiry = datetime.utcnow() + timedelta(hours=1)
        session = Session(
            user_id=user.id,
            data="test_data",
            salt="test_salt",
            expires_at=original_expiry,
            is_active=True
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Extend session by 2 hours
        extension_hours = 2
        session.extend_session(extension_hours)
        
        # Verify session was extended
        expected_expiry = original_expiry + timedelta(hours=extension_hours)
        assert session.expires_at >= expected_expiry - timedelta(seconds=1)  # Allow for small time differences
        assert session.expires_at <= expected_expiry + timedelta(seconds=1)
    
    def test_invalidate_method(self, app_context, db_utils):
        """Test the invalidate method."""
        user = db_utils.create_test_user()
        
        session = Session(
            user_id=user.id,
            data="test_data",
            salt="test_salt",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Verify session is initially active
        assert session.is_active is True
        
        # Invalidate session
        session.invalidate()
        
        # Verify session is now inactive
        assert session.is_active is False
    
    def test_to_dict_method(self, app_context, db_utils):
        """Test the to_dict method."""
        user = db_utils.create_test_user()
        
        expires_at = datetime.utcnow() + timedelta(hours=2)
        session = Session(
            user_id=user.id,
            data="serialized_data",
            salt="unique_salt",
            expires_at=expires_at,
            ip_address="10.0.0.1",
            user_agent="Test User Agent",
            is_active=True
        )
        
        db.session.add(session)
        db.session.commit()
        
        session_dict = session.to_dict()
        
        # Verify dictionary contains expected fields
        assert 'id' in session_dict
        assert session_dict['user_id'] == user.id
        assert session_dict['data'] == "serialized_data"
        assert session_dict['salt'] == "unique_salt"
        assert 'expires_at' in session_dict
        assert session_dict['ip_address'] == "10.0.0.1"
        assert session_dict['user_agent'] == "Test User Agent"
        assert session_dict['is_active'] is True
        assert 'created_at' in session_dict
        assert 'updated_at' in session_dict
    
    def test_foreign_key_constraints(self, app_context, db_utils):
        """Test foreign key constraints."""
        # Test invalid user_id
        session = Session(
            user_id=99999,  # Non-existent user
            data="test_data",
            salt="test_salt",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True
        )
        
        db.session.add(session)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
        
        db.session.rollback()
    
    def test_cascade_delete(self, app_context, db_utils):
        """Test cascade delete when user is deleted."""
        user = db_utils.create_test_user()
        
        session = Session(
            user_id=user.id,
            data="test_data",
            salt="test_salt",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True
        )
        
        db.session.add(session)
        db.session.commit()
        
        session_id = session.id
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        # Verify session was also deleted
        deleted_session = db.session.get(Session, session_id)
        assert deleted_session is None
    
    def test_multiple_sessions_per_user(self, app_context, db_utils):
        """Test that a user can have multiple sessions."""
        user = db_utils.create_test_user()
        
        # Create multiple sessions for the same user
        sessions = []
        for i in range(3):
            session = Session(
                user_id=user.id,
                data=f"session_data_{i}",
                salt=f"salt_{i}",
                expires_at=datetime.utcnow() + timedelta(hours=i+1),
                ip_address=f"192.168.1.{100+i}",
                user_agent=f"UserAgent_{i}",
                is_active=True
            )
            sessions.append(session)
            db.session.add(session)
        
        db.session.commit()
        
        # Verify all sessions were created
        user_sessions = Session.query.filter_by(user_id=user.id).all()
        assert len(user_sessions) == 3
        
        # Verify each session has unique data
        session_data = [s.data for s in user_sessions]
        assert len(set(session_data)) == 3  # All unique
    
    def test_session_filtering_by_active_status(self, app_context, db_utils):
        """Test filtering sessions by active status."""
        user = db_utils.create_test_user()
        
        # Create active and inactive sessions
        active_session = Session(
            user_id=user.id,
            data="active_data",
            salt="active_salt",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=True
        )
        
        inactive_session = Session(
            user_id=user.id,
            data="inactive_data",
            salt="inactive_salt",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_active=False
        )
        
        db.session.add_all([active_session, inactive_session])
        db.session.commit()
        
        # Test filtering by active status
        active_sessions = Session.query.filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        inactive_sessions = Session.query.filter_by(
            user_id=user.id,
            is_active=False
        ).all()
        
        assert len(active_sessions) == 1
        assert len(inactive_sessions) == 1
        assert active_sessions[0].data == "active_data"
        assert inactive_sessions[0].data == "inactive_data"
    
    def test_session_filtering_by_expiry(self, app_context, db_utils):
        """Test filtering sessions by expiry date."""
        user = db_utils.create_test_user()
        
        now = datetime.utcnow()
        
        # Create sessions with different expiry times
        expired_session = Session(
            user_id=user.id,
            data="expired_data",
            salt="expired_salt",
            expires_at=now - timedelta(hours=1),  # Expired
            is_active=True
        )
        
        valid_session = Session(
            user_id=user.id,
            data="valid_data",
            salt="valid_salt",
            expires_at=now + timedelta(hours=1),  # Valid
            is_active=True
        )
        
        db.session.add_all([expired_session, valid_session])
        db.session.commit()
        
        # Test filtering by expiry
        valid_sessions = Session.query.filter(
            Session.user_id == user.id,
            Session.expires_at > now,
            Session.is_active == True
        ).all()
        
        expired_sessions = Session.query.filter(
            Session.user_id == user.id,
            Session.expires_at <= now,
            Session.is_active == True
        ).all()
        
        assert len(valid_sessions) == 1
        assert len(expired_sessions) == 1
        assert valid_sessions[0].data == "valid_data"
        assert expired_sessions[0].data == "expired_data"
    
    def test_composite_indexes(self, app_context, db_utils):
        """Test that composite indexes exist and work efficiently."""
        user = db_utils.create_test_user()
        
        # Create multiple sessions with different combinations
        sessions_data = [
            {"ip": "192.168.1.1", "active": True, "hours_offset": 1},
            {"ip": "192.168.1.1", "active": False, "hours_offset": 2},
            {"ip": "192.168.1.2", "active": True, "hours_offset": 3},
            {"ip": "192.168.1.2", "active": False, "hours_offset": 4},
            {"ip": "192.168.1.3", "active": True, "hours_offset": 5},
        ]
        
        for i, data in enumerate(sessions_data):
            session = Session(
                user_id=user.id,
                data=f"session_data_{i}",
                salt=f"salt_{i}",
                expires_at=datetime.utcnow() + timedelta(hours=data["hours_offset"]),
                ip_address=data["ip"],
                user_agent=f"UserAgent_{i}",
                is_active=data["active"]
            )
            db.session.add(session)
        
        db.session.commit()
        
        # Test querying with indexed columns (user_id, is_active)
        active_sessions = Session.query.filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        
        assert len(active_sessions) == 3
        
        # Test querying with IP address index
        ip1_sessions = Session.query.filter_by(
            ip_address="192.168.1.1"
        ).all()
        
        assert len(ip1_sessions) == 2
        
        # Test ordering by expires_at (should use index)
        ordered_sessions = Session.query.filter_by(
            user_id=user.id
        ).order_by(Session.expires_at.asc()).all()
        
        assert len(ordered_sessions) == 5
        # Verify ordering
        for i in range(len(ordered_sessions) - 1):
            assert ordered_sessions[i].expires_at <= ordered_sessions[i + 1].expires_at