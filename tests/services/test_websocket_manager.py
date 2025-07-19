"""Tests for WebSocket Manager."""

import pytest
import time
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.services.websocket_manager import (
    WebSocketManager, ConnectionInfo, ConnectionStatus, 
    MessagePriority, QueuedMessage
)


class TestWebSocketManager:
    """Test cases for WebSocket Manager."""
    
    @pytest.fixture
    def mock_socketio(self):
        """Create mock SocketIO instance."""
        socketio = Mock()
        socketio.emit = Mock()
        return socketio
    
    @pytest.fixture
    def mock_app(self):
        """Create mock Flask app."""
        app = Mock()
        return app
    
    @pytest.fixture
    def websocket_manager(self, mock_socketio, mock_app):
        """Create WebSocket manager instance."""
        with patch('src.services.websocket_manager.Thread'):
            manager = WebSocketManager(mock_socketio, mock_app)
            return manager
    
    def test_initialization(self, mock_socketio, mock_app):
        """Test WebSocket manager initialization."""
        with patch('src.services.websocket_manager.Thread'):
            manager = WebSocketManager(mock_socketio, mock_app)
            
            assert manager.socketio == mock_socketio
            assert manager.app == mock_app
            assert isinstance(manager.connections, dict)
            assert isinstance(manager.user_sessions, dict)
            assert isinstance(manager.room_members, dict)
            assert isinstance(manager.message_queue, dict)
            assert isinstance(manager.health_stats, dict)
    
    def test_connection_info_creation(self):
        """Test ConnectionInfo creation and serialization."""
        connection = ConnectionInfo(
            session_id="test_session",
            user_id="test_user",
            connected_at=datetime.now(),
            last_ping=datetime.now(),
            status=ConnectionStatus.CONNECTED,
            rooms=set(["room1", "room2"]),
            client_info={"ip": "127.0.0.1"}
        )
        
        # Test to_dict method
        data = connection.to_dict()
        assert data['session_id'] == "test_session"
        assert data['user_id'] == "test_user"
        assert data['status'] == "connected"
        assert set(data['rooms']) == {"room1", "room2"}
        assert data['client_info'] == {"ip": "127.0.0.1"}
    
    def test_join_room(self, websocket_manager):
        """Test joining a room."""
        session_id = "test_session"
        room_name = "test_room"
        
        # Create a connection first
        connection = ConnectionInfo(
            session_id=session_id,
            user_id="test_user",
            connected_at=datetime.now(),
            last_ping=datetime.now(),
            status=ConnectionStatus.CONNECTED,
            rooms=set(),
            client_info={}
        )
        websocket_manager.connections[session_id] = connection
        
        with patch('src.services.websocket_manager.join_room') as mock_join:
            success = websocket_manager.join_room(session_id, room_name)
            
            assert success is True
            assert room_name in connection.rooms
            assert session_id in websocket_manager.room_members[room_name]
            mock_join.assert_called_once_with(room_name, sid=session_id)
    
    def test_leave_room(self, websocket_manager):
        """Test leaving a room."""
        session_id = "test_session"
        room_name = "test_room"
        
        # Create a connection with room membership
        connection = ConnectionInfo(
            session_id=session_id,
            user_id="test_user",
            connected_at=datetime.now(),
            last_ping=datetime.now(),
            status=ConnectionStatus.CONNECTED,
            rooms={room_name},
            client_info={}
        )
        websocket_manager.connections[session_id] = connection
        websocket_manager.room_members[room_name] = {session_id}
        
        with patch('src.services.websocket_manager.leave_room') as mock_leave:
            success = websocket_manager.leave_room(session_id, room_name)
            
            assert success is True
            assert room_name not in connection.rooms
            assert room_name not in websocket_manager.room_members
            mock_leave.assert_called_once_with(room_name, sid=session_id)
    
    def test_emit_to_room(self, websocket_manager):
        """Test emitting message to room."""
        room_name = "test_room"
        event = "test_event"
        data = {"message": "test"}
        
        success = websocket_manager.emit_to_room(room_name, event, data)
        
        assert success is True
        websocket_manager.socketio.emit.assert_called_once()
        call_args = websocket_manager.socketio.emit.call_args
        assert call_args[0][0] == event
        assert call_args[1]['room'] == room_name
        assert websocket_manager.health_stats['total_messages_sent'] == 1
    
    def test_emit_to_user_online(self, websocket_manager):
        """Test emitting message to online user."""
        user_id = "test_user"
        session_id = "test_session"
        event = "test_event"
        data = {"message": "test"}
        
        # Set up user session
        websocket_manager.user_sessions[user_id] = {session_id}
        
        success = websocket_manager.emit_to_user(user_id, event, data)
        
        assert success is True
        websocket_manager.socketio.emit.assert_called_once()
        assert websocket_manager.health_stats['total_messages_sent'] == 1
    
    def test_emit_to_user_offline(self, websocket_manager):
        """Test emitting message to offline user (should queue)."""
        user_id = "test_user"
        event = "test_event"
        data = {"message": "test"}
        priority = MessagePriority.HIGH
        
        success = websocket_manager.emit_to_user(user_id, event, data, priority)
        
        assert success is False  # User is offline
        # Check that message was queued
        queue_key = f"user:{user_id}"
        assert queue_key in websocket_manager.message_queue
        assert len(websocket_manager.message_queue[queue_key]) == 1
        
        queued_message = websocket_manager.message_queue[queue_key][0]
        assert queued_message.event == event
        assert queued_message.priority == priority
    
    def test_message_queuing_and_delivery(self, websocket_manager):
        """Test message queuing and delivery on reconnection."""
        user_id = "test_user"
        session_id = "test_session"
        event = "test_event"
        data = {"message": "test"}
        
        # Queue a message for offline user
        websocket_manager.emit_to_user(user_id, event, data, MessagePriority.HIGH)
        
        # Verify message is queued
        queue_key = f"user:{user_id}"
        assert len(websocket_manager.message_queue[queue_key]) == 1
        
        # Simulate user connection
        connection = ConnectionInfo(
            session_id=session_id,
            user_id=user_id,
            connected_at=datetime.now(),
            last_ping=datetime.now(),
            status=ConnectionStatus.CONNECTED,
            rooms=set(),
            client_info={}
        )
        websocket_manager.connections[session_id] = connection
        
        # Deliver queued messages
        websocket_manager._deliver_queued_messages(session_id)
        
        # Verify message was delivered and queue is empty
        websocket_manager.socketio.emit.assert_called()
        assert len(websocket_manager.message_queue[queue_key]) == 0
    
    def test_connection_health_stats(self, websocket_manager):
        """Test health statistics tracking."""
        # Initial stats
        stats = websocket_manager.get_health_stats()
        assert stats['active_connections'] == 0
        assert stats['total_messages_sent'] == 0
        
        # Add a connection
        session_id = "test_session"
        connection = ConnectionInfo(
            session_id=session_id,
            user_id="test_user",
            connected_at=datetime.now(),
            last_ping=datetime.now(),
            status=ConnectionStatus.CONNECTED,
            rooms=set(),
            client_info={}
        )
        websocket_manager.connections[session_id] = connection
        websocket_manager.health_stats['active_connections'] = 1
        
        # Send a message
        websocket_manager.emit_to_room("test_room", "test_event", {})
        
        # Check updated stats
        stats = websocket_manager.get_health_stats()
        assert stats['active_connections'] == 1
        assert stats['total_messages_sent'] == 1
    
    def test_cleanup_expired_connections(self, websocket_manager):
        """Test cleanup of expired connections."""
        # Create an old disconnected connection
        old_time = datetime.now() - timedelta(hours=2)
        session_id = "old_session"
        
        connection = ConnectionInfo(
            session_id=session_id,
            user_id="test_user",
            connected_at=old_time,
            last_ping=old_time,
            status=ConnectionStatus.DISCONNECTED,
            rooms=set(),
            client_info={}
        )
        websocket_manager.connections[session_id] = connection
        
        # Run cleanup
        websocket_manager._cleanup_expired_data()
        
        # Verify connection was removed
        assert session_id not in websocket_manager.connections
    
    def test_cleanup_expired_messages(self, websocket_manager):
        """Test cleanup of expired messages."""
        # Create an expired message
        expired_message = QueuedMessage(
            message_id="test_id",
            room="test_room",
            event="test_event",
            data={},
            priority=MessagePriority.NORMAL,
            created_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1)
        )
        
        queue_key = "user:test_user"
        websocket_manager.message_queue[queue_key].append(expired_message)
        
        # Run cleanup
        websocket_manager._cleanup_expired_data()
        
        # Verify message was removed
        assert len(websocket_manager.message_queue[queue_key]) == 0
    
    def test_get_room_members(self, websocket_manager):
        """Test getting room members."""
        room_name = "test_room"
        session_ids = {"session1", "session2", "session3"}
        
        websocket_manager.room_members[room_name] = session_ids.copy()
        
        members = websocket_manager.get_room_members(room_name)
        assert members == session_ids
        
        # Test non-existent room
        empty_members = websocket_manager.get_room_members("nonexistent")
        assert empty_members == set()
    
    def test_get_user_sessions(self, websocket_manager):
        """Test getting user sessions."""
        user_id = "test_user"
        session_ids = {"session1", "session2"}
        
        websocket_manager.user_sessions[user_id] = session_ids.copy()
        
        sessions = websocket_manager.get_user_sessions(user_id)
        assert sessions == session_ids
        
        # Test non-existent user
        empty_sessions = websocket_manager.get_user_sessions("nonexistent")
        assert empty_sessions == set()
    
    def test_event_handlers(self, websocket_manager):
        """Test event handler registration."""
        connection_handler = Mock()
        disconnection_handler = Mock()
        message_handler = Mock()
        
        websocket_manager.add_connection_handler(connection_handler)
        websocket_manager.add_disconnection_handler(disconnection_handler)
        websocket_manager.add_message_handler("test_event", message_handler)
        
        assert connection_handler in websocket_manager.connection_handlers
        assert disconnection_handler in websocket_manager.disconnection_handlers
        assert message_handler in websocket_manager.message_handlers["test_event"]
    
    def test_disconnect_session(self, websocket_manager):
        """Test disconnecting a specific session."""
        session_id = "test_session"
        
        with patch('src.services.websocket_manager.disconnect') as mock_disconnect:
            websocket_manager.disconnect_session(session_id, "Test reason")
            mock_disconnect.assert_called_once_with(sid=session_id)
    
    def test_disconnect_user(self, websocket_manager):
        """Test disconnecting all sessions for a user."""
        user_id = "test_user"
        session_ids = {"session1", "session2"}
        
        websocket_manager.user_sessions[user_id] = session_ids.copy()
        
        with patch('src.services.websocket_manager.disconnect') as mock_disconnect:
            websocket_manager.disconnect_user(user_id, "Test reason")
            assert mock_disconnect.call_count == 2
    
    def test_queued_message_retry_logic(self, websocket_manager):
        """Test message retry logic for failed deliveries."""
        user_id = "test_user"
        session_id = "test_session"
        
        # Create connection
        connection = ConnectionInfo(
            session_id=session_id,
            user_id=user_id,
            connected_at=datetime.now(),
            last_ping=datetime.now(),
            status=ConnectionStatus.CONNECTED,
            rooms=set(),
            client_info={}
        )
        websocket_manager.connections[session_id] = connection
        
        # Create a message that will fail delivery
        message = QueuedMessage(
            message_id="test_id",
            room=f"user:{user_id}",
            event="test_event",
            data={"test": "data"},
            priority=MessagePriority.NORMAL,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=10),
            retry_count=0,
            max_retries=3
        )
        
        queue_key = f"user:{user_id}"
        websocket_manager.message_queue[queue_key].append(message)
        
        # Mock emit to raise exception
        websocket_manager.socketio.emit.side_effect = Exception("Network error")
        
        # Try to deliver messages
        websocket_manager._deliver_queued_messages(session_id)
        
        # Verify message was re-queued with incremented retry count
        assert len(websocket_manager.message_queue[queue_key]) == 1
        requeued_message = websocket_manager.message_queue[queue_key][0]
        assert requeued_message.retry_count == 1
    
    def test_high_priority_message_queuing(self, websocket_manager):
        """Test that high priority messages are queued even for online users."""
        room_name = "test_room"
        event = "critical_event"
        data = {"urgent": "message"}
        
        # Emit high priority message to room
        websocket_manager.emit_to_room(room_name, event, data, MessagePriority.CRITICAL)
        
        # Verify message was both sent and queued
        websocket_manager.socketio.emit.assert_called_once()
        queue_key = f"room:{room_name}"
        assert queue_key in websocket_manager.message_queue
        assert len(websocket_manager.message_queue[queue_key]) == 1
        
        queued_message = websocket_manager.message_queue[queue_key][0]
        assert queued_message.priority == MessagePriority.CRITICAL
    
    @patch('src.services.websocket_manager.request')
    def test_extract_user_id_from_auth(self, mock_request, websocket_manager):
        """Test extracting user ID from authentication data."""
        # Test with auth data
        auth_data = {"user_id": "test_user"}
        user_id = websocket_manager._extract_user_id(auth_data)
        assert user_id == "test_user"
        
        # Test with no auth data
        user_id = websocket_manager._extract_user_id(None)
        assert user_id is None
        
        # Test with invalid auth data
        user_id = websocket_manager._extract_user_id("invalid")
        assert user_id is None
    
    @patch('src.services.websocket_manager.request')
    def test_get_client_info(self, mock_request, websocket_manager):
        """Test getting client information from request."""
        # Mock request data
        mock_request.environ = {'HTTP_X_FORWARDED_FOR': '192.168.1.1'}
        mock_request.remote_addr = '127.0.0.1'
        mock_request.headers = {
            'User-Agent': 'Test Browser',
            'Origin': 'http://localhost:3000'
        }
        
        client_info = websocket_manager._get_client_info()
        
        assert client_info['ip_address'] == '192.168.1.1'
        assert client_info['user_agent'] == 'Test Browser'
        assert client_info['origin'] == 'http://localhost:3000'
        assert 'timestamp' in client_info