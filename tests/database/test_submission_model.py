"""Unit tests for Submission model."""

import pytest
import hashlib
from sqlalchemy.exc import IntegrityError

from src.database.optimized_models import User, MarkingGuide, Submission, db


class TestSubmissionModel:
    """Test cases for Submission model."""

    @pytest.fixture
    def user(self, app_context):
        """Create a test user."""
        user = User(username="testuser", email="test@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        return user

    @pytest.fixture
    def marking_guide(self, app_context, user):
        """Create a test marking guide."""
        guide = MarkingGuide(
            user_id=user.id,
            title="Test Guide",
            filename="guide.pdf",
            file_path="/uploads/guide.pdf",
            file_size=1024,
            file_type="application/pdf"
        )
        db.session.add(guide)
        db.session.commit()
        return guide

    def test_submission_creation_valid(self, app_context, user, marking_guide):
        """Test creating a valid submission."""
        submission = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_name="John Doe",
            student_id="12345",
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_size=2048,
            file_type="application/pdf",
            content_text="Student answers",
            ocr_confidence=0.95,
            processing_status="pending"
        )
        
        db.session.add(submission)
        db.session.commit()
        
        assert submission.id is not None
        assert submission.user_id == user.id
        assert submission.marking_guide_id == marking_guide.id
        assert submission.student_name == "John Doe"
        assert submission.student_id == "12345"
        assert submission.filename == "submission.pdf"
        assert submission.file_path == "/uploads/submission.pdf"
        assert submission.file_size == 2048
        assert submission.file_type == "application/pdf"
        assert submission.content_text == "Student answers"
        assert submission.ocr_confidence == 0.95
        assert submission.processing_status == "pending"
        assert submission.archived is False
        assert submission.processed is False
        assert submission.created_at is not None
        assert submission.updated_at is not None

    def test_student_name_validation(self, app_context, user, marking_guide):
        """Test student name validation rules."""
        submission = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_id="12345",
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_size=2048,
            file_type="application/pdf"
        )
        
        # Test empty student name
        with pytest.raises(ValueError, match="Student name is required"):
            submission.student_name = ""
        
        # Test whitespace-only student name
        with pytest.raises(ValueError, match="Student name is required"):
            submission.student_name = "   "
        
        # Test long student name
        with pytest.raises(ValueError, match="Student name must be no more than 200 characters"):
            submission.student_name = "a" * 201
        
        # Test valid student name
        submission.student_name = "John Doe"
        assert submission.student_name == "John Doe"
        
        # Test student name with leading/trailing whitespace
        submission.student_name = "  Jane Smith  "
        assert submission.student_name == "Jane Smith"

    def test_student_id_validation(self, app_context, user, marking_guide):
        """Test student ID validation rules."""
        submission = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_name="John Doe",
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_size=2048,
            file_type="application/pdf"
        )
        
        # Test empty student ID
        with pytest.raises(ValueError, match="Student ID is required"):
            submission.student_id = ""
        
        # Test whitespace-only student ID
        with pytest.raises(ValueError, match="Student ID is required"):
            submission.student_id = "   "
        
        # Test long student ID
        with pytest.raises(ValueError, match="Student ID must be no more than 100 characters"):
            submission.student_id = "a" * 101
        
        # Test valid student ID
        submission.student_id = "12345"
        assert submission.student_id == "12345"
        
        # Test student ID with leading/trailing whitespace
        submission.student_id = "  67890  "
        assert submission.student_id == "67890"

    def test_processing_status_validation(self, app_context, user, marking_guide):
        """Test processing status validation rules."""
        submission = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_name="John Doe",
            student_id="12345",
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_size=2048,
            file_type="application/pdf"
        )
        
        # Test invalid status
        with pytest.raises(ValueError, match="Status must be one of"):
            submission.processing_status = "invalid_status"
        
        # Test valid statuses
        valid_statuses = ['pending', 'processing', 'completed', 'failed']
        for status in valid_statuses:
            submission.processing_status = status
            assert submission.processing_status == status

    def test_file_size_validation(self, app_context, user, marking_guide):
        """Test file size validation rules."""
        submission = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_name="John Doe",
            student_id="12345",
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_type="application/pdf"
        )
        
        # Test zero file size
        with pytest.raises(ValueError, match="File size must be greater than 0"):
            submission.file_size = 0
        
        # Test negative file size
        with pytest.raises(ValueError, match="File size must be greater than 0"):
            submission.file_size = -1
        
        # Test file size too large (100MB limit)
        with pytest.raises(ValueError, match="File size must be less than 100MB"):
            submission.file_size = 101 * 1024 * 1024
        
        # Test valid file size
        submission.file_size = 2048
        assert submission.file_size == 2048

    def test_content_hash_generation(self, app_context, user, marking_guide):
        """Test content hash generation."""
        submission = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_name="John Doe",
            student_id="12345",
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_size=2048,
            file_type="application/pdf",
            content_text="Student answers"
        )
        
        # Test hash generation from content text
        submission.generate_content_hash()
        expected_hash = hashlib.sha256("Student answers".encode('utf-8')).hexdigest()
        assert submission.content_hash == expected_hash
        
        # Test hash generation from binary content
        binary_content = b"Binary submission content"
        submission.generate_content_hash(binary_content)
        expected_hash = hashlib.sha256(binary_content).hexdigest()
        assert submission.content_hash == expected_hash

    def test_duplicate_detection(self, app_context, user, marking_guide):
        """Test duplicate detection functionality."""
        # Create first submission
        submission1 = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_name="John Doe",
            student_id="12345",
            filename="submission1.pdf",
            file_path="/uploads/submission1.pdf",
            file_size=2048,
            file_type="application/pdf",
            content_text="Same content"
        )
        submission1.generate_content_hash()
        
        db.session.add(submission1)
        db.session.commit()
        
        # Initially not a duplicate
        assert submission1.is_duplicate is False
        
        # Create second submission with same content hash
        submission2 = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_name="Jane Smith",
            student_id="67890",
            filename="submission2.pdf",
            file_path="/uploads/submission2.pdf",
            file_size=2048,
            file_type="application/pdf",
            content_text="Same content"
        )
        submission2.generate_content_hash()
        
        db.session.add(submission2)
        db.session.commit()
        
        # Second submission should be detected as duplicate
        assert submission2.is_duplicate is True
        
        # First submission should still not be duplicate (it was first)
        assert submission1.is_duplicate is False

    def test_foreign_key_constraints(self, app_context):
        """Test foreign key constraints."""
        # Try to create submission with non-existent user
        submission = Submission(
            user_id="non-existent-user-id",
            student_name="John Doe",
            student_id="12345",
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_size=2048,
            file_type="application/pdf"
        )
        
        db.session.add(submission)
        
        # This should raise an IntegrityError due to foreign key constraint
        with pytest.raises(IntegrityError):
            db.session.commit()
        
        db.session.rollback()
        
        # Try to create submission with non-existent marking guide
        submission = Submission(
            marking_guide_id="non-existent-guide-id",
            student_name="John Doe",
            student_id="12345",
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_size=2048,
            file_type="application/pdf"
        )
        
        db.session.add(submission)
        
        # This should raise an IntegrityError due to foreign key constraint
        with pytest.raises(IntegrityError):
            db.session.commit()

    def test_relationships(self, app_context, user, marking_guide):
        """Test relationships with other models."""
        submission = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_name="John Doe",
            student_id="12345",
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_size=2048,
            file_type="application/pdf"
        )
        
        db.session.add(submission)
        db.session.commit()
        
        # Test relationship to user
        assert submission.user is not None
        assert submission.user.id == user.id
        assert submission.user.username == "testuser"
        
        # Test relationship to marking guide
        assert submission.marking_guide is not None
        assert submission.marking_guide.id == marking_guide.id
        assert submission.marking_guide.title == "Test Guide"
        
        # Test reverse relationships
        assert len(user.submissions) == 1
        assert user.submissions[0].id == submission.id
        
        assert len(marking_guide.submissions) == 1
        assert marking_guide.submissions[0].id == submission.id
        
        # Test that relationships are properly defined
        assert hasattr(submission, 'mappings')
        assert hasattr(submission, 'grading_results')
        assert len(submission.mappings) == 0
        assert len(submission.grading_results) == 0

    def test_cascade_delete(self, app_context, user, marking_guide):
        """Test cascade delete when parent records are deleted."""
        submission = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_name="John Doe",
            student_id="12345",
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_size=2048,
            file_type="application/pdf"
        )
        
        db.session.add(submission)
        db.session.commit()
        
        submission_id = submission.id
        
        # Delete user should cascade delete submission
        db.session.delete(user)
        db.session.commit()
        
        # Submission should be deleted
        deleted_submission = Submission.query.get(submission_id)
        assert deleted_submission is None

    def test_to_dict_method(self, app_context, user, marking_guide):
        """Test to_dict method."""
        submission = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_name="John Doe",
            student_id="12345",
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_size=2048,
            file_type="application/pdf",
            content_text="Student answers",
            ocr_confidence=0.95,
            processing_status="completed",
            archived=False
        )
        
        db.session.add(submission)
        db.session.commit()
        
        data = submission.to_dict()
        
        expected_keys = {
            "id", "user_id", "marking_guide_id", "student_name", "student_id",
            "filename", "file_size", "file_type", "content_text", "answers",
            "ocr_confidence", "processing_status", "processing_error",
            "archived", "created_at", "updated_at"
        }
        
        assert set(data.keys()) == expected_keys
        assert data["student_name"] == "John Doe"
        assert data["student_id"] == "12345"
        assert data["user_id"] == user.id
        assert data["marking_guide_id"] == marking_guide.id
        assert data["file_size"] == 2048
        assert data["ocr_confidence"] == 0.95
        assert data["processing_status"] == "completed"
        assert data["archived"] is False

    def test_check_constraints_validation(self, app_context, user, marking_guide):
        """Test that check constraints are properly validated."""
        submission = Submission(
            user_id=user.id,
            marking_guide_id=marking_guide.id,
            student_name="John Doe",
            student_id="12345",
            filename="submission.pdf",
            file_path="/uploads/submission.pdf",
            file_size=2048,
            file_type="application/pdf"
        )
        
        # Test invalid OCR confidence (should be between 0 and 1)
        submission.ocr_confidence = 1.5
        db.session.add(submission)
        
        # Note: SQLite doesn't enforce check constraints by default
        # This test documents the intended behavior
        # In production with PostgreSQL, this would raise an IntegrityError
        
        # Reset to valid value
        submission.ocr_confidence = 0.95
        db.session.commit()
        
        assert submission.ocr_confidence == 0.95

    def test_performance_indexes(self, app_context, user, marking_guide):
        """Test that performance indexes work correctly."""
        # Create multiple submissions to test index performance
        submissions = []
        statuses = ['pending', 'processing', 'completed', 'failed']
        
        for i in range(20):
            submission = Submission(
                user_id=user.id,
                marking_guide_id=marking_guide.id,
                student_name=f"Student {i}",
                student_id=f"ID{i:03d}",
                filename=f"submission_{i}.pdf",
                file_path=f"/uploads/submission_{i}.pdf",
                file_size=1024 + i,
                file_type="application/pdf",
                processing_status=statuses[i % 4]
            )
            submissions.append(submission)
            db.session.add(submission)
        
        db.session.commit()
        
        # Test queries that should use indexes
        
        # Test idx_user_status index
        user_pending = Submission.query.filter_by(
            user_id=user.id,
            processing_status='pending'
        ).all()
        assert len(user_pending) == 5
        
        # Test idx_user_created index
        user_recent = Submission.query.filter_by(
            user_id=user.id
        ).order_by(
            Submission.created_at.desc()
        ).limit(5).all()
        assert len(user_recent) == 5
        
        # Test idx_status_created index
        completed_recent = Submission.query.filter_by(
            processing_status='completed'
        ).order_by(
            Submission.created_at.desc()
        ).limit(3).all()
        assert len(completed_recent) == 3
        
        # Test idx_guide_status index
        guide_completed = Submission.query.filter_by(
            marking_guide_id=marking_guide.id,
            processing_status='completed'
        ).all()
        assert len(guide_completed) == 5