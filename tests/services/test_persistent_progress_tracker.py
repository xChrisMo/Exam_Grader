"""Tests for Persistent Progress Tracker."""

import json
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.database.models import db
from src.database.progress_models import (
    ProgressMetrics,
    ProgressRecovery,
    ProgressSession,
    ProgressUpdate,
)
from src.services.persistent_progress_tracker import PersistentProgressTracker
from src.services.websocket_manager import MessagePriority, WebSocketManager


class TestPersistentProgressTracker:
    """Test cases for PersistentProgressTracker."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create a mock WebSocket manager."""
        return Mock(spec=WebSocketManager)
    
    @pytest.fixture
    def progress_tracker(self, websocket_manager):
        """Create a progress tracker instance."""
        return PersistentProgressTracker(websocket_manager=websocket_manager)
    
    @pytest.fixture
    def sample_session_data(self):
        """Sample session data for testing."""
        return {
            "session_id": "test_session_123",
            "total_steps": 10,
            "total_submissions": 2,
            "user_id": "user_456",
            "session_type": "grading",
            "estimated_duration": 300.0,
            "metadata": {"exam_id": "exam_789", "subject": "math"}
        }
    
    def test_initialization(self, websocket_manager):
        """Test progress tracker initialization."""
        tracker = PersistentProgressTracker(websocket_manager=websocket_manager)
        
        assert tracker.websocket_manager == websocket_manager
        assert tracker._realtime_service is None
        assert tracker._active_sessions_cache == {}
        assert tracker._metrics_buffer == []
    
    def test_set_realtime_service(self, progress_tracker):
        """Test setting realtime service."""
        mock_service = Mock()
        progress_tracker.set_realtime_service(mock_service)
        
        assert progress_tracker._realtime_service == mock_service
    
    def test_create_session(self, progress_tracker, sample_session_data):
        """Test creating a new progress session."""
        session_id = progress_tracker.create_session(**sample_session_data)
        
        assert session_id == sample_session_data["session_id"]
        
        # Verify database record
        db_session = db.session.query(ProgressSession).filter_by(
            session_id=session_id
        ).first()
        
        assert db_session is not None
        assert db_session.session_id == sample_session_data["session_id"]
        assert db_session.total_steps == sample_session_data["total_steps"]
        assert db_session.user_id == sample_session_data["user_id"]
        assert db_session.session_type == sample_session_data["session_type"]
        assert db_session.status == "active"
        
        # Verify cache
        assert session_id in progress_tracker._active_sessions_cache
    
    def test_create_session_minimal(self, progress_tracker):
        """Test creating session with minimal parameters."""
        session_id = "minimal_session"
        result = progress_tracker.create_session(
            session_id=session_id,
            total_steps=5
        )
        
        assert result == session_id
        
        db_session = db.session.query(ProgressSession).filter_by(
            session_id=session_id
        ).first()
        
        assert db_session.total_submissions == 1
        assert db_session.user_id is None
        assert db_session.session_type is None
    
    def test_update_progress(self, progress_tracker, sample_session_data):
        """Test updating progress for a session."""
        # Create session first
        session_id = progress_tracker.create_session(**sample_session_data)
        
        # Update progress
        update = progress_tracker.update_progress(
            session_id=session_id,
            step_number=3,
            operation="Processing submission 1",
            submission_index=0,
            status="processing",
            details="Analyzing answers",
            metrics={"processing_time": 1.5, "accuracy": 0.95}
        )
        
        assert update is not None
        assert update.session_id == session_id
        assert update.step_number == 3
        assert update.operation == "Processing submission 1"
        assert update.percentage > 0
        
        # Verify database record
        db_update = db.session.query(ProgressUpdate).filter_by(
            session_id=session_id
        ).first()
        
        assert db_update is not None
        assert db_update.step_number == 3
        assert db_update.details == "Analyzing answers"
    
    def test_update_progress_nonexistent_session(self, progress_tracker):
        """Test updating progress for non-existent session."""
        update = progress_tracker.update_progress(
            session_id="nonexistent",
            step_number=1,
            operation="Test"
        )
        
        assert update is None
    
    def test_complete_session(self, progress_tracker, sample_session_data):
        """Test completing a session."""
        # Create and update session
        session_id = progress_tracker.create_session(**sample_session_data)
        progress_tracker.update_progress(
            session_id=session_id,
            step_number=5,
            operation="Halfway done"
        )
        
        # Complete session
        success = progress_tracker.complete_session(
            session_id=session_id,
            status="completed",
            final_message="All submissions processed"
        )
        
        assert success is True
        
        # Verify database state
        db_session = db.session.query(ProgressSession).filter_by(
            session_id=session_id
        ).first()
        
        assert db_session.status == "completed"
        assert db_session.end_time is not None
        
        # Verify final update
        final_update = db.session.query(ProgressUpdate).filter_by(
            session_id=session_id
        ).order_by(ProgressUpdate.created_at.desc()).first()
        
        assert final_update.percentage == 100.0
        assert final_update.status == "completed"
        assert final_update.details == "All submissions processed"
        
        # Verify removed from cache
        assert session_id not in progress_tracker._active_sessions_cache
    
    def test_get_session_progress(self, progress_tracker, sample_session_data):
        """Test getting current session progress."""
        # Create and update session
        session_id = progress_tracker.create_session(**sample_session_data)
        progress_tracker.update_progress(
            session_id=session_id,
            step_number=7,
            operation="Almost done",
            details="Final processing"
        )
        
        # Get progress
        progress = progress_tracker.get_session_progress(session_id)
        
        assert progress is not None
        assert progress["session_id"] == session_id
        assert progress["current_step"] == 7
        assert progress["status"] == "active"
        assert progress["latest_operation"] == "Almost done"
        assert progress["latest_details"] == "Final processing"
        assert "latest_update_time" in progress
    
    def test_get_session_history(self, progress_tracker, sample_session_data):
        """Test getting session progress history."""
        # Create session and add multiple updates
        session_id = progress_tracker.create_session(**sample_session_data)
        
        updates = [
            {"step_number": 1, "operation": "Starting"},
            {"step_number": 3, "operation": "Processing"},
            {"step_number": 7, "operation": "Finalizing"}
        ]
        
        for update_data in updates:
            progress_tracker.update_progress(
                session_id=session_id,
                **update_data
            )
        
        # Get history
        history = progress_tracker.get_session_history(session_id)
        
        assert len(history) == 3
        assert history[0]["step_number"] == 1
        assert history[1]["step_number"] == 3
        assert history[2]["step_number"] == 7
        
        # Verify chronological order
        timestamps = [update["created_at"] for update in history]
        assert timestamps == sorted(timestamps)
    
    def test_recover_session_resume(self, progress_tracker, sample_session_data):
        """Test resuming a failed session."""
        # Create and fail session
        session_id = progress_tracker.create_session(**sample_session_data)
        progress_tracker.update_progress(
            session_id=session_id,
            step_number=5,
            operation="Processing",
            status="failed"
        )
        progress_tracker.complete_session(session_id, status="failed")
        
        # Recover session
        success = progress_tracker.recover_session(
            session_id=session_id,
            recovery_type="resume",
            recovery_data={"reason": "Network error resolved"}
        )
        
        assert success is True
        
        # Verify session state
        db_session = db.session.query(ProgressSession).filter_by(
            session_id=session_id
        ).first()
        
        assert db_session.status == "active"
        assert db_session.end_time is None
        
        # Verify recovery record
        recovery = db.session.query(ProgressRecovery).filter_by(
            session_id=session_id
        ).first()
        
        assert recovery is not None
        assert recovery.recovery_type == "resume"
        assert recovery.recovery_status == "pending"
        
        # Verify back in cache
        assert session_id in progress_tracker._active_sessions_cache
    
    def test_recover_session_restart(self, progress_tracker, sample_session_data):
        """Test restarting a session from beginning."""
        # Create and complete session
        session_id = progress_tracker.create_session(**sample_session_data)
        progress_tracker.update_progress(session_id=session_id, step_number=8, operation="Near end")
        progress_tracker.complete_session(session_id, status="completed")
        
        # Restart session
        success = progress_tracker.recover_session(
            session_id=session_id,
            recovery_type="restart"
        )
        
        assert success is True
        
        # Verify session reset
        db_session = db.session.query(ProgressSession).filter_by(
            session_id=session_id
        ).first()
        
        assert db_session.current_step == 0
        assert db_session.current_submission == 0
        assert db_session.status == "active"
    
    def test_get_active_sessions(self, progress_tracker):
        """Test getting active sessions."""
        # Create multiple sessions
        sessions = [
            {"session_id": "active_1", "total_steps": 5, "user_id": "user1"},
            {"session_id": "active_2", "total_steps": 8, "user_id": "user2"},
            {"session_id": "completed_1", "total_steps": 3, "user_id": "user1"}
        ]
        
        for session_data in sessions:
            progress_tracker.create_session(**session_data)
        
        # Complete one session
        progress_tracker.complete_session("completed_1", status="completed")
        
        # Get all active sessions
        active_sessions = progress_tracker.get_active_sessions()
        assert len(active_sessions) == 2
        
        session_ids = [s["session_id"] for s in active_sessions]
        assert "active_1" in session_ids
        assert "active_2" in session_ids
        assert "completed_1" not in session_ids
        
        # Get active sessions for specific user
        user1_sessions = progress_tracker.get_active_sessions(user_id="user1")
        assert len(user1_sessions) == 1
        assert user1_sessions[0]["session_id"] == "active_1"
    
    def test_cleanup_old_sessions(self, progress_tracker):
        """Test cleaning up old completed sessions."""
        # Create sessions with different completion times
        old_session = progress_tracker.create_session(
            session_id="old_session",
            total_steps=3
        )
        recent_session = progress_tracker.create_session(
            session_id="recent_session",
            total_steps=3
        )
        
        # Complete sessions
        progress_tracker.complete_session(old_session, status="completed")
        progress_tracker.complete_session(recent_session, status="completed")
        
        # Manually set old completion time
        old_db_session = db.session.query(ProgressSession).filter_by(
            session_id=old_session
        ).first()
        old_db_session.end_time = datetime.utcnow() - timedelta(days=10)
        db.session.commit()
        
        # Cleanup old sessions (older than 7 days)
        cleaned_count = progress_tracker.cleanup_old_sessions(days_old=7)
        
        assert cleaned_count == 1
        
        # Verify old session is gone
        remaining_sessions = db.session.query(ProgressSession).all()
        session_ids = [s.session_id for s in remaining_sessions]
        assert old_session not in session_ids
        assert recent_session in session_ids
    
    def test_performance_metrics(self, progress_tracker, sample_session_data):
        """Test recording and retrieving performance metrics."""
        # Create session and update with metrics
        session_id = progress_tracker.create_session(**sample_session_data)
        
        metrics_data = {
            "processing_time": 2.5,
            "memory_usage": 150.0,
            "cpu_usage": 75.5
        }
        
        progress_tracker.update_progress(
            session_id=session_id,
            step_number=1,
            operation="Processing",
            metrics=metrics_data
        )
        
        # Get metrics
        metrics = progress_tracker.get_performance_metrics(
            session_id=session_id,
            hours=1
        )
        
        assert len(metrics) == 3
        
        metric_types = [m["metric_type"] for m in metrics]
        assert "processing_time" in metric_types
        assert "memory_usage" in metric_types
        assert "cpu_usage" in metric_types
        
        # Test filtering by metric type
        cpu_metrics = progress_tracker.get_performance_metrics(
            session_id=session_id,
            metric_type="cpu_usage"
        )
        
        assert len(cpu_metrics) == 1
        assert cpu_metrics[0]["metric_value"] == 75.5
    
    def test_create_progress_callback(self, progress_tracker, sample_session_data):
        """Test creating progress callback function."""
        session_id = progress_tracker.create_session(**sample_session_data)
        callback = progress_tracker.create_progress_callback(session_id)
        
        # Test with ProcessingProgress-like object
        class MockProgress:
            def __init__(self):
                self.current_step = 3
                self.current_operation = "Testing"
                self.submission_index = 1
                self.status = "processing"
                self.details = "Mock progress"
        
        mock_progress = MockProgress()
        callback(mock_progress)
        
        # Verify update was recorded
        updates = progress_tracker.get_session_history(session_id)
        assert len(updates) == 1
        assert updates[0]["step_number"] == 3
        assert updates[0]["operation"] == "Testing"
        
        # Test with dictionary
        dict_progress = {
            "current_step": 5,
            "operation": "Dictionary test",
            "submission_index": 0,
            "status": "processing",
            "details": "Testing dict format"
        }
        
        callback(dict_progress)
        
        # Verify second update
        updates = progress_tracker.get_session_history(session_id)
        assert len(updates) == 2
        assert updates[1]["step_number"] == 5
        assert updates[1]["operation"] == "Dictionary test"
    
    def test_websocket_integration(self, progress_tracker, websocket_manager, sample_session_data):
        """Test WebSocket manager integration."""
        websocket_manager.emit_to_room.return_value = True
        
        # Create session and update progress
        session_id = progress_tracker.create_session(**sample_session_data)
        progress_tracker.update_progress(
            session_id=session_id,
            step_number=2,
            operation="WebSocket test"
        )
        
        # Verify WebSocket emission
        websocket_manager.emit_to_room.assert_called()
        call_args = websocket_manager.emit_to_room.call_args
        
        assert call_args[0][0] == f'progress_{session_id}'  # room
        assert call_args[0][1] == 'progress_update'  # event
        assert call_args[1]['priority'] == MessagePriority.NORMAL
    
    def test_realtime_service_fallback(self, progress_tracker, sample_session_data):
        """Test fallback to realtime service when WebSocket fails."""
        # Set up WebSocket to fail
        progress_tracker.websocket_manager.emit_to_room.return_value = False
        
        # Set up realtime service mock
        mock_realtime = Mock()
        progress_tracker.set_realtime_service(mock_realtime)
        
        # Create session and update
        session_id = progress_tracker.create_session(**sample_session_data)
        progress_tracker.update_progress(
            session_id=session_id,
            step_number=1,
            operation="Fallback test"
        )
        
        # Verify realtime service was called
        mock_realtime.emit_progress_update.assert_called_once()
    
    def test_error_handling(self, progress_tracker):
        """Test error handling in various scenarios."""
        # Test database error during session creation
        with patch('src.database.models.db.session.commit', side_effect=Exception("DB Error")):
            with pytest.raises(Exception):
                progress_tracker.create_session(
                    session_id="error_test",
                    total_steps=5
                )
        
        # Test progress update with invalid session
        update = progress_tracker.update_progress(
            session_id="nonexistent",
            step_number=1,
            operation="Should fail"
        )
        assert update is None
        
        # Test completion of nonexistent session
        success = progress_tracker.complete_session("nonexistent")
        assert success is False
    
    def test_percentage_calculation(self, progress_tracker):
        """Test progress percentage calculation."""
        # Create session with multiple submissions
        session_id = progress_tracker.create_session(
            session_id="percentage_test",
            total_steps=10,
            total_submissions=4
        )
        
        # Test various progress points
        test_cases = [
            (2, 0, 5.0),   # 2/10 steps of first submission
            (10, 0, 25.0), # Completed first submission
            (5, 1, 37.5),  # Halfway through second submission
            (10, 3, 100.0) # Completed all submissions
        ]
        
        for step, submission, expected_percentage in test_cases:
            update = progress_tracker.update_progress(
                session_id=session_id,
                step_number=step,
                operation=f"Step {step}, Submission {submission}",
                submission_index=submission
            )
            
            assert abs(update.percentage - expected_percentage) < 0.1
    
    def test_session_caching(self, progress_tracker, sample_session_data):
        """Test session caching mechanism."""
        # Create session
        session_id = progress_tracker.create_session(**sample_session_data)
        
        # Verify in cache
        assert session_id in progress_tracker._active_sessions_cache
        
        # Clear cache and verify database lookup works
        progress_tracker._active_sessions_cache.clear()
        
        # Update should still work (will load from database)
        update = progress_tracker.update_progress(
            session_id=session_id,
            step_number=1,
            operation="Cache test"
        )
        
        assert update is not None
        # Should be back in cache now
        assert session_id in progress_tracker._active_sessions_cache
    
    def test_concurrent_access(self, progress_tracker, sample_session_data):
        """Test thread safety with concurrent access."""
        import threading
        
        session_id = progress_tracker.create_session(**sample_session_data)
        results = []
        
        def update_progress(step):
            update = progress_tracker.update_progress(
                session_id=session_id,
                step_number=step,
                operation=f"Concurrent step {step}"
            )
            results.append(update is not None)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_progress, args=(i + 1,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all updates succeeded
        assert all(results)
        assert len(results) == 5
        
        # Verify all updates were recorded
        history = progress_tracker.get_session_history(session_id)
        assert len(history) == 5