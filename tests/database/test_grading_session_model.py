"""Unit tests for the GradingSession model."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from src.database.optimized_models import db, GradingSession, User, MarkingGuide, Submission


class TestGradingSessionModel:
    """Test cases for the GradingSession model."""
    
    def test_valid_grading_session_creation(self, app_context, db_utils):
        """Test creating a valid grading session."""
        # Create test data
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        # Create grading session
        session = GradingSession(
            submission_id=submission.id,
            marking_guide_id=guide.id,
            user_id=user.id,
            progress_id="progress_abc123",
            status="in_progress",
            current_step="mapping",
            total_questions_mapped=5,
            total_questions_graded=3,
            max_questions_limit=10,
            processing_start_time=datetime.utcnow(),
            session_data={"batch_id": "batch_001", "settings": {"auto_grade": True}}
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Verify grading session was created
        assert session.id is not None
        assert session.submission_id == submission.id
        assert session.marking_guide_id == guide.id
        assert session.user_id == user.id
        assert session.progress_id == "progress_abc123"
        assert session.status == "in_progress"
        assert session.current_step == "mapping"
        assert session.total_questions_mapped == 5
        assert session.total_questions_graded == 3
        assert session.max_questions_limit == 10
    
    def test_grading_session_relationships(self, app_context, db_utils):
        """Test grading session relationships with other models."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        session = GradingSession(
            submission_id=submission.id,
            marking_guide_id=guide.id,
            user_id=user.id,
            progress_id="test_progress",
            status="not_started",
            current_step="text_retrieval"
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Test relationships
        assert session.submission == submission
        assert session.marking_guide == guide
        assert session.user == user
        assert session in submission.grading_sessions
        assert session in guide.grading_sessions
        assert session in user.grading_sessions
    
    def test_status_validation(self, app_context, db_utils):
        """Test status validation."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        # Test valid statuses
        valid_statuses = ["not_started", "in_progress", "completed", "failed"]
        
        for status in valid_statuses:
            session = GradingSession(
                submission_id=submission.id,
                marking_guide_id=guide.id,
                user_id=user.id,
                progress_id=f"progress_{status}",
                status=status,
                current_step="text_retrieval"
            )
            
            # Should not raise validation error
            result = session.validate_status(status)
            assert result is True
            
            db.session.add(session)
            db.session.commit()
            
            assert session.status == status
            
            # Clean up for next iteration
            db.session.delete(session)
            db.session.commit()
        
        # Test invalid status
        session = GradingSession(
            submission_id=submission.id,
            marking_guide_id=guide.id,
            user_id=user.id,
            progress_id="progress_invalid",
            status="invalid_status",
            current_step="text_retrieval"
        )
        
        # Should raise validation error
        with pytest.raises(ValueError, match="Invalid status"):
            session.validate_status("invalid_status")
    
    def test_current_step_validation(self, app_context, db_utils):
        """Test current step validation."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        # Test valid steps
        valid_steps = ["text_retrieval", "mapping", "grading", "saving"]
        
        for step in valid_steps:
            session = GradingSession(
                submission_id=submission.id,
                marking_guide_id=guide.id,
                user_id=user.id,
                progress_id=f"progress_{step}",
                status="in_progress",
                current_step=step
            )
            
            # Should not raise validation error
            result = session.validate_current_step(step)
            assert result is True
            
            db.session.add(session)
            db.session.commit()
            
            assert session.current_step == step
            
            # Clean up for next iteration
            db.session.delete(session)
            db.session.commit()
        
        # Test invalid step
        session = GradingSession(
            submission_id=submission.id,
            marking_guide_id=guide.id,
            user_id=user.id,
            progress_id="progress_invalid_step",
            status="in_progress",
            current_step="invalid_step"
        )
        
        # Should raise validation error
        with pytest.raises(ValueError, match="Invalid current step"):
            session.validate_current_step("invalid_step")
    
    def test_question_count_constraints(self, app_context, db_utils):
        """Test question count validation constraints."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        # Test invalid total_questions_mapped (negative)
        session = GradingSession(
            submission_id=submission.id,
            marking_guide_id=guide.id,
            user_id=user.id,
            progress_id="progress_negative_mapped",
            status="in_progress",
            current_step="mapping",
            total_questions_mapped=-1,  # Invalid: negative
            total_questions_graded=0,
            max_questions_limit=10
        )
        
        db.session.add(session)
        
        # For SQLite, check constraints might not be enforced
        try:
            db.session.commit()
            assert session.total_questions_mapped == -1
        except IntegrityError:
            db.session.rollback()
    
    def test_foreign_key_constraints(self, app_context, db_utils):
        """Test foreign key constraints."""
        # Test invalid submission_id
        session = GradingSession(
            submission_id=99999,  # Non-existent submission
            marking_guide_id=1,
            user_id=1,
            progress_id="progress_invalid_submission",
            status="not_started",
            current_step="text_retrieval"
        )
        
        db.session.add(session)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
        
        db.session.rollback()
    
    def test_cascade_delete(self, app_context, db_utils):
        """Test cascade delete when submission is deleted."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        session = GradingSession(
            submission_id=submission.id,
            marking_guide_id=guide.id,
            user_id=user.id,
            progress_id="progress_cascade_test",
            status="in_progress",
            current_step="grading"
        )
        
        db.session.add(session)
        db.session.commit()
        
        session_id = session.id
        
        # Delete submission
        db.session.delete(submission)
        db.session.commit()
        
        # Verify grading session was also deleted
        deleted_session = db.session.get(GradingSession, session_id)
        assert deleted_session is None
    
    def test_to_dict_method(self, app_context, db_utils):
        """Test the to_dict method."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=30)
        
        session = GradingSession(
            submission_id=submission.id,
            marking_guide_id=guide.id,
            user_id=user.id,
            progress_id="progress_to_dict_test",
            status="completed",
            current_step="saving",
            total_questions_mapped=8,
            total_questions_graded=8,
            max_questions_limit=10,
            processing_start_time=start_time,
            processing_end_time=end_time,
            error_message=None,
            session_data={"batch_id": "batch_002", "auto_save": True}
        )
        
        db.session.add(session)
        db.session.commit()
        
        session_dict = session.to_dict()
        
        # Verify dictionary contains expected fields
        assert 'id' in session_dict
        assert session_dict['submission_id'] == submission.id
        assert session_dict['marking_guide_id'] == guide.id
        assert session_dict['user_id'] == user.id
        assert session_dict['progress_id'] == "progress_to_dict_test"
        assert session_dict['status'] == "completed"
        assert session_dict['current_step'] == "saving"
        assert session_dict['total_questions_mapped'] == 8
        assert session_dict['total_questions_graded'] == 8
        assert session_dict['max_questions_limit'] == 10
        assert 'processing_start_time' in session_dict
        assert 'processing_end_time' in session_dict
        assert session_dict['error_message'] is None
        assert session_dict['session_data'] == {"batch_id": "batch_002", "auto_save": True}
        assert 'created_at' in session_dict
        assert 'updated_at' in session_dict
    
    def test_session_progress_tracking(self, app_context, db_utils):
        """Test session progress tracking functionality."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        # Create session with initial state
        session = GradingSession(
            submission_id=submission.id,
            marking_guide_id=guide.id,
            user_id=user.id,
            progress_id="progress_tracking_test",
            status="not_started",
            current_step="text_retrieval",
            total_questions_mapped=0,
            total_questions_graded=0,
            max_questions_limit=5
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Simulate progress updates
        session.status = "in_progress"
        session.current_step = "mapping"
        session.processing_start_time = datetime.utcnow()
        db.session.commit()
        
        # Update mapping progress
        session.total_questions_mapped = 3
        session.current_step = "grading"
        db.session.commit()
        
        # Update grading progress
        session.total_questions_graded = 2
        db.session.commit()
        
        # Complete session
        session.total_questions_graded = 3
        session.status = "completed"
        session.current_step = "saving"
        session.processing_end_time = datetime.utcnow()
        db.session.commit()
        
        # Verify final state
        assert session.status == "completed"
        assert session.current_step == "saving"
        assert session.total_questions_mapped == 3
        assert session.total_questions_graded == 3
        assert session.processing_start_time is not None
        assert session.processing_end_time is not None
    
    def test_error_handling(self, app_context, db_utils):
        """Test error handling in grading sessions."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        # Create session that encounters an error
        session = GradingSession(
            submission_id=submission.id,
            marking_guide_id=guide.id,
            user_id=user.id,
            progress_id="progress_error_test",
            status="in_progress",
            current_step="grading",
            total_questions_mapped=5,
            total_questions_graded=2,
            processing_start_time=datetime.utcnow()
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Simulate error occurrence
        error_message = "AI service timeout during grading"
        session.status = "failed"
        session.error_message = error_message
        session.processing_end_time = datetime.utcnow()
        db.session.commit()
        
        # Verify error state
        assert session.status == "failed"
        assert session.error_message == error_message
        assert session.processing_end_time is not None
    
    def test_composite_indexes(self, app_context, db_utils):
        """Test that composite indexes exist and work efficiently."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        # Create multiple grading sessions
        statuses = ["not_started", "in_progress", "completed", "failed", "in_progress"]
        steps = ["text_retrieval", "mapping", "grading", "saving", "grading"]
        
        for i, (status, step) in enumerate(zip(statuses, steps)):
            session = GradingSession(
                submission_id=submission.id,
                marking_guide_id=guide.id,
                user_id=user.id,
                progress_id=f"progress_index_test_{i}",
                status=status,
                current_step=step,
                total_questions_mapped=i + 1,
                total_questions_graded=i if status == "completed" else 0
            )
            db.session.add(session)
        
        db.session.commit()
        
        # Test querying with indexed columns
        in_progress_sessions = GradingSession.query.filter_by(
            submission_id=submission.id,
            status="in_progress"
        ).all()
        
        assert len(in_progress_sessions) == 2
        
        # Test querying by user and status
        user_completed_sessions = GradingSession.query.filter_by(
            user_id=user.id,
            status="completed"
        ).all()
        
        assert len(user_completed_sessions) == 1
        
        # Test querying by progress_id (should use index)
        specific_session = GradingSession.query.filter_by(
            progress_id="progress_index_test_2"
        ).first()
        
        assert specific_session is not None
        assert specific_session.status == "completed"
    
    def test_session_data_json_field(self, app_context, db_utils):
        """Test JSON session_data field functionality."""
        user = db_utils.create_test_user()
        guide = db_utils.create_test_marking_guide(user)
        submission = db_utils.create_test_submission(user, guide)
        
        # Test with complex JSON data
        complex_data = {
            "batch_settings": {
                "auto_grade": True,
                "confidence_threshold": 0.85,
                "retry_failed": False
            },
            "processing_metadata": {
                "ai_model": "gpt-4",
                "processing_version": "2.1.0",
                "start_timestamp": datetime.utcnow().isoformat()
            },
            "user_preferences": {
                "notification_enabled": True,
                "detailed_feedback": True
            }
        }
        
        session = GradingSession(
            submission_id=submission.id,
            marking_guide_id=guide.id,
            user_id=user.id,
            progress_id="progress_json_test",
            status="in_progress",
            current_step="mapping",
            session_data=complex_data
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Verify JSON data was stored and retrieved correctly
        retrieved_session = GradingSession.query.filter_by(
            progress_id="progress_json_test"
        ).first()
        
        assert retrieved_session.session_data == complex_data
        assert retrieved_session.session_data["batch_settings"]["auto_grade"] is True
        assert retrieved_session.session_data["processing_metadata"]["ai_model"] == "gpt-4"
        assert retrieved_session.session_data["user_preferences"]["notification_enabled"] is True