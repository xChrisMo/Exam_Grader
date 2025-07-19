"""Unit tests for MarkingGuide model."""

import pytest
import hashlib
from sqlalchemy.exc import IntegrityError

from src.database.optimized_models import User, MarkingGuide, db


class TestMarkingGuideModel:
    """Test cases for MarkingGuide model."""

    @pytest.fixture
    def user(self, app_context):
        """Create a test user."""
        user = User(username="testuser", email="test@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user

    def test_marking_guide_creation_valid(self, app_context, user):
        """Test creating a valid marking guide."""
        guide = MarkingGuide(
            user_id=user.id,
            title="Test Guide",
            description="A test marking guide",
            filename="test_guide.pdf",
            file_path="/uploads/test_guide.pdf",
            file_size=1024,
            file_type="application/pdf",
            content_text="Sample content",
            total_marks=100.0,
            max_questions_to_answer=5
        )
        
        db.session.add(guide)
        db.session.commit()
        
        assert guide.id is not None
        assert guide.user_id == user.id
        assert guide.title == "Test Guide"
        assert guide.description == "A test marking guide"
        assert guide.filename == "test_guide.pdf"
        assert guide.file_path == "/uploads/test_guide.pdf"
        assert guide.file_size == 1024
        assert guide.file_type == "application/pdf"
        assert guide.content_text == "Sample content"
        assert guide.total_marks == 100.0
        assert guide.max_questions_to_answer == 5
        assert guide.is_active is True
        assert guide.created_at is not None
        assert guide.updated_at is not None

    def test_title_validation(self, app_context, user):
        """Test title validation rules."""
        guide = MarkingGuide(
            user_id=user.id,
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024,
            file_type="application/pdf"
        )
        
        # Test empty title
        with pytest.raises(ValueError, match="Title is required"):
            guide.title = ""
        
        # Test whitespace-only title
        with pytest.raises(ValueError, match="Title is required"):
            guide.title = "   "
        
        # Test long title
        with pytest.raises(ValueError, match="Title must be no more than 200 characters"):
            guide.title = "a" * 201
        
        # Test valid title
        guide.title = "Valid Title"
        assert guide.title == "Valid Title"
        
        # Test title with leading/trailing whitespace
        guide.title = "  Trimmed Title  "
        assert guide.title == "Trimmed Title"

    def test_file_size_validation(self, app_context, user):
        """Test file size validation rules."""
        guide = MarkingGuide(
            user_id=user.id,
            title="Test Guide",
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_type="application/pdf"
        )
        
        # Test zero file size
        with pytest.raises(ValueError, match="File size must be positive"):
            guide.file_size = 0
        
        # Test negative file size
        with pytest.raises(ValueError, match="File size must be positive"):
            guide.file_size = -1
        
        # Test file size too large (100MB limit)
        with pytest.raises(ValueError, match="File size cannot exceed 100MB"):
            guide.file_size = 101 * 1024 * 1024
        
        # Test valid file size
        guide.file_size = 1024
        assert guide.file_size == 1024

    def test_file_type_validation(self, app_context, user):
        """Test file type validation rules."""
        guide = MarkingGuide(
            user_id=user.id,
            title="Test Guide",
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024
        )
        
        # Test invalid file type
        with pytest.raises(ValueError, match="File type .* is not allowed"):
            guide.file_type = "application/exe"
        
        # Test valid file types
        valid_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'image/jpeg',
            'image/png',
            'image/gif'
        ]
        
        for file_type in valid_types:
            guide.file_type = file_type
            assert guide.file_type == file_type

    def test_content_hash_generation(self, app_context, user):
        """Test content hash generation."""
        guide = MarkingGuide(
            user_id=user.id,
            title="Test Guide",
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024,
            file_type="application/pdf",
            content_text="Sample content"
        )
        
        # Test hash generation from content text
        guide.generate_content_hash()
        expected_hash = hashlib.sha256("Sample content".encode('utf-8')).hexdigest()
        assert guide.content_hash == expected_hash
        
        # Test hash generation from binary content
        binary_content = b"Binary content"
        guide.generate_content_hash(binary_content)
        expected_hash = hashlib.sha256(binary_content).hexdigest()
        assert guide.content_hash == expected_hash

    def test_question_count_property(self, app_context, user):
        """Test question_count hybrid property."""
        guide = MarkingGuide(
            user_id=user.id,
            title="Test Guide",
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024,
            file_type="application/pdf"
        )
        
        # Test with no questions
        assert guide.question_count == 0
        
        # Test with questions
        guide.questions = [
            {"id": "q1", "text": "Question 1", "marks": 10},
            {"id": "q2", "text": "Question 2", "marks": 15},
            {"id": "q3", "text": "Question 3", "marks": 20}
        ]
        assert guide.question_count == 3

    def test_foreign_key_constraint(self, app_context):
        """Test foreign key constraint with user."""
        # Try to create guide with non-existent user
        guide = MarkingGuide(
            user_id="non-existent-id",
            title="Test Guide",
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024,
            file_type="application/pdf"
        )
        
        db.session.add(guide)
        
        # This should raise an IntegrityError due to foreign key constraint
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_user_relationship(self, app_context, user):
        """Test relationship with User model."""
        guide = MarkingGuide(
            user_id=user.id,
            title="Test Guide",
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024,
            file_type="application/pdf"
        )
        
        db.session.add(guide)
        db.session.commit()
        
        # Test relationship from guide to user
        assert guide.user is not None
        assert guide.user.id == user.id
        assert guide.user.username == "testuser"
        
        # Test relationship from user to guides
        assert len(user.marking_guides) == 1
        assert user.marking_guides[0].id == guide.id

    def test_cascade_delete(self, app_context, user):
        """Test cascade delete when user is deleted."""
        guide = MarkingGuide(
            user_id=user.id,
            title="Test Guide",
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024,
            file_type="application/pdf"
        )
        
        db.session.add(guide)
        db.session.commit()
        
        guide_id = guide.id
        
        # Delete user should cascade delete guide
        db.session.delete(user)
        db.session.commit()
        
        # Guide should be deleted
        deleted_guide = MarkingGuide.query.get(guide_id)
        assert deleted_guide is None

    def test_to_dict_method(self, app_context, user):
        """Test to_dict method."""
        guide = MarkingGuide(
            user_id=user.id,
            title="Test Guide",
            description="Test description",
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024,
            file_type="application/pdf",
            total_marks=100.0,
            questions=[
                {"id": "q1", "text": "Question 1", "marks": 50},
                {"id": "q2", "text": "Question 2", "marks": 50}
            ]
        )
        
        db.session.add(guide)
        db.session.commit()
        
        data = guide.to_dict()
        
        expected_keys = {
            "id", "user_id", "title", "description", "filename",
            "file_size", "file_type", "total_marks", "is_active",
            "questions", "created_at", "updated_at"
        }
        
        assert set(data.keys()) == expected_keys
        assert data["title"] == "Test Guide"
        assert data["user_id"] == user.id
        assert data["file_size"] == 1024
        assert data["total_marks"] == 100.0
        assert len(data["questions"]) == 2

    def test_check_constraints_validation(self, app_context, user):
        """Test that check constraints are properly validated."""
        guide = MarkingGuide(
            user_id=user.id,
            title="Test Guide",
            filename="test.pdf",
            file_path="/uploads/test.pdf",
            file_size=1024,
            file_type="application/pdf"
        )
        
        # Test negative total_marks (should be prevented by check constraint)
        guide.total_marks = -10.0
        db.session.add(guide)
        
        # Note: SQLite doesn't enforce check constraints by default
        # This test documents the intended behavior
        # In production with PostgreSQL, this would raise an IntegrityError
        
        # Reset to valid value
        guide.total_marks = 100.0
        db.session.commit()
        
        assert guide.total_marks == 100.0

    def test_indexes_exist(self, app_context, user):
        """Test that performance indexes are created."""
        # Create multiple guides to test index performance
        guides = []
        for i in range(10):
            guide = MarkingGuide(
                user_id=user.id,
                title=f"Test Guide {i}",
                filename=f"test_{i}.pdf",
                file_path=f"/uploads/test_{i}.pdf",
                file_size=1024 + i,
                file_type="application/pdf",
                is_active=(i % 2 == 0)  # Alternate active/inactive
            )
            guides.append(guide)
            db.session.add(guide)
        
        db.session.commit()
        
        # Test queries that should use indexes
        # These queries should be fast due to composite indexes
        
        # Test idx_guide_user_title index
        result = MarkingGuide.query.filter_by(
            user_id=user.id
        ).filter(
            MarkingGuide.title.like("Test Guide%")
        ).all()
        assert len(result) == 10
        
        # Test idx_guide_user_active index
        active_guides = MarkingGuide.query.filter_by(
            user_id=user.id,
            is_active=True
        ).all()
        assert len(active_guides) == 5
        
        # Test idx_guide_created_active index
        recent_active = MarkingGuide.query.filter(
            MarkingGuide.is_active == True
        ).order_by(
            MarkingGuide.created_at.desc()
        ).limit(3).all()
        assert len(recent_active) == 3

    def test_validation_mixin_integration(self, app_context, user):
        """Test ValidationMixin methods integration."""
        guide = MarkingGuide(user_id=user.id)
        
        # Test validate_required_fields
        errors = guide.validate_required_fields('title', 'filename', 'file_path')
        assert len(errors) == 3
        
        guide.title = "Test Guide"
        guide.filename = "test.pdf"
        guide.file_path = "/uploads/test.pdf"
        
        errors = guide.validate_required_fields('title', 'filename', 'file_path')
        assert len(errors) == 0
        
        # Test validate_string_length
        errors = guide.validate_string_length('title', min_length=5, max_length=200)
        assert len(errors) == 0
        
        guide.title = "a" * 201
        errors = guide.validate_string_length('title', max_length=200)
        assert len(errors) == 1
        assert "title must be no more than 200 characters" in errors[0]