"""Real-time Service for WebSocket-based live updates.
Provides real-time communication for dashboard updates, progress tracking, and notifications.
Integrated with enhanced WebSocketManager for comprehensive connection handling."""

from typing import Any, Dict

from flask_socketio import SocketIO, emit, join_room, leave_room

from src.logging import get_logger
from src.services.websocket_manager import MessagePriority, WebSocketManager

if get_logger is not None:
    logger = get_logger(__name__)
else:
    import logging

    logger = logging.getLogger(__name__)

# Initialize SocketIO
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


class RealtimeService:
    """Real-time service for WebSocket communication and live updates."""

    def __init__(self, app=None):
        """Initialize the real-time service."""
        self.app = app
        self.websocket_manager = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the service with Flask app."""
        self.app = app
        socketio.init_app(app, cors_allowed_origins="*")

        # Initialize WebSocket manager
        self.websocket_manager = WebSocketManager(socketio, app)

        # Register event handlers
        self._register_handlers()

        # Register WebSocket manager handlers
        self._register_websocket_handlers()

        logger.info("Real-time service initialized with enhanced WebSocket manager")

    def _register_handlers(self):
        """Register SocketIO event handlers."""

        @socketio.on("connect")
        def handle_connect():
            """Handle client connection."""
            logger.info(f"Client connected: {request.sid}")
            emit(
                "connected",
                {"status": "connected", "timestamp": datetime.now().isoformat()},
            )

        @socketio.on("disconnect")
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info(f"Client disconnected: {request.sid}")

        @socketio.on("join_dashboard")
        def handle_join_dashboard(data):
            """Join dashboard room for user-specific updates."""
            user_id = data.get("user_id")
            if user_id:
                room = f"dashboard_{user_id}"
                join_room(room)
                logger.info(f"User {user_id} joined dashboard room: {room}")
                emit("joined_dashboard", {"room": room})

        @socketio.on("join_progress")
        def handle_join_progress(data):
            """Join progress tracking room."""
            progress_id = data.get("progress_id")
            if progress_id:
                room = f"progress_{progress_id}"
                join_room(room)
                logger.info(f"Client joined progress room: {room}")
                emit("joined_progress", {"room": room})

        @socketio.on("leave_room")
        def handle_leave_room(data):
            """Leave a specific room."""
            room = data.get("room")
            if room:
                leave_room(room)
                logger.info(f"Client left room: {room}")

    def _register_websocket_handlers(self):
        """Register WebSocket manager event handlers."""
        if not self.websocket_manager:
            return

        def on_connection(connection_info):
            """Handle new WebSocket connection."""
            logger.info(
                f"WebSocket connection established: {connection_info.session_id} (user: {connection_info.user_id})"
            )

            # Auto-join user to their dashboard room
            if connection_info.user_id:
                dashboard_room = f"dashboard_{connection_info.user_id}"
                self.websocket_manager.join_room(
                    connection_info.session_id, dashboard_room
                )

        def on_disconnection(connection_info):
            """Handle WebSocket disconnection."""
            logger.info(
                f"WebSocket connection closed: {connection_info.session_id} (user: {connection_info.user_id})"
            )

        # Register handlers
        self.websocket_manager.add_connection_handler(on_connection)
        self.websocket_manager.add_disconnection_handler(on_disconnection)

    def emit_dashboard_update(self, user_id: str, update_data: Dict[str, Any]):
        """Emit dashboard update to specific user."""
        if self.websocket_manager:
            success = self.websocket_manager.emit_to_user(
                user_id, "dashboard_update", update_data, MessagePriority.NORMAL
            )
            if not success:
                logger.warning(f"Failed to emit dashboard update to user {user_id}")
        else:
            # Fallback to direct emission
            room = f"dashboard_{user_id}"
            emit("dashboard_update", update_data, room=room, namespace="/")
        logger.debug(
            f"Dashboard update emitted to user {user_id}: {update_data.get('type', 'unknown')}"
        )

    def emit_progress_update(self, progress_id: str, progress_data: Dict[str, Any]):
        """Emit progress update to progress tracking room."""
        room = f"progress_{progress_id}"
        if self.websocket_manager:
            priority = (
                MessagePriority.HIGH
                if progress_data.get("status") == "error"
                else MessagePriority.NORMAL
            )
            success = self.websocket_manager.emit_to_room(
                room, "progress_update", progress_data, priority
            )
            if not success:
                logger.warning(f"Failed to emit progress update to room {room}")
        else:
            # Fallback to direct emission
            emit("progress_update", progress_data, room=room, namespace="/")
        logger.debug(
            f"Progress update emitted to {room}: {progress_data.get('current_step', 0)}/{progress_data.get('total_steps', 0)}"
        )

    def emit_notification(self, user_id: str, notification_data: Dict[str, Any]):
        """Emit notification to specific user."""
        if self.websocket_manager:
            priority = (
                MessagePriority.HIGH
                if notification_data.get("type") == "error"
                else MessagePriority.NORMAL
            )
            success = self.websocket_manager.emit_to_user(
                user_id, "notification", notification_data, priority
            )
            if not success:
                logger.warning(f"Failed to emit notification to user {user_id}")
        else:
            # Fallback to direct emission
            room = f"dashboard_{user_id}"
            emit("notification", notification_data, room=room, namespace="/")
        logger.debug(
            f"Notification emitted to user {user_id}: {notification_data.get('type', 'info')}"
        )

    def emit_global_update(self, update_data: Dict[str, Any]):
        """Emit update to all connected clients."""
        if self.websocket_manager:
            # Emit to a global broadcast room
            global_room = "global_updates"
            priority = (
                MessagePriority.HIGH
                if update_data.get("type") == "system_alert"
                else MessagePriority.NORMAL
            )
            success = self.websocket_manager.emit_to_room(
                global_room, "global_update", update_data, priority
            )
            if not success:
                logger.warning("Failed to emit global update")
        else:
            # Fallback to direct emission
            emit("global_update", update_data, namespace="/")
        logger.debug(f"Global update emitted: {update_data.get('type', 'unknown')}")

    def broadcast_file_upload_status(
        self, user_id: str, filename: str, status: str, message: str = ""
    ):
        """Broadcast file upload status update."""
        update_data = {
            "type": "file_upload_status",
            "filename": filename,
            "status": status,  # 'uploading', 'processing', 'completed', 'failed'
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        self.emit_dashboard_update(user_id, update_data)

    def broadcast_ocr_status(
        self,
        user_id: str,
        filename: str,
        status: str,
        progress: float = 0.0,
        message: str = "",
    ):
        """Broadcast OCR processing status."""
        update_data = {
            "type": "ocr_status",
            "filename": filename,
            "status": status,  # 'starting', 'processing', 'completed', 'failed'
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        self.emit_dashboard_update(user_id, update_data)

    def broadcast_llm_status(
        self,
        user_id: str,
        filename: str,
        status: str,
        progress: float = 0.0,
        message: str = "",
    ):
        """Broadcast LLM grading status."""
        update_data = {
            "type": "llm_status",
            "filename": filename,
            "status": status,  # 'starting', 'mapping', 'grading', 'completed', 'failed'
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        self.emit_dashboard_update(user_id, update_data)

    def broadcast_grading_complete(self, user_id: str, results_summary: Dict[str, Any]):
        """Broadcast grading completion with results summary."""
        update_data = {
            "type": "grading_complete",
            "results": results_summary,
            "timestamp": datetime.now().isoformat(),
        }
        self.emit_dashboard_update(user_id, update_data)

    def broadcast_error(
        self,
        user_id: str,
        error_type: str,
        error_message: str,
        details: Dict[str, Any] = None,
    ):
        """Broadcast error notification."""
        update_data = {
            "type": "error",
            "error_type": error_type,
            "message": error_message,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.emit_notification(user_id, update_data)

    def join_progress_room(self, session_id: str, progress_id: str) -> bool:
        """Join a progress tracking room.

        Args:
            session_id: Session ID
            progress_id: Progress tracking ID

        Returns:
            True if successful
        """
        if self.websocket_manager:
            room = f"progress_{progress_id}"
            return self.websocket_manager.join_room(session_id, room)
        return False

    def leave_progress_room(self, session_id: str, progress_id: str) -> bool:
        """Leave a progress tracking room.

        Args:
            session_id: Session ID
            progress_id: Progress tracking ID

        Returns:
            True if successful
        """
        if self.websocket_manager:
            room = f"progress_{progress_id}"
            return self.websocket_manager.leave_room(session_id, room)
        return False

    def get_websocket_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics.

        Returns:
            Statistics dictionary
        """
        if self.websocket_manager:
            return self.websocket_manager.get_health_stats()
        return {}

    def disconnect_user_sessions(self, user_id: str, reason: str = "Server disconnect"):
        """Disconnect all sessions for a user.

        Args:
            user_id: User ID
            reason: Disconnect reason
        """
        if self.websocket_manager:
            self.websocket_manager.disconnect_user(user_id, reason)


# Global instance
realtime_service = RealtimeService()


def init_realtime_service(app):
    """Initialize the realtime service with Flask app.

    Args:
        app: Flask application instance
    """
    global realtime_service
    realtime_service = RealtimeService(app)
    return realtime_service
