"""Tests for Unified Progress Service."""

import pytest
from unittest.mock import Mock, patch

from src.services.progress_service import ProgressService
from src.services.websocket_manager import WebSocketManager


class TestProgressService:
    """Test cases for ProgressService."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create a mock WebSocket manager."""
        return Mock(spec=WebSocketManager)
    
    @pytest.fixture
    def progress_service_full(self, websocket_manager):
        """Create a progress service with both trackers enabled."""
        with patch('src.services.progress_service.PersistentProgressTracker') as mock_persistent, \
             patch('src.services.progress_service.ProgressTracker') as mock_memory:
            
            service = ProgressService(
                websocket_manager=websocket_manager,
                enable_persistence=True,
                fallback_to_memory=True
            )
            
            # Set up mocks
            service.persistent_tracker = mock_persistent.return_value
            service.memory_tracker = mock_memory.return_value
            
            return service
    
    @pytest.fixture
    def progress_service_memory_only(self, websocket_manager):
        """Create a progress service with only memory tracker."""
        with patch('src.services.progress_service.ProgressTracker') as mock_memory:
            service = ProgressService(
                websocket_manager=websocket_manager,
                enable_persistence=False,
                fallback_to_memory=True
            )
            
            service.memory_tracker = mock_memory.return_value
            
            return service
    
    @pytest.fixture
    def progress_service_persistent_only(self, websocket_manager):
        """Create a progress service with only persistent tracker."""
        with patch('src.services.progress_service.PersistentProgressTracker') as mock_persistent:
            service = ProgressService(
                websocket_manager=websocket_manager,
                enable_persistence=True,
                fallback_to_memory=False
            )
            
            service.persistent_tracker = mock_persistent.return_value
            
            return service
    
    def test_initialization_full_service(self, websocket_manager):
        """Test initialization with both trackers enabled."""
        with patch('src.services.progress_service.PersistentProgressTracker') as mock_persistent, \
             patch('src.services.progress_service.ProgressTracker') as mock_memory:
            
            service = ProgressService(
                websocket_manager=websocket_manager,
                enable_persistence=True,
                fallback_to_memory=True
            )
            
            assert service.websocket_manager == websocket_manager
            assert service.enable_persistence is True
            assert service.fallback_to_memory is True
            
            # Verify both trackers were initialized
            mock_persistent.assert_called_once_with(websocket_manager=websocket_manager)
            mock_memory.assert_called_once_with(websocket_manager=websocket_manager)
    
    def test_initialization_memory_only(self, websocket_manager):
        """Test initialization with only memory tracker."""
        with patch('src.services.progress_service.PersistentProgressTracker') as mock_persistent, \
             patch('src.services.progress_service.ProgressTracker') as mock_memory:
            
            service = ProgressService(
                websocket_manager=websocket_manager,
                enable_persistence=False,
                fallback_to_memory=True
            )
            
            # Only memory tracker should be initialized
            mock_persistent.assert_not_called()
            mock_memory.assert_called_once_with(websocket_manager=websocket_manager)
    
    def test_initialization_persistent_failure_with_fallback(self, websocket_manager):
        """Test initialization when persistent tracker fails but fallback is enabled."""
        with patch('src.services.progress_service.PersistentProgressTracker', side_effect=Exception("DB Error")), \
             patch('src.services.progress_service.ProgressTracker') as mock_memory:
            
            service = ProgressService(
                websocket_manager=websocket_manager,
                enable_persistence=True,
                fallback_to_memory=True
            )
            
            # Memory tracker should still be initialized
            mock_memory.assert_called_once_with(websocket_manager=websocket_manager)
            assert service.persistent_tracker is None
    
    def test_set_realtime_service(self, progress_service_full):
        """Test setting realtime service on both trackers."""
        mock_realtime = Mock()
        progress_service_full.set_realtime_service(mock_realtime)
        
        progress_service_full.persistent_tracker.set_realtime_service.assert_called_once_with(mock_realtime)
        progress_service_full.memory_tracker.set_realtime_service.assert_called_once_with(mock_realtime)
    
    def test_create_session_persistent_success(self, progress_service_full):
        """Test creating session with persistent tracker success."""
        session_id = "test_session"
        progress_service_full.persistent_tracker.create_session.return_value = session_id
        
        result = progress_service_full.create_session(
            session_id=session_id,
            total_steps=10,
            user_id="user123"
        )
        
        assert result == session_id
        progress_service_full.persistent_tracker.create_session.assert_called_once()
        progress_service_full.memory_tracker.create_session.assert_not_called()
    
    def test_create_session_persistent_failure_fallback(self, progress_service_full):
        """Test creating session with persistent tracker failure and fallback."""
        session_id = "test_session"
        progress_service_full.persistent_tracker.create_session.side_effect = Exception("DB Error")
        progress_service_full.memory_tracker.create_session.return_value = session_id
        
        result = progress_service_full.create_session(
            session_id=session_id,
            total_steps=10
        )
        
        assert result == session_id
        progress_service_full.persistent_tracker.create_session.assert_called_once()
        progress_service_full.memory_tracker.create_session.assert_called_once()
    
    def test_create_session_memory_only(self, progress_service_memory_only):
        """Test creating session with memory tracker only."""
        session_id = "test_session"
        progress_service_memory_only.memory_tracker.create_session.return_value = session_id
        
        result = progress_service_memory_only.create_session(
            session_id=session_id,
            total_steps=5
        )
        
        assert result == session_id
        progress_service_memory_only.memory_tracker.create_session.assert_called_once()
    
    def test_update_progress_persistent_success(self, progress_service_full):
        """Test updating progress with persistent tracker success."""
        session_id = "test_session"
        mock_update = Mock()
        progress_service_full.persistent_tracker.update_progress.return_value = mock_update
        
        result = progress_service_full.update_progress(
            session_id=session_id,
            step_number=3,
            operation="Processing",
            details="Test details"
        )
        
        assert result is True
        progress_service_full.persistent_tracker.update_progress.assert_called_once()
        progress_service_full.memory_tracker.update_progress.assert_not_called()
    
    def test_update_progress_persistent_failure_fallback(self, progress_service_full):
        """Test updating progress with persistent tracker failure and fallback."""
        session_id = "test_session"
        progress_service_full.persistent_tracker.update_progress.side_effect = Exception("DB Error")
        
        result = progress_service_full.update_progress(
            session_id=session_id,
            step_number=3,
            operation="Processing"
        )
        
        assert result is True
        progress_service_full.persistent_tracker.update_progress.assert_called_once()
        progress_service_full.memory_tracker.update_progress.assert_called_once()
    
    def test_update_progress_both_fail(self, progress_service_full):
        """Test updating progress when both trackers fail."""
        session_id = "test_session"
        progress_service_full.persistent_tracker.update_progress.side_effect = Exception("DB Error")
        progress_service_full.memory_tracker.update_progress.side_effect = Exception("Memory Error")
        
        result = progress_service_full.update_progress(
            session_id=session_id,
            step_number=3,
            operation="Processing"
        )
        
        assert result is False
    
    def test_complete_session_persistent_success(self, progress_service_full):
        """Test completing session with persistent tracker success."""
        session_id = "test_session"
        progress_service_full.persistent_tracker.complete_session.return_value = True
        
        result = progress_service_full.complete_session(
            session_id=session_id,
            status="completed",
            final_message="All done"
        )
        
        assert result is True
        progress_service_full.persistent_tracker.complete_session.assert_called_once_with(
            session_id=session_id,
            status="completed",
            final_message="All done"
        )
        progress_service_full.memory_tracker.update_progress.assert_not_called()
    
    def test_complete_session_persistent_failure_fallback(self, progress_service_full):
        """Test completing session with persistent tracker failure and fallback."""
        session_id = "test_session"
        progress_service_full.persistent_tracker.complete_session.side_effect = Exception("DB Error")
        
        result = progress_service_full.complete_session(
            session_id=session_id,
            status="completed"
        )
        
        assert result is True
        progress_service_full.memory_tracker.update_progress.assert_called_once()
    
    def test_get_session_progress_persistent_success(self, progress_service_full):
        """Test getting session progress with persistent tracker success."""
        session_id = "test_session"
        expected_progress = {"session_id": session_id, "percentage": 50.0}
        progress_service_full.persistent_tracker.get_session_progress.return_value = expected_progress
        
        result = progress_service_full.get_session_progress(session_id)
        
        assert result == expected_progress
        progress_service_full.persistent_tracker.get_session_progress.assert_called_once_with(session_id)
        progress_service_full.memory_tracker.get_latest_progress.assert_not_called()
    
    def test_get_session_progress_persistent_failure_fallback(self, progress_service_full):
        """Test getting session progress with persistent tracker failure and fallback."""
        session_id = "test_session"
        expected_progress = {"session_id": session_id, "percentage": 30.0}
        progress_service_full.persistent_tracker.get_session_progress.side_effect = Exception("DB Error")
        progress_service_full.memory_tracker.get_latest_progress.return_value = expected_progress
        
        result = progress_service_full.get_session_progress(session_id)
        
        assert result == expected_progress
        progress_service_full.memory_tracker.get_latest_progress.assert_called_once_with(session_id)
    
    def test_get_session_history_persistent_only(self, progress_service_full):
        """Test getting session history (only available in persistent tracker)."""
        session_id = "test_session"
        expected_history = [{"step": 1}, {"step": 2}]
        progress_service_full.persistent_tracker.get_session_history.return_value = expected_history
        
        result = progress_service_full.get_session_history(session_id)
        
        assert result == expected_history
        progress_service_full.persistent_tracker.get_session_history.assert_called_once_with(session_id)
    
    def test_get_session_history_memory_fallback(self, progress_service_memory_only):
        """Test getting session history with memory tracker fallback."""
        session_id = "test_session"
        expected_history = [{"step": 1}]
        progress_service_memory_only.memory_tracker.get_progress_history.return_value = expected_history
        
        result = progress_service_memory_only.get_session_history(session_id)
        
        assert result == expected_history
        progress_service_memory_only.memory_tracker.get_progress_history.assert_called_once_with(session_id)
    
    def test_recover_session_persistent_only(self, progress_service_full):
        """Test session recovery (only available in persistent tracker)."""
        session_id = "test_session"
        progress_service_full.persistent_tracker.recover_session.return_value = True
        
        result = progress_service_full.recover_session(
            session_id=session_id,
            recovery_type="resume"
        )
        
        assert result is True
        progress_service_full.persistent_tracker.recover_session.assert_called_once_with(
            session_id=session_id,
            recovery_type="resume",
            recovery_point=None,
            recovery_data=None
        )
    
    def test_recover_session_memory_only(self, progress_service_memory_only):
        """Test session recovery with memory tracker only (not supported)."""
        session_id = "test_session"
        
        result = progress_service_memory_only.recover_session(session_id)
        
        assert result is False
    
    def test_get_active_sessions_combined(self, progress_service_full):
        """Test getting active sessions from both trackers."""
        persistent_sessions = [{"session_id": "persistent_1"}]
        memory_sessions = {"memory_1": {"user_id": "user123"}}
        
        progress_service_full.persistent_tracker.get_active_sessions.return_value = persistent_sessions
        progress_service_full.memory_tracker.get_active_sessions.return_value = memory_sessions
        
        result = progress_service_full.get_active_sessions()
        
        assert len(result) == 2
        assert {"session_id": "persistent_1"} in result
        assert any(s["session_id"] == "memory_1" for s in result)
    
    def test_get_active_sessions_user_filter(self, progress_service_full):
        """Test getting active sessions with user filter."""
        user_id = "user123"
        persistent_sessions = [{"session_id": "persistent_1", "user_id": user_id}]
        memory_sessions = {
            "memory_1": {"user_id": user_id},
            "memory_2": {"user_id": "other_user"}
        }
        
        progress_service_full.persistent_tracker.get_active_sessions.return_value = persistent_sessions
        progress_service_full.memory_tracker.get_active_sessions.return_value = memory_sessions
        
        result = progress_service_full.get_active_sessions(user_id=user_id)
        
        # Should get persistent session + filtered memory session
        assert len(result) == 2
        progress_service_full.persistent_tracker.get_active_sessions.assert_called_once_with(user_id=user_id)
    
    def test_cleanup_old_sessions_combined(self, progress_service_full):
        """Test cleaning up old sessions from both trackers."""
        progress_service_full.persistent_tracker.cleanup_old_sessions.return_value = 3
        progress_service_full.memory_tracker.cleanup_old_sessions.return_value = 2
        
        result = progress_service_full.cleanup_old_sessions(days_old=7)
        
        assert result == 5
        progress_service_full.persistent_tracker.cleanup_old_sessions.assert_called_once_with(7)
        progress_service_full.memory_tracker.cleanup_old_sessions.assert_called_once()
    
    def test_get_performance_metrics_persistent_only(self, progress_service_full):
        """Test getting performance metrics (only available in persistent tracker)."""
        expected_metrics = [{"metric_type": "cpu", "value": 75.0}]
        progress_service_full.persistent_tracker.get_performance_metrics.return_value = expected_metrics
        
        result = progress_service_full.get_performance_metrics(
            session_id="test_session",
            metric_type="cpu",
            hours=12
        )
        
        assert result == expected_metrics
        progress_service_full.persistent_tracker.get_performance_metrics.assert_called_once_with(
            session_id="test_session",
            metric_type="cpu",
            hours=12
        )
    
    def test_get_performance_metrics_memory_only(self, progress_service_memory_only):
        """Test getting performance metrics with memory tracker only (not supported)."""
        result = progress_service_memory_only.get_performance_metrics()
        
        assert result == []
    
    def test_create_progress_callback(self, progress_service_full):
        """Test creating progress callback function."""
        session_id = "test_session"
        callback = progress_service_full.create_progress_callback(session_id)
        
        # Test with ProcessingProgress-like object
        class MockProgress:
            def __init__(self):
                self.current_step = 5
                self.current_operation = "Testing callback"
                self.submission_index = 1
                self.status = "processing"
                self.details = "Callback test"
        
        mock_progress = MockProgress()
        progress_service_full.persistent_tracker.update_progress.return_value = Mock()
        
        callback(mock_progress)
        
        # Verify update_progress was called with correct parameters
        progress_service_full.persistent_tracker.update_progress.assert_called_once()
        call_args = progress_service_full.persistent_tracker.update_progress.call_args[1]
        assert call_args['session_id'] == session_id
        assert call_args['step_number'] == 5
        assert call_args['operation'] == "Testing callback"
    
    def test_create_progress_callback_dict_format(self, progress_service_full):
        """Test progress callback with dictionary format."""
        session_id = "test_session"
        callback = progress_service_full.create_progress_callback(session_id)
        
        dict_progress = {
            "current_step": 3,
            "operation": "Dictionary test",
            "submission_index": 0,
            "status": "processing",
            "details": "Testing dict format"
        }
        
        progress_service_full.persistent_tracker.update_progress.return_value = Mock()
        
        callback(dict_progress)
        
        # Verify update_progress was called
        progress_service_full.persistent_tracker.update_progress.assert_called_once()
        call_args = progress_service_full.persistent_tracker.update_progress.call_args[1]
        assert call_args['step_number'] == 3
        assert call_args['operation'] == "Dictionary test"
    
    def test_get_service_status(self, progress_service_full):
        """Test getting service status."""
        status = progress_service_full.get_service_status()
        
        expected_status = {
            "persistent_tracker_available": True,
            "memory_tracker_available": True,
            "websocket_manager_available": True,
            "persistence_enabled": True,
            "fallback_enabled": True
        }
        
        assert status == expected_status
    
    def test_get_service_status_memory_only(self, progress_service_memory_only):
        """Test getting service status with memory tracker only."""
        status = progress_service_memory_only.get_service_status()
        
        assert status["persistent_tracker_available"] is False
        assert status["memory_tracker_available"] is True
        assert status["persistence_enabled"] is False
        assert status["fallback_enabled"] is True
    
    def test_error_handling_no_trackers(self, websocket_manager):
        """Test error handling when no trackers are available."""
        with patch('src.services.progress_service.PersistentProgressTracker', side_effect=Exception("DB Error")), \
             patch('src.services.progress_service.ProgressTracker', side_effect=Exception("Memory Error")):
            
            with pytest.raises(Exception):
                ProgressService(
                    websocket_manager=websocket_manager,
                    enable_persistence=True,
                    fallback_to_memory=False
                )
    
    def test_create_session_override_persistence(self, progress_service_full):
        """Test creating session with persistence override."""
        session_id = "test_session"
        progress_service_full.memory_tracker.create_session.return_value = session_id
        
        # Override to use memory tracker even though persistence is enabled
        result = progress_service_full.create_session(
            session_id=session_id,
            total_steps=5,
            use_persistence=False
        )
        
        assert result == session_id
        progress_service_full.persistent_tracker.create_session.assert_not_called()
        progress_service_full.memory_tracker.create_session.assert_called_once()
    
    def test_concurrent_operations(self, progress_service_full):
        """Test concurrent operations on the progress service."""
        import threading
        
        session_id = "concurrent_test"
        results = []
        
        def update_progress(step):
            progress_service_full.persistent_tracker.update_progress.return_value = Mock()
            result = progress_service_full.update_progress(
                session_id=session_id,
                step_number=step,
                operation=f"Concurrent step {step}"
            )
            results.append(result)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_progress, args=(i + 1,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all operations succeeded
        assert all(results)
        assert len(results) == 5
        assert progress_service_full.persistent_tracker.update_progress.call_count == 5