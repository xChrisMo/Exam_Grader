"""
Integration tests for WebSocket Communication

Tests the real-time WebSocket communication for training progress updates.
"""

import json
import time
import pytest
from unittest.mock import patch, Mock

from tests.conftest import create_test_user
from webapp.app_factory import create_app
from src.services.realtime_service import socketio

class TestWebSocketCommunication:
    """Integration tests for WebSocket communication"""

    @pytest.fixture
    def app(self):
        """Create test application with SocketIO"""
        app = create_app('testing')
        return app

    @pytest.fixture
    def client(self, app):
        """Create SocketIO test client"""
        return socketio.test_client(app, namespace='/training')

    @pytest.fixture
    def test_user(self, app):
        """Create test user"""
        with app.app_context():
            return create_test_user()

    def test_websocket_connection(self, client, test_user):
        """Test WebSocket connection to training namespace"""
        with patch('flask_login.current_user', test_user):
            # Connect to training namespace
            assert client.is_connected(namespace='/training')

            # Check connection status message
            received = client.get_received(namespace='/training')
            assert len(received) > 0

            connection_msg = received[0]
            assert connection_msg['name'] == 'connection_status'
            assert connection_msg['args'][0]['status'] == 'connected'
            assert connection_msg['args'][0]['user_id'] == test_user.id

    def test_join_training_session(self, client, test_user):
        """Test joining a training session room"""
        session_id = f'session_{test_user.id}_123456'

        with patch('flask_login.current_user', test_user):
            # Join training session
            client.emit('join_training_session', {
                'session_id': session_id
            }, namespace='/training')

            # Check join confirmation
            received = client.get_received(namespace='/training')
            join_msg = next((msg for msg in received if msg['name'] == 'joined_session'), None)

            assert join_msg is not None
            assert join_msg['args'][0]['session_id'] == session_id
            assert join_msg['args'][0]['room'] == f'training_session_{session_id}'

    def test_leave_training_session(self, client, test_user):
        """Test leaving a training session room"""
        session_id = f'session_{test_user.id}_123456'

        with patch('flask_login.current_user', test_user):
            # First join the session
            client.emit('join_training_session', {
                'session_id': session_id
            }, namespace='/training')

            # Clear received messages
            client.get_received(namespace='/training')

            # Leave training session
            client.emit('leave_training_session', {
                'session_id': session_id
            }, namespace='/training')

            # Check leave confirmation
            received = client.get_received(namespace='/training')
            leave_msg = next((msg for msg in received if msg['name'] == 'left_session'), None)

            assert leave_msg is not None
            assert leave_msg['args'][0]['session_id'] == session_id

    def test_request_progress_update(self, client, test_user):
        """Test requesting progress update"""
        session_id = f'session_{test_user.id}_123456'

        with patch('flask_login.current_user', test_user):
            # Join session first
            client.emit('join_training_session', {
                'session_id': session_id
            }, namespace='/training')

            # Clear received messages
            client.get_received(namespace='/training')

            # Request progress update
            client.emit('request_progress_update', {
                'session_id': session_id
            }, namespace='/training')

            # Check progress update response
            received = client.get_received(namespace='/training')
            progress_msg = next((msg for msg in received if msg['name'] == 'progress_update'), None)

            assert progress_msg is not None
            assert progress_msg['args'][0]['type'] == 'progress_update'
            assert 'data' in progress_msg['args'][0]
            assert progress_msg['args'][0]['data']['session_id'] == session_id

    def test_ping_pong(self, client, test_user):
        """Test ping-pong communication"""
        with patch('flask_login.current_user', test_user):
            # Send ping
            client.emit('ping', {'test': 'data'}, namespace='/training')

            # Check pong response
            received = client.get_received(namespace='/training')
            pong_msg = next((msg for msg in received if msg['name'] == 'pong'), None)

            assert pong_msg is not None
            assert 'timestamp' in pong_msg['args'][0]
            assert pong_msg['args'][0]['data']['test'] == 'data'

    def test_subscribe_to_updates(self, client, test_user):
        """Test subscribing to specific update types"""
        session_id = f'session_{test_user.id}_123456'
        update_types = ['progress', 'logs', 'errors']

        with patch('flask_login.current_user', test_user):
            # Subscribe to updates
            client.emit('subscribe_to_updates', {
                'session_id': session_id,
                'update_types': update_types
            }, namespace='/training')

            # Check subscription confirmation
            received = client.get_received(namespace='/training')
            sub_msg = next((msg for msg in received if msg['name'] == 'subscription_confirmed'), None)

            assert sub_msg is not None
            assert sub_msg['args'][0]['session_id'] == session_id
            assert sub_msg['args'][0]['update_types'] == update_types

    def test_unsubscribe_from_updates(self, client, test_user):
        """Test unsubscribing from updates"""
        session_id = f'session_{test_user.id}_123456'

        with patch('flask_login.current_user', test_user):
            # First subscribe
            client.emit('subscribe_to_updates', {
                'session_id': session_id,
                'update_types': ['progress']
            }, namespace='/training')

            # Clear messages
            client.get_received(namespace='/training')

            # Unsubscribe
            client.emit('unsubscribe_from_updates', {
                'session_id': session_id
            }, namespace='/training')

            # Check unsubscription confirmation
            received = client.get_received(namespace='/training')
            unsub_msg = next((msg for msg in received if msg['name'] == 'unsubscription_confirmed'), None)

            assert unsub_msg is not None
            assert unsub_msg['args'][0]['session_id'] == session_id

    def test_unauthenticated_connection(self, client):
        """Test WebSocket connection without authentication"""
        with patch('flask_login.current_user.is_authenticated', False):
            # Should not be connected due to authentication check
            assert not client.is_connected(namespace='/training')

    def test_invalid_session_access(self, client, test_user):
        """Test accessing invalid session"""
        invalid_session_id = 'session_999_invalid'

        with patch('flask_login.current_user', test_user):
            # Try to join invalid session
            client.emit('join_training_session', {
                'session_id': invalid_session_id
            }, namespace='/training')

            # Should still work (validation happens at application level)
            received = client.get_received(namespace='/training')
            join_msg = next((msg for msg in received if msg['name'] == 'joined_session'), None)

            # WebSocket layer allows join, but application layer would validate
            assert join_msg is not None

    def test_missing_session_id(self, client, test_user):
        """Test operations with missing session ID"""
        with patch('flask_login.current_user', test_user):
            # Try to join without session ID
            client.emit('join_training_session', {}, namespace='/training')

            # Check error response
            received = client.get_received(namespace='/training')
            error_msg = next((msg for msg in received if msg['name'] == 'error'), None)

            assert error_msg is not None
            assert 'Session ID required' in error_msg['args'][0]['message']

    def test_multiple_clients_same_session(self, app, test_user):
        """Test multiple clients joining the same session"""
        session_id = f'session_{test_user.id}_123456'

        # Create multiple clients
        client1 = socketio.test_client(app, namespace='/training')
        client2 = socketio.test_client(app, namespace='/training')

        with patch('flask_login.current_user', test_user):
            # Both clients join the same session
            client1.emit('join_training_session', {
                'session_id': session_id
            }, namespace='/training')

            client2.emit('join_training_session', {
                'session_id': session_id
            }, namespace='/training')

            # Both should receive join confirmations
            received1 = client1.get_received(namespace='/training')
            received2 = client2.get_received(namespace='/training')

            join_msg1 = next((msg for msg in received1 if msg['name'] == 'joined_session'), None)
            join_msg2 = next((msg for msg in received2 if msg['name'] == 'joined_session'), None)

            assert join_msg1 is not None
            assert join_msg2 is not None
            assert join_msg1['args'][0]['session_id'] == session_id
            assert join_msg2['args'][0]['session_id'] == session_id

    def test_websocket_disconnect_handling(self, client, test_user):
        """Test WebSocket disconnect handling"""
        with patch('flask_login.current_user', test_user):
            # Connect and join session
            session_id = f'session_{test_user.id}_123456'
            client.emit('join_training_session', {
                'session_id': session_id
            }, namespace='/training')

            # Disconnect
            client.disconnect(namespace='/training')

            # Should be disconnected
            assert not client.is_connected(namespace='/training')

    def test_broadcast_progress_update(self, app, test_user):
        """Test broadcasting progress updates to session room"""
        from webapp.routes.training_websocket import send_training_progress_update

        session_id = f'session_{test_user.id}_123456'

        # Create client and join session
        client = socketio.test_client(app, namespace='/training')

        with patch('flask_login.current_user', test_user):
            client.emit('join_training_session', {
                'session_id': session_id
            }, namespace='/training')

            # Clear initial messages
            client.get_received(namespace='/training')

            # Broadcast progress update
            progress_data = {
                'session_id': session_id,
                'percentage': 75,
                'current_step': 'Processing files...',
                'status': 'in_progress'
            }

            with app.app_context():
                send_training_progress_update(session_id, progress_data)

            # Check if client received the broadcast
            received = client.get_received(namespace='/training')
            progress_msg = next((msg for msg in received if msg['name'] == 'progress_update'), None)

            assert progress_msg is not None
            assert progress_msg['args'][0]['data']['percentage'] == 75

    def test_broadcast_log_entry(self, app, test_user):
        """Test broadcasting log entries to session room"""
        from webapp.routes.training_websocket import send_training_log_entry

        session_id = f'session_{test_user.id}_123456'

        # Create client and join session
        client = socketio.test_client(app, namespace='/training')

        with patch('flask_login.current_user', test_user):
            client.emit('join_training_session', {
                'session_id': session_id
            }, namespace='/training')

            # Clear initial messages
            client.get_received(namespace='/training')

            # Broadcast log entry
            log_data = {
                'level': 'INFO',
                'message': 'Processing file 1 of 5',
                'timestamp': time.time()
            }

            with app.app_context():
                send_training_log_entry(session_id, log_data)

            # Check if client received the broadcast
            received = client.get_received(namespace='/training')
            log_msg = next((msg for msg in received if msg['name'] == 'log_entry'), None)

            assert log_msg is not None
            assert log_msg['args'][0]['data']['message'] == 'Processing file 1 of 5'

    def test_broadcast_error_notification(self, app, test_user):
        """Test broadcasting error notifications to session room"""
        from webapp.routes.training_websocket import send_training_error

        session_id = f'session_{test_user.id}_123456'

        # Create client and join session
        client = socketio.test_client(app, namespace='/training')

        with patch('flask_login.current_user', test_user):
            client.emit('join_training_session', {
                'session_id': session_id
            }, namespace='/training')

            # Clear initial messages
            client.get_received(namespace='/training')

            # Broadcast error
            error_data = {
                'type': 'processing_error',
                'message': 'Failed to process file',
                'timestamp': time.time()
            }

            with app.app_context():
                send_training_error(session_id, error_data)

            # Check if client received the broadcast
            received = client.get_received(namespace='/training')
            error_msg = next((msg for msg in received if msg['name'] == 'error'), None)

            assert error_msg is not None
            assert error_msg['args'][0]['data']['message'] == 'Failed to process file'

    def test_batch_update_broadcast(self, app, test_user):
        """Test broadcasting batch updates to reduce WebSocket traffic"""
        from webapp.routes.training_websocket import send_batch_update

        session_id = f'session_{test_user.id}_123456'

        # Create client and join session
        client = socketio.test_client(app, namespace='/training')

        with patch('flask_login.current_user', test_user):
            client.emit('join_training_session', {
                'session_id': session_id
            }, namespace='/training')

            # Clear initial messages
            client.get_received(namespace='/training')

            # Send batch update
            updates = [
                {'type': 'progress', 'data': {'percentage': 50}},
                {'type': 'log', 'data': {'message': 'Step completed'}},
                {'type': 'confidence', 'data': {'avg_confidence': 0.85}}
            ]

            with app.app_context():
                send_batch_update(session_id, updates)

            # Check if client received the batch update
            received = client.get_received(namespace='/training')
            batch_msg = next((msg for msg in received if msg['name'] == 'batch_update'), None)

            assert batch_msg is not None
            assert len(batch_msg['args'][0]['data']['updates']) == 3
            assert batch_msg['args'][0]['data']['session_id'] == session_id

    def test_websocket_manager_notifications(self, app, test_user):
        """Test WebSocket manager notification methods"""
        from webapp.routes.training_websocket import training_websocket_manager

        session_id = f'session_{test_user.id}_123456'

        # Create client and join session
        client = socketio.test_client(app, namespace='/training')

        with patch('flask_login.current_user', test_user):
            client.emit('join_training_session', {
                'session_id': session_id
            }, namespace='/training')

            # Clear initial messages
            client.get_received(namespace='/training')

            # Test session started notification
            session_data = {'name': 'Test Session', 'status': 'in_progress'}

            with app.app_context():
                training_websocket_manager.notify_session_started(session_id, session_data)

            # Check if client received the notification
            received = client.get_received(namespace='/training')
            status_msg = next((msg for msg in received if msg['name'] == 'status_change'), None)

            assert status_msg is not None
            assert status_msg['args'][0]['data']['status'] == 'in_progress'