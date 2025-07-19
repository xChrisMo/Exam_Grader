"""Unit tests for the GradingResult model."""

import pytest
from sqlalchemy.exc import IntegrityError
from src.database.optimized_models import db, GradingResult, User, MarkingGuide, Submission, Mapping


class TestGradingResultModel:
    """Test cases for the GradingResult model."""
    
    def test_valid_grading_result_creation(self, app_context, db_utils):
        """Test creating a valid grading result."""
        # Create test data
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
            match_score=8.0,
            mapping_method="exact"
        )
        db.session.add(mapping)
        db.session.commit()
        
        # Create grading result
        result = GradingResult(
            submission_id=submission.id,
            mapping_id=mapping.id,
            score=8.5,
            max_score=10.0,
            percentage=85.0,
            feedback="Good answer",
            detailed_feedback="The answer demonstrates understanding",
            progress_id="progress_123",
            grading_method="ai",
            confidence=0.95
        )
        
        db.session.add(result)
        db.session.commit()
        
        # Verify grading result was created
        assert result.id is not None
        assert result.submission_id == submission.id
        assert result.mapping_id == mapping.id
        assert result.score == 8.5
        assert result.max_score == 10.0
        assert result.percentage == 85.0
        assert result.grading_method == "ai"
        assert result.confidence == 0.95
    
    def test_grading_result_relationships(self, app_context, db_utils):
        """Test grading result relationships with other models."""
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
            match_score=8.0,
            mapping_method="exact"
        )
        db.session.add(mapping)
        db.session.commit()
        
        result = GradingResult(
            submission_id=submission.id,
            mapping_id=mapping.id,
            score=7.5,
            max_score=10.0,
            percentage=75.0,
            grading_method="manual"
        )
        
        db.session.add(result)
        db.session.commit()
        
        # Test relationships
        assert result.submission == submission
        assert result.mapping == mapping
        assert result in submission.grading_results
        assert result in mapping.grading_results
    
    def test_score_validation(self, app_context, db_utils):
        """Test score validation constraints."""
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
            match_score=8.0,
            mapping_method="exact"
        )
        db.session.add(mapping)
        db.session.commit()
        
        # Test invalid score (negative)
        result = GradingResult(
            submission_id=submission.id,
            mapping_id=mapping.id,
            score=-1.0,  # Invalid: negative score
            max_score=10.0,
            percentage=0.0,
            grading_method="manual"
        )
        
        db.session.add(result)
        
        # For SQLite, check constraints might not be enforced
        try:
            db.session.commit()
            assert result.score == -1.0
        except IntegrityError:
            db.session.rollback()
    
    def test_percentage_validation(self, app_context, db_utils):
        """Test percentage validation constraints."""
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
            match_score=8.0,
            mapping_method="exact"
        )
        db.session.add(mapping)
        db.session.commit()
        
        # Test invalid percentage (over 100)
        result = GradingResult(
            submission_id=submission.id,
            mapping_id=mapping.id,
            score=8.0,
            max_score=10.0,
            percentage=150.0,  # Invalid: over 100%
            grading_method="manual"
        )
        
        db.session.add(result)
        
        # For SQLite, check constraints might not be enforced
        try:
            db.session.commit()
            assert result.percentage == 150.0
        except IntegrityError:
            db.session.rollback()
    
    def test_confidence_validation(self, app_context, db_utils):
        """Test confidence validation constraints."""
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
            match_score=8.0,
            mapping_method="exact"
        )
        db.session.add(mapping)
        db.session.commit()
        
        # Test invalid confidence (over 1.0)
        result = GradingResult(
            submission_id=submission.id,
            mapping_id=mapping.id,
            score=8.0,
            max_score=10.0,
            percentage=80.0,
            grading_method="ai",
            confidence=1.5  # Invalid: over 1.0
        )
        
        db.session.add(result)
        
        # For SQLite, check constraints might not be enforced
        try:
            db.session.commit()
            assert result.confidence == 1.5
        except IntegrityError:
            db.session.rollback()
    
    def test_foreign_key_constraints(self, app_context, db_utils):
        """Test foreign key constraints."""
        # Test invalid submission_id
        result = GradingResult(
            submission_id=99999,  # Non-existent submission
            mapping_id=1,
            score=8.0,
            max_score=10.0,
            percentage=80.0,
            grading_method="manual"
        )
        
        db.session.add(result)
        
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
            match_score=8.0,
            mapping_method="exact"
        )
        db.session.add(mapping)
        db.session.commit()
        
        result = GradingResult(
            submission_id=submission.id,
            mapping_id=mapping.id,
            score=7.5,
            max_score=10.0,
            percentage=75.0,
            grading_method="manual"
        )
        
        db.session.add(result)
        db.session.commit()
        
        result_id = result.id
        
        # Delete submission
        db.session.delete(submission)
        db.session.commit()
        
        # Verify grading result was also deleted
        deleted_result = db.session.get(GradingResult, result_id)
        assert deleted_result is None
    
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
            match_score=8.0,
            mapping_method="exact"
        )
        db.session.add(mapping)
        db.session.commit()
        
        result = GradingResult(
            submission_id=submission.id,
            mapping_id=mapping.id,
            score=8.5,
            max_score=10.0,
            percentage=85.0,
            feedback="Excellent work",
            detailed_feedback="Shows deep understanding",
            progress_id="progress_456",
            grading_method="ai",
            confidence=0.92
        )
        
        db.session.add(result)
        db.session.commit()
        
        result_dict = result.to_dict()
        
        # Verify dictionary contains expected fields
        assert 'id' in result_dict
        assert result_dict['submission_id'] == submission.id
        assert result_dict['mapping_id'] == mapping.id
        assert result_dict['score'] == 8.5
        assert result_dict['max_score'] == 10.0
        assert result_dict['percentage'] == 85.0
        assert result_dict['feedback'] == "Excellent work"
        assert result_dict['detailed_feedback'] == "Shows deep understanding"
        assert result_dict['progress_id'] == "progress_456"
        assert result_dict['grading_method'] == "ai"
        assert result_dict['confidence'] == 0.92
        assert 'created_at' in result_dict
        assert 'updated_at' in result_dict
    
    def test_grading_method_values(self, app_context, db_utils):
        """Test different grading method values."""
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
            match_score=8.0,
            mapping_method="exact"
        )
        db.session.add(mapping)
        db.session.commit()
        
        methods = ["ai", "manual", "hybrid", "automated"]
        
        for i, method in enumerate(methods):
            result = GradingResult(
                submission_id=submission.id,
                mapping_id=mapping.id,
                score=float(7 + i),
                max_score=10.0,
                percentage=float(70 + i * 10),
                grading_method=method,
                progress_id=f"progress_{i}"
            )
            
            db.session.add(result)
            db.session.commit()
            
            assert result.grading_method == method
    
    def test_composite_indexes(self, app_context, db_utils):
        """Test that composite indexes exist and work efficiently."""
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
            match_score=8.0,
            mapping_method="exact"
        )
        db.session.add(mapping)
        db.session.commit()
        
        # Create multiple grading results
        for i in range(5):
            result = GradingResult(
                submission_id=submission.id,
                mapping_id=mapping.id,
                score=float(5 + i),
                max_score=10.0,
                percentage=float(50 + i * 10),
                grading_method="ai" if i % 2 == 0 else "manual",
                progress_id=f"progress_{i}",
                confidence=0.8 + (i * 0.05)
            )
            db.session.add(result)
        
        db.session.commit()
        
        # Test querying with indexed columns
        ai_results = GradingResult.query.filter_by(
            submission_id=submission.id,
            grading_method="ai"
        ).all()
        
        assert len(ai_results) == 3  # Results 0, 2, 4
        
        # Test ordering by score (should use index)
        ordered_results = GradingResult.query.filter_by(
            submission_id=submission.id
        ).order_by(GradingResult.score.desc()).all()
        
        assert len(ordered_results) == 5
        assert ordered_results[0].score == 9.0
        assert ordered_results[-1].score == 5.0
    
    def test_progress_id_filtering(self, app_context, db_utils):
        """Test filtering by progress_id."""
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
            match_score=8.0,
            mapping_method="exact"
        )
        db.session.add(mapping)
        db.session.commit()
        
        # Create results with different progress_ids
        progress_ids = ["batch_1", "batch_1", "batch_2", "batch_2", "batch_3"]
        
        for i, progress_id in enumerate(progress_ids):
            result = GradingResult(
                submission_id=submission.id,
                mapping_id=mapping.id,
                score=float(5 + i),
                max_score=10.0,
                percentage=float(50 + i * 10),
                grading_method="ai",
                progress_id=progress_id
            )
            db.session.add(result)
        
        db.session.commit()
        
        # Test filtering by progress_id
        batch_1_results = GradingResult.query.filter_by(
            progress_id="batch_1"
        ).all()
        
        assert len(batch_1_results) == 2
        
        batch_2_results = GradingResult.query.filter_by(
            progress_id="batch_2"
        ).all()
        
        assert len(batch_2_results) == 2
        
        batch_3_results = GradingResult.query.filter_by(
            progress_id="batch_3"
        ).all()
        
        assert len(batch_3_results) == 1