"""Pytest configuration and fixtures for database tests."""

import pytest
import tempfile
import os
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from src.database.optimized_models import db
from src.config.unified_config import Config


@pytest.fixture(scope="session")
def app():
    """Create and configure a test Flask application."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'poolclass': StaticPool,
            'pool_pre_ping': True,
            'connect_args': {
                'check_same_thread': False,
            },
        }
    })
    
    # Initialize the database
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    # Clean up the temporary database file
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def app_context(app):
    """Create an application context for each test."""
    with app.app_context():
        yield app
        # Clean up any data created during the test
        db.session.rollback()
        # Clear all tables for the next test
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


@pytest.fixture(scope="function")
def db_session(app_context):
    """Create a database session for each test."""
    connection = db.engine.connect()
    transaction = connection.begin()
    
    # Configure session to use the connection
    session = db.create_scoped_session(
        options={"bind": connection, "binds": {}}
    )
    
    # Make session available to the application
    db.session = session
    
    yield session
    
    # Rollback transaction and close connection
    transaction.rollback()
    connection.close()
    session.remove()


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test runner for the Flask application."""
    return app.test_cli_runner()


class DatabaseTestUtils:
    """Utility class for database testing."""
    
    @staticmethod
    def create_test_user(username="testuser", email="test@example.com", password="password123"):
        """Create a test user."""
        from src.database.optimized_models import User
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def create_test_marking_guide(user, title="Test Guide", filename="test.pdf"):
        """Create a test marking guide."""
        from src.database.optimized_models import MarkingGuide
        
        guide = MarkingGuide(
            user_id=user.id,
            title=title,
            filename=filename,
            file_path=f"/uploads/{filename}",
            file_size=1024,
            file_type="application/pdf"
        )
        db.session.add(guide)
        db.session.commit()
        return guide
    
    @staticmethod
    def create_test_submission(user, marking_guide, student_name="John Doe", student_id="12345"):
        """Create a test submission."""
        from src.database.optimized_models import Submission
        
        submission = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_name=student_name,
            student_id=student_id,
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_size=2048,
            file_type="application/pdf"
        )
        db.session.add(submission)
        db.session.commit()
        return submission


@pytest.fixture
def db_utils():
    """Provide database testing utilities."""
    return DatabaseTestUtils


# Markers for different types of tests
pytestmark = [
    pytest.mark.database,
    pytest.mark.unit
]