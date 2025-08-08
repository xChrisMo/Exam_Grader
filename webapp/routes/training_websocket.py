"""
Training WebSocket Routes

Handles real-time WebSocket communication for training progress monitoring.
"""

from flask import request
from flask_login import current_user, login_required
from flask_socketio import emit, join_room, leave_room, disconnect

from src.services.realtime_service import socketio
# websocket_manager will be accessed through realtime_service.websocket_manager
from utils.logger import logger
from datetime import datetime
import time


@socketio.on('connect', namespace='/training')
def handle_training_connect(auth=None):
    """
    Handle client connection to training namespace
    """
    try:
        if not current_user.is_authenticated:
            logger.warning("Unauthenticated user attempted to connect to training WebSocket")
            disconnect()
            return False
        
        session_id = request.sid
        user_id = current_user.id
        
        logger.info(f"Training WebSocket connected: user={user_id}, session={session_id}")
        
        # Join user-specific room for training updates
        join_room(f"training_user_{user_id}")
        
        # Send connection confirmation
        emit('connection_status', {
            'status': 'connected',
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        })
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling training WebSocket connection: {e}")
        emit('connection_error', {'error': str(e)})
        return False


@socketio.on('disconnect', namespace='/training')
def handle_training_disconnect():
    """
    Handle client disconnection from training namespace
    """
    try:
        if current_user.is_authenticated:
            session_id = request.sid
            user_id = current_user.id
            
            logger.info(f"Training WebSocket disconnected: user={user_id}, session={session_id}")
            
            # Leave user-specific room
            leave_room(f"training_user_{user_id}")
            
    except Exception as e:
        logger.error(f"Error handling training WebSocket disconnection: {e}")


