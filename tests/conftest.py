"""
Test configuration and fixtures for the Exam Grader test suite.
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from webapp.app_factory import create_app
from src.database.models import db, User
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="session")
def app():
    """Create test application."""
    app = create_app("testing")
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "DATABASE_URL": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key",
        "SUPPRESS_STARTUP_LOGS": True
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def db_session(app):
    """Create database session for testing."""
    with app.app_context():
        yield db.session


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    return create_test_user()


@pytest.fixture
def sample_files():
    """Create sample training files for testing."""
    files = []
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create sample PDF file
        pdf_path = os.path.join(temp_dir, "sample.pdf")
        with open(pdf_path, 'wb') as f:
            f.write(b"%PDF-1.4 sample content")
        files.append({
            'filename': 'sample.pdf',
            'file_path': pdf_path,
            'original_name': 'Sample Training Guide.pdf',
            'size': len(b"%PDF-1.4 sample content"),
            'category': 'qa',
            'extension': '.pdf'
        })
        
        # Create sample image file
        img_path = os.path.join(temp_dir, "sample.jpg")
        with open(img_path, 'wb') as f:
            f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF")  # Basic JPEG header
        files.append({
            'filename': 'sample.jpg',
            'file_path': img_path,
            'original_name': 'Sample Image.jpg',
            'size': len(b"\xff\xd8\xff\xe0\x00\x10JFIF"),
            'category': 'submission',
            'extension': '.jpg'
        })
        
        yield files


def create_test_user(username=None, email=None, password="TestPass123!"):
    """Create a test user."""
    import uuid
    
    # Generate unique username and email if not provided
    if username is None:
        username = f"testuser_{str(uuid.uuid4())[:8]}"
    if email is None:
        email = f"test_{str(uuid.uuid4())[:8]}@testing.local"
    
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    return user


def login_user(client, username="testuser", password="TestPass123!"):
    """Login a user via the test client."""
    return client.post('/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Test content for file processing")
        temp_path = f.name
    
    yield temp_path
    
    try:
        os.unlink(temp_path)
    except OSError:
        pass


@pytest.fixture
def mock_ocr_service():
    """Mock OCR service for testing."""
    with patch('src.services.ocr_service.OCRService') as mock:
        mock_instance = Mock()
        mock_instance.extract_text.return_value = {
            'success': True,
            'text': 'Mocked OCR text',
            'confidence': 0.95
        }
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing."""
    with patch('src.services.llm_service.LLMService') as mock:
        mock_instance = Mock()
        mock_instance.grade_answer.return_value = {
            'success': True,
            'score': 85,
            'feedback': 'Good answer with minor improvements needed'
        }
        mock.return_value = mock_instance
        yield mock_instance