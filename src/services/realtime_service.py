"""
Real-time Service for WebSocket-based live updates.
Provides real-time communication for dashboard updates, progress tracking, and notifications.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import current_app, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from utils.logger import logger

# Initialize SocketIO
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')


class RealtimeService:
    """Real-time service for WebSocket communication and live updates."""
    
    def __init__(self, app=None):
        """Initialize the real-time service."""
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the service with Flask app."""
        self.app = app
        socketio.init_app(app, cors_allowed_origins="*")
        
        # Register event handlers
        self._register_handlers()
        
        logger.info("Real-time service initialized with SocketIO")
    
    def _register_handlers(self):
        """Register SocketIO event handlers."""
        
        @socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.info(f"Client connected: {request.sid}")
            emit('connected', {'status': 'connected', 'timestamp': datetime.now().isoformat()})
        
        @socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info(f"Client disconnected: {request.sid}")
        
        @socketio.on('join_dashboard')
        def handle_join_dashboard(data):
            """Join dashboard room for user-specific updates."""
            user_id = data.get('user_id')
            if user_id:
                room = f"dashboard_{user_id}"
                join_room(room)
                logger.info(f"User {user_id} joined dashboard room: {room}")
                emit('joined_dashboard', {'room': room})
        
        @socketio.on('join_progress')
        def handle_join_progress(data):
            """Join progress tracking room."""
            progress_id = data.get('progress_id')
            if progress_id:
                room = f"progress_{progress_id}"
                join_room(room)
                logger.info(f"Client joined progress room: {room}")
                emit('joined_progress', {'room': room})
        
        @socketio.on('leave_room')
        def handle_leave_room(data):
            """Leave a specific room."""
            room = data.get('room')
            if room:
                leave_room(room)
                logger.info(f"Client left room: {room}")
    
    def emit_dashboard_update(self, user_id: str, update_data: Dict[str, Any]):
        """Emit dashboard update to specific user."""
        room = f"dashboard_{user_id}"
        emit('dashboard_update', update_data, room=room, namespace='/')
        logger.debug(f"Dashboard update emitted to {room}: {update_data.get('type', 'unknown')}")
    
    def emit_progress_update(self, progress_id: str, progress_data: Dict[str, Any]):
        """Emit progress update to progress tracking room."""
        room = f"progress_{progress_id}"
        emit('progress_update', progress_data, room=room, namespace='/')
        logger.debug(f"Progress update emitted to {room}: {progress_data.get('current_step', 0)}/{progress_data.get('total_steps', 0)}")
    
    def emit_notification(self, user_id: str, notification_data: Dict[str, Any]):
        """Emit notification to specific user."""
        room = f"dashboard_{user_id}"
        emit('notification', notification_data, room=room, namespace='/')
        logger.debug(f"Notification emitted to {room}: {notification_data.get('type', 'info')}")
    
    def emit_global_update(self, update_data: Dict[str, Any]):
        """Emit update to all connected clients."""
        emit('global_update', update_data, namespace='/')
        logger.debug(f"Global update emitted: {update_data.get('type', 'unknown')}")
    
    def broadcast_file_upload_status(self, user_id: str, filename: str, status: str, message: str = ""):
        """Broadcast file upload status update."""
        update_data = {
            'type': 'file_upload_status',
            'filename': filename,
            'status': status,  # 'uploading', 'processing', 'completed', 'failed'
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.emit_dashboard_update(user_id, update_data)
    
    def broadcast_ocr_status(self, user_id: str, filename: str, status: str, progress: float = 0.0, message: str = ""):
        """Broadcast OCR processing status."""
        update_data = {
            'type': 'ocr_status',
            'filename': filename,
            'status': status,  # 'starting', 'processing', 'completed', 'failed'
            'progress': progress,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.emit_dashboard_update(user_id, update_data)
    
    def broadcast_llm_status(self, user_id: str, filename: str, status: str, progress: float = 0.0, message: str = ""):
        """Broadcast LLM grading status."""
        update_data = {
            'type': 'llm_status',
            'filename': filename,
            'status': status,  # 'starting', 'mapping', 'grading', 'completed', 'failed'
            'progress': progress,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.emit_dashboard_update(user_id, update_data)
    
    def broadcast_grading_complete(self, user_id: str, results_summary: Dict[str, Any]):
        """Broadcast grading completion with results summary."""
        update_data = {
            'type': 'grading_complete',
            'results': results_summary,
            'timestamp': datetime.now().isoformat()
        }
        self.emit_dashboard_update(user_id, update_data)
    
    def broadcast_error(self, user_id: str, error_type: str, error_message: str, details: Dict[str, Any] = None):
        """Broadcast error notification."""
        update_data = {
            'type': 'error',
            'error_type': error_type,
            'message': error_message,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        self.emit_notification(user_id, update_data)


# Global instance
realtime_service = RealtimeService()


def init_realtime_service(app):
    """Initialize real-time service with Flask app."""
    realtime_service.init_app(app)
    return realtime_service 