@socketio.on('join_training_session', namespace='/training')
def handle_join_training_session(data):
    """
    Join a specific training session room for real-time updates
    """
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        training_session_id = data.get('session_id')
        if not training_session_id:
            emit('error', {'message': 'Session ID required'})
            return
        
        # TODO: Verify user has access to this training session
        # For now, assume user has access if authenticated
        
        room_name = f"training_session_{training_session_id}"
        join_room(room_name)
        
        logger.info(f"User {current_user.id} joined training session room: {room_name}")
        
        emit('joined_session', {
            'session_id': training_session_id,
            'room': room_name,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error joining training session room: {e}")
        emit('error', {'message': 'Failed to join training session'})


@socketio.on('leave_training_session', namespace='/training')
def handle_leave_training_session(data):
    """
    Leave a specific training session room
    """
    try:
        training_session_id = data.get('session_id')
        if not training_session_id:
            emit('error', {'message': 'Session ID required'})
            return
        
        room_name = f"training_session_{training_session_id}"
        leave_room(room_name)
        
        logger.info(f"User {current_user.id} left training session room: {room_name}")
        
        emit('left_session', {
            'session_id': training_session_id,
            'room': room_name,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error leaving training session room: {e}")
        emit('error', {'message': 'Failed to leave training session'})


@socketio.on('request_progress_update', namespace='/training')
def handle_progress_update_request(data):
    """
    Handle request for current progress update
    """
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        training_session_id = data.get('session_id')
        if not training_session_id:
            emit('error', {'message': 'Session ID required'})
            return
        
        # TODO: Get actual progress from TrainingService
        # For now, send mock progress data
        progress_data = {
            'session_id': training_session_id,
            'percentage': 45,
            'current_step': 'Processing files...',
            'status': 'in_progress',
            'files_processed': 2,
            'total_files': 5,
            'questions_generated': 12,
            'avg_confidence': 0.78,
            'errors': {
                'total': 1,
                'processing': 1,
                'llm': 0,
                'validation': 0
            },
            'confidence': {
                'high': 8,
                'medium': 3,
                'low': 1
            },
            'timestamp': datetime.now().isoformat()
        }
        
        emit('progress_update', {
            'type': 'progress_update',
            'data': progress_data
        })
        
        logger.debug(f"Sent progress update for session {training_session_id}")
        
    except Exception as e:
        logger.error(f"Error handling progress update request: {e}")
        emit('error', {'message': 'Failed to get progress update'})


@socketio.on('ping', namespace='/training')
def handle_training_ping(data=None):
    """
    Handle ping from training client
    """
    try:
        emit('pong', {
            'timestamp': datetime.now().isoformat(),
            'data': data
        })
        
    except Exception as e:
        logger.error(f"Error handling training ping: {e}")


def send_training_progress_update(session_id, progress_data):
    """
    Send progress update to all clients monitoring a training session
    
    Args:
        session_id: Training session ID
        progress_data: Progress data dictionary
    """
    try:
        room_name = f"training_session_{session_id}"
        
        socketio.emit('progress_update', {
            'type': 'progress_update',
            'data': progress_data
        }, room=room_name, namespace='/training')
        
        logger.debug(f"Sent progress update to room {room_name}")
        
    except Exception as e:
        logger.error(f"Error sending training progress update: {e}")


def send_training_log_entry(session_id, log_data):
    """
    Send log entry to all clients monitoring a training session
    
    Args:
        session_id: Training session ID
        log_data: Log entry data
    """
    try:
        room_name = f"training_session_{session_id}"
        
        socketio.emit('log_entry', {
            'type': 'log_entry',
            'data': log_data
        }, room=room_name, namespace='/training')
        
        logger.debug(f"Sent log entry to room {room_name}")
        
    except Exception as e:
        logger.error(f"Error sending training log entry: {e}")


def send_training_error(session_id, error_data):
    """
    Send error notification to all clients monitoring a training session
    
    Args:
        session_id: Training session ID
        error_data: Error data dictionary
    """
    try:
        room_name = f"training_session_{session_id}"
        
        socketio.emit('error', {
            'type': 'error',
            'data': error_data
        }, room=room_name, namespace='/training')
        
        logger.debug(f"Sent error notification to room {room_name}")
        
    except Exception as e:
        logger.error(f"Error sending training error notification: {e}")


def send_training_step_update(session_id, step_data):
    """
    Send training step update to all clients monitoring a training session
    
    Args:
        session_id: Training session ID
        step_data: Step update data
    """
    try:
        room_name = f"training_session_{session_id}"
        
        socketio.emit('step_update', {
            'type': 'step_update',
            'data': step_data
        }, room=room_name, namespace='/training')
        
        logger.debug(f"Sent step update to room {room_name}")
        
    except Exception as e:
        logger.error(f"Error sending training step update: {e}")


def send_confidence_update(session_id, confidence_data):
    """
    Send confidence score update to all clients monitoring a training session
    
    Args:
        session_id: Training session ID
        confidence_data: Confidence data dictionary
    """
    try:
        room_name = f"training_session_{session_id}"
        
        socketio.emit('confidence_update', {
            'type': 'confidence_update',
            'data': confidence_data
        }, room=room_name, namespace='/training')
        
        logger.debug(f"Sent confidence update to room {room_name}")
        
    except Exception as e:
        logger.error(f"Error sending training confidence update: {e}")


def send_status_change(session_id, status_data):
    """
    Send status change notification to all clients monitoring a training session
    
    Args:
        session_id: Training session ID
        status_data: Status change data
    """
    try:
        room_name = f"training_session_{session_id}"
        
        socketio.emit('status_change', {
            'type': 'status_change',
            'data': status_data
        }, room=room_name, namespace='/training')
        
        logger.info(f"Sent status change to room {room_name}: {status_data.get('status')}")
        
    except Exception as e:
        logger.error(f"Error sending training status change: {e}")


@socketio.on('subscribe_to_updates', namespace='/training')
def handle_subscribe_to_updates(data):
    """
    Subscribe to specific types of updates for a training session
    """
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        session_id = data.get('session_id')
        update_types = data.get('update_types', ['progress', 'logs', 'errors'])
        
        if not session_id:
            emit('error', {'message': 'Session ID required'})
            return
        
        # Store subscription preferences using websocket_manager
        subscription_data = {
            'user_id': current_user.id,
            'session_id': session_id,
            'update_types': update_types,
            'subscribed_at': time.time()
        }
        
        logger.info(f"User {current_user.id} subscribed to {update_types} updates for session {session_id}")
        
        emit('subscription_confirmed', {
            'session_id': session_id,
            'update_types': update_types,
            'message': 'Successfully subscribed to updates'
        })
        
    except Exception as e:
        logger.error(f"Error handling subscription: {e}")
        emit('error', {'message': 'Failed to subscribe to updates'})


@socketio.on('unsubscribe_from_updates', namespace='/training')
def handle_unsubscribe_from_updates(data):
    """
    Unsubscribe from updates for a training session
    """
    try:
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        
        session_id = data.get('session_id')
        
        if not session_id:
            emit('error', {'message': 'Session ID required'})
            return
        
        logger.info(f"User {current_user.id} unsubscribed from updates for session {session_id}")
        
        emit('unsubscription_confirmed', {
            'session_id': session_id,
            'message': 'Successfully unsubscribed from updates'
        })
        
    except Exception as e:
        logger.error(f"Error handling unsubscription: {e}")
        emit('error', {'message': 'Failed to unsubscribe from updates'})


def broadcast_training_notification(user_id, notification_data):
    """
    Send notification to a specific user across all their connected sessions
    
    Args:
        user_id: Target user ID
        notification_data: Notification data dictionary
    """
    try:
        room_name = f"training_user_{user_id}"
        
        socketio.emit('notification', {
            'type': 'notification',
            'data': notification_data
        }, room=room_name, namespace='/training')
        
        logger.debug(f"Sent notification to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting notification: {e}")


def send_training_completion_notification(session_id, completion_data):
    """
    Send training completion notification with results summary
    
    Args:
        session_id: Training session ID
        completion_data: Completion data dictionary
    """
    try:
        room_name = f"training_session_{session_id}"
        
        socketio.emit('training_completed', {
            'type': 'training_completed',
            'data': completion_data
        }, room=room_name, namespace='/training')
        
        logger.info(f"Sent training completion notification for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error sending training completion notification: {e}")


def send_batch_update(session_id, updates):
    """
    Send multiple updates in a single message to reduce WebSocket traffic
    
    Args:
        session_id: Training session ID
        updates: List of update dictionaries
    """
    try:
        room_name = f"training_session_{session_id}"
        
        socketio.emit('batch_update', {
            'type': 'batch_update',
            'data': {
                'session_id': session_id,
                'updates': updates,
                'timestamp': time.time()
            }
        }, room=room_name, namespace='/training')
        
        logger.debug(f"Sent batch update with {len(updates)} items to session {session_id}")
        
    except Exception as e:
        logger.error(f"Error sending batch update: {e}")


class TrainingWebSocketManager:
    """
    Manager class for training-specific WebSocket operations
    """
    
    @staticmethod
    def notify_session_created(user_id, session_data):
        """Notify user when a new training session is created"""
        broadcast_training_notification(user_id, {
            'type': 'session_created',
            'session': session_data,
            'message': f'Training session "{session_data.get("name")}" created successfully'
        })
    
    @staticmethod
    def notify_session_started(session_id, session_data):
        """Notify all session subscribers when training starts"""
        send_status_change(session_id, {
            'status': 'in_progress',
            'started_at': time.time(),
            'message': 'Training session started'
        })
    
    @staticmethod
    def notify_session_completed(session_id, results):
        """Notify all session subscribers when training completes"""
        send_training_completion_notification(session_id, {
            'session_id': session_id,
            'status': 'completed',
            'completed_at': time.time(),
            'results': results,
            'message': 'Training session completed successfully'
        })
    
    @staticmethod
    def notify_session_failed(session_id, error_info):
        """Notify all session subscribers when training fails"""
        send_status_change(session_id, {
            'status': 'failed',
            'failed_at': time.time(),
            'error': error_info,
            'message': 'Training session failed'
        })
    
    @staticmethod
    def send_progress_batch(session_id, progress_data, logs=None, errors=None):
        """Send progress update with optional logs and errors in a single message"""
        updates = [{'type': 'progress', 'data': progress_data}]
        
        if logs:
            updates.extend([{'type': 'log', 'data': log} for log in logs])
        
        if errors:
            updates.extend([{'type': 'error', 'data': error} for error in errors])
        
        send_batch_update(session_id, updates)


# Export the manager for use in other modules
training_websocket_manager = TrainingWebSocketManager()