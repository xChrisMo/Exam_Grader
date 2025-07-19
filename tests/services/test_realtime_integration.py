"""Tests for real-time communication integration."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.services.realtime_service import RealtimeService
from src.services.websocket_manager import WebSocketManager, ConnectionInfo, MessagePriority
from src.services.progress_tracker import ProgressTracker, ProgressUpdate


class TestRealtimeIntegration:
    """Test real-time communication integration."""
    
    @pytest.fixture
    def mock_app(self):
        """Create mock Flask app."""
        app = Mock()
        app.config = {'SECRET_KEY': 'test'}
        return app
    
    @pytest.fixture
    def mock_socketio(self):
        """Create mock SocketIO."""
        return Mock()
    
    @pytest.fixture
    def websocket_manager(self):
        """Create WebSocket manager."""
        return WebSocketManager()
    
    @pytest.fixture
    def realtime_service(self, mock_app, websocket_manager):
        """Create realtime service with WebSocket manager."""
        with patch('src.services.realtime_service.SocketIO'):
            return RealtimeService(mock_app, websocket_manager)
    
    @pytest.fixture
    def progress_tracker(self, websocket_manager):
        """Create progress tracker with WebSocket manager."""
        return ProgressTracker(websocket_manager)
    
    def test_realtime_service_websocket_integration(self, realtime_service, websocket_manager):
        """Test realtime service WebSocket manager integration."""
        assert realtime_service.websocket_manager is websocket_manager
        assert hasattr(realtime_service, '_register_websocket_handlers')
    
    def test_progress_tracker_websocket_integration(self, progress_tracker, websocket_manager):
        """Test progress tracker WebSocket manager integration."""
        assert progress_tracker.websocket_manager is websocket_manager
        assert hasattr(progress_tracker, '_emit_progress_update')
    
    def test_dashboard_update_with_websocket_manager(self, realtime_service, websocket_manager):
        """Test dashboard update via WebSocket manager."""
        user_id = "test_user"
        update_data = {"type": "status", "message": "Test update"}
        
        # Mock WebSocket manager emit_to_user
        websocket_manager.emit_to_user = Mock(return_value=True)
        
        realtime_service.emit_dashboard_update(user_id, update_data)
        
        websocket_manager.emit_to_user.assert_called_once_with(
            user_id, 'dashboard_update', update_data, MessagePriority.NORMAL
        )
    
    def test_progress_update_with_websocket_manager(self, realtime_service, websocket_manager):
        """Test progress update via WebSocket manager."""
        session_id = "test_session"
        update_data = {"progress": 50, "message": "Processing..."}
        
        # Mock WebSocket manager emit_to_room
        websocket_manager.emit_to_room = Mock(return_value=True)
        
        realtime_service.emit_progress_update(session_id, update_data)
        
        websocket_manager.emit_to_room.assert_called_once_with(
            f"progress_{session_id}", 'progress_update', update_data, MessagePriority.NORMAL
        )
    
    def test_notification_with_high_priority(self, realtime_service, websocket_manager):
        """Test error notification with high priority."""
        user_id = "test_user"
        notification_data = {"type": "error", "message": "Critical error"}
        
        # Mock WebSocket manager emit_to_user
        websocket_manager.emit_to_user = Mock(return_value=True)
        
        realtime_service.emit_notification(user_id, notification_data)
        
        websocket_manager.emit_to_user.assert_called_once_with(
            user_id, 'notification', notification_data, MessagePriority.HIGH
        )
    
    def test_global_update_with_websocket_manager(self, realtime_service, websocket_manager):
        """Test global update via WebSocket manager."""
        update_data = {"type": "maintenance", "message": "System maintenance"}
        
        # Mock WebSocket manager emit_to_room
        websocket_manager.emit_to_room = Mock(return_value=True)
        
        realtime_service.emit_global_update(update_data)
        
        websocket_manager.emit_to_room.assert_called_once_with(
            "global_updates", 'global_update', update_data, MessagePriority.NORMAL
        )
    
    def test_progress_tracker_emit_integration(self, progress_tracker, websocket_manager):
        """Test progress tracker emission via WebSocket manager."""
        session_id = "test_session"
        progress_update = ProgressUpdate(
            progress_id="test_progress",
            session_id=session_id,
            current_step=5,
            total_steps=10,
            percentage=50.0,
            current_operation="Processing",
            estimated_time_remaining=30,
            timestamp=datetime.now()
        )
        
        # Mock WebSocket manager emit_to_room
        websocket_manager.emit_to_room = Mock(return_value=True)
        
        progress_tracker._emit_progress_update(session_id, progress_update)
        
        # Verify WebSocket manager was called
        websocket_manager.emit_to_room.assert_called_once()
        call_args = websocket_manager.emit_to_room.call_args
        assert call_args[0][0] == f"progress_{session_id}"
        assert call_args[0][1] == 'progress_update'
        assert call_args[0][3] == MessagePriority.NORMAL
    
    def test_fallback_to_socketio_when_websocket_manager_fails(self, realtime_service, websocket_manager):
        """Test fallback to direct SocketIO when WebSocket manager fails."""
        user_id = "test_user"
        update_data = {"type": "status", "message": "Test update"}
        
        # Mock WebSocket manager to fail
        websocket_manager.emit_to_user = Mock(return_value=False)
        
        with patch('src.services.realtime_service.emit') as mock_emit:
            realtime_service.emit_dashboard_update(user_id, update_data)
            
            # Verify fallback was used
            mock_emit.assert_called_once_with(
                'dashboard_update', update_data, room=f"dashboard_{user_id}", namespace='/'
            )
    
    def test_progress_room_management(self, realtime_service, websocket_manager):
        """Test progress room joining and leaving."""
        session_id = "test_session"
        progress_id = "test_progress"
        
        # Mock WebSocket manager room methods
        websocket_manager.join_room = Mock(return_value=True)
        websocket_manager.leave_room = Mock(return_value=True)
        
        # Test joining progress room
        result = realtime_service.join_progress_room(session_id, progress_id)
        assert result is True
        websocket_manager.join_room.assert_called_once_with(
            session_id, f"progress_{progress_id}"
        )
        
        # Test leaving progress room
        result = realtime_service.leave_progress_room(session_id, progress_id)
        assert result is True
        websocket_manager.leave_room.assert_called_once_with(
            session_id, f"progress_{progress_id}"
        )
    
    def test_websocket_stats_retrieval(self, realtime_service, websocket_manager):
        """Test WebSocket statistics retrieval."""
        mock_stats = {
            'total_connections': 10,
            'active_rooms': 5,
            'messages_sent': 100
        }
        
        websocket_manager.get_health_stats = Mock(return_value=mock_stats)
        
        stats = realtime_service.get_websocket_stats()
        assert stats == mock_stats
        websocket_manager.get_health_stats.assert_called_once()
    
    def test_user_disconnection(self, realtime_service, websocket_manager):
        """Test user session disconnection."""
        user_id = "test_user"
        reason = "Admin disconnect"
        
        websocket_manager.disconnect_user = Mock()
        
        realtime_service.disconnect_user_sessions(user_id, reason)
        
        websocket_manager.disconnect_user.assert_called_once_with(user_id, reason)
    
    def test_realtime_service_without_websocket_manager(self, mock_app):
        """Test realtime service fallback when no WebSocket manager is provided."""
        with patch('src.services.realtime_service.SocketIO'):
            service = RealtimeService(mock_app)
            assert service.websocket_manager is None
            
            # Test that methods still work without WebSocket manager
            with patch('src.services.realtime_service.emit') as mock_emit:
                service.emit_dashboard_update("user1", {"test": "data"})
                mock_emit.assert_called_once()
    
    def test_progress_tracker_realtime_service_integration(self, progress_tracker):
        """Test progress tracker integration with realtime service."""
        mock_realtime_service = Mock()
        progress_tracker.set_realtime_service(mock_realtime_service)
        
        assert progress_tracker._realtime_service is mock_realtime_service
        
        # Test emission via realtime service when WebSocket manager is not available
        progress_tracker.websocket_manager = None
        session_id = "test_session"
        progress_update = ProgressUpdate(
            progress_id="test_progress",
            session_id=session_id,
            current_step=1,
            total_steps=10,
            percentage=10.0,
            current_operation="Starting",
            estimated_time_remaining=90,
            timestamp=datetime.now()
        )
        
        progress_tracker._emit_progress_update(session_id, progress_update)
        
        mock_realtime_service.emit_progress_update.assert_called_once()
    
    def test_connection_handler_registration(self, realtime_service, websocket_manager):
        """Test WebSocket connection handler registration."""
        websocket_manager.add_connection_handler = Mock()
        websocket_manager.add_disconnection_handler = Mock()
        
        realtime_service._register_websocket_handlers()
        
        # Verify handlers were registered
        websocket_manager.add_connection_handler.assert_called_once()
        websocket_manager.add_disconnection_handler.assert_called_once()
    
    def test_auto_dashboard_room_join(self, realtime_service, websocket_manager):
        """Test automatic dashboard room joining on connection."""
        user_id = "test_user"
        session_id = "test_session"
        
        # Mock connection info
        connection_info = ConnectionInfo(
            session_id=session_id,
            user_id=user_id,
            connected_at=datetime.now()
        )
        
        websocket_manager.join_room = Mock()
        websocket_manager.add_connection_handler = Mock()
        websocket_manager.add_disconnection_handler = Mock()
        
        # Register handlers
        realtime_service._register_websocket_handlers()
        
        # Get the connection handler
        connection_handler = websocket_manager.add_connection_handler.call_args[0][0]
        
        # Simulate connection
        connection_handler(connection_info)
        
        # Verify dashboard room join
        websocket_manager.join_room.assert_called_once_with(
            session_id, f"dashboard_{user_id}"
        )