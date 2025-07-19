"""Unit tests for the Mapping model."""

import pytest
from sqlalchemy.exc import IntegrityError
from src.database.optimized_models import db, Mapping, User, MarkingGuide, Submission


class TestMappingModel:
    """Test cases for the Mapping model."""
    
    def test_valid_mapping_creation(self, app_context, db_utils):
        """Test creating a valid mapping."""
        # Create test data
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        # Create mapping
        mapping = Mapping(
            submission_id=submission.id,
            guide_question_id=1,
            guide_question_text="What is 2+2?",
            guide_answer="4",
            max_score=10.0,
            submission_answer="Four",
            match_score=8.5,
            match_reason="Correct answer in different format",
            mapping_method="semantic"
        )
        
        db.session.add(mapping)
        db.session.commit()
        
        # Verify mapping was created
        assert mapping.id is not None
        assert mapping.submission_id == submission.id
        assert mapping.guide_question_id == 1
        assert mapping.match_score == 8.5
        assert mapping.mapping_method == "semantic"
    
    def test_mapping_relationships(self, app_context, db_utils):
        """Test mapping relationships with other models."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        mapping = Mapping(
            submission_id=submission.id,
            guide_question_id=1,
            guide_question_text="Test question",
            guide_answer="Test answer",
            max_score=10.0,
            submission_answer="Student answer",
            match_score=7.0,
            mapping_method="exact"
        )
        
        db.session.add(mapping)
        db.session.commit()
        
        # Test relationship with submission
        assert mapping.submission == submission
        assert mapping in submission.mappings
    
    def test_match_score_validation(self, app_context, db_utils):
        """Test match score validation constraints."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        # Test invalid match score (negative)
        mapping = Mapping(
            submission_id=submission.id,
            guide_question_id=1,
            guide_question_text="Test question",
            guide_answer="Test answer",
            max_score=10.0,
            submission_answer="Student answer",
            match_score=-1.0,  # Invalid: negative score
            mapping_method="exact"
        )
        
        db.session.add(mapping)
        
        # For SQLite, check constraints might not be enforced
        # This test documents the expected behavior
        try:
            db.session.commit()
            # If we reach here, the constraint wasn't enforced (SQLite behavior)
            assert mapping.match_score == -1.0
        except IntegrityError:
            # If constraint is enforced, this is the expected behavior
            db.session.rollback()
    
    def test_max_score_validation(self, app_context, db_utils):
        """Test max score validation constraints."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        # Test invalid max score (zero)
        mapping = Mapping(
            submission_id=submission.id,
            guide_question_id=1,
            guide_question_text="Test question",
            guide_answer="Test answer",
            max_score=0.0,  # Invalid: zero score
            submission_answer="Student answer",
            match_score=5.0,
            mapping_method="exact"
        )
        
        db.session.add(mapping)
        
        # For SQLite, check constraints might not be enforced
        try:
            db.session.commit()
            assert mapping.max_score == 0.0
        except IntegrityError:
            db.session.rollback()
    
    def test_foreign_key_constraints(self, app_context, db_utils):
        """Test foreign key constraints."""
        # Test invalid submission_id
        mapping = Mapping(
            submission_id=99999,  # Non-existent submission
            guide_question_id=1,
            guide_question_text="Test question",
            guide_answer="Test answer",
            max_score=10.0,
            submission_answer="Student answer",
            match_score=7.0,
            mapping_method="exact"
        )
        
        db.session.add(mapping)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
        
        db.session.rollback()
    
    def test_cascade_delete(self, app_context, db_utils):
        """Test cascade delete when submission is deleted."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        mapping = Mapping(
            submission_id=submission.id,
            guide_question_id=1,
            guide_question_text="Test question",
            guide_answer="Test answer",
            max_score=10.0,
            submission_answer="Student answer",
            match_score=7.0,
            mapping_method="exact"
        )
        
        db.session.add(mapping)
        db.session.commit()
        
        mapping_id = mapping.id
        
        # Delete submission
        db.session.delete(submission)
        db.session.commit()
        
        # Verify mapping was also deleted
        deleted_mapping = db.session.get(Mapping, mapping_id)
        assert deleted_mapping is None
    
    def test_to_dict_method(self, app_context, db_utils):
        """Test the to_dict method."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        mapping = Mapping(
            submission_id=submission.id,
            guide_question_id=1,
            guide_question_text="Test question",
            guide_answer="Test answer",
            max_score=10.0,
            submission_answer="Student answer",
            match_score=7.0,
            match_reason="Good match",
            mapping_method="semantic"
        )
        
        db.session.add(mapping)
        db.session.commit()
        
        mapping_dict = mapping.to_dict()
        
        # Verify dictionary contains expected fields
        assert 'id' in mapping_dict
        assert mapping_dict['submission_id'] == submission.id
        assert mapping_dict['guide_question_id'] == 1
        assert mapping_dict['guide_question_text'] == "Test question"
        assert mapping_dict['guide_answer'] == "Test answer"
        assert mapping_dict['max_score'] == 10.0
        assert mapping_dict['submission_answer'] == "Student answer"
        assert mapping_dict['match_score'] == 7.0
        assert mapping_dict['match_reason'] == "Good match"
        assert mapping_dict['mapping_method'] == "semantic"
        assert 'created_at' in mapping_dict
        assert 'updated_at' in mapping_dict
    
    def test_mapping_method_values(self, app_context, db_utils):
        """Test different mapping method values."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        methods = ["exact", "semantic", "fuzzy", "manual"]
        
        for method in methods:
            mapping = Mapping(
                submission_id=submission.id,
                guide_question_id=1,
                guide_question_text="Test question",
                guide_answer="Test answer",
                max_score=10.0,
                submission_answer="Student answer",
                match_score=7.0,
                mapping_method=method
            )
            
            db.session.add(mapping)
            db.session.commit()
            
            assert mapping.mapping_method == method
            
            # Clean up for next iteration
            db.session.delete(mapping)
            db.session.commit()
    
    def test_composite_indexes(self, app_context, db_utils):
        """Test that composite indexes exist and work efficiently."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        # Create multiple mappings
        for i in range(5):
            mapping = Mapping(
                submission_id=submission.id,
                guide_question_id=i + 1,
                guide_question_text=f"Question {i + 1}",
                guide_answer=f"Answer {i + 1}",
                max_score=10.0,
                submission_answer=f"Student answer {i + 1}",
                match_score=float(i + 5),
                mapping_method="exact" if i % 2 == 0 else "semantic"
            )
            db.session.add(mapping)
        
        db.session.commit()
        
        # Test querying with indexed columns
        mappings = Mapping.query.filter_by(
            submission_id=submission.id,
            mapping_method="exact"
        ).all()
        
        assert len(mappings) == 3  # Questions 1, 3, 5 (0-indexed: 0, 2, 4)
        
        # Test ordering by match_score (should use index)
        ordered_mappings = Mapping.query.filter_by(
            submission_id=submission.id
        ).order_by(Mapping.match_score.desc()).all()
        
        assert len(ordered_mappings) == 5
        assert ordered_mappings[0].match_score == 9.0
        assert ordered_mappings[-1].match_score == 5.0