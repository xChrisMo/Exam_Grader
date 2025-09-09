"""Enhanced WebSocket Manager for Real-time Communication.

Provides comprehensive WebSocket connection management with:
- Connection recovery and fallback mechanisms
- Room-based messaging for progress tracking
- Connection health monitoring
- Automatic reconnection handling
- Message queuing for offline clients
"""

import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
import uuid
from dataclasses import dataclass
from enum import Enum
from threading import Lock, Thread
from typing import Any, Callable, Dict, List, Optional, Set

from flask_socketio import SocketIO, disconnect, emit, join_room, leave_room

from src.logging import get_logger

if get_logger is not None:
    logger = get_logger(__name__)
else:
    import logging

    logger = logging.getLogger(__name__)

class ConnectionStatus(Enum):
    """WebSocket connection status."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"

class MessagePriority(Enum):
    """Message priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""

    session_id: str
    user_id: Optional[str]
    connected_at: datetime
    last_ping: datetime
    status: ConnectionStatus
    rooms: Set[str]
    client_info: Dict[str, Any]
    reconnect_attempts: int = 0
    max_reconnect_attempts: int = 5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "status": self.status.value,
            "rooms": list(self.rooms),
            "client_info": self.client_info,
            "reconnect_attempts": self.reconnect_attempts,
        }

@dataclass
class QueuedMessage:
    """Queued message for offline clients."""

    message_id: str
    room: str
    event: str
    data: Dict[str, Any]
    priority: MessagePriority
    created_at: datetime
    expires_at: datetime
    retry_count: int = 0
    max_retries: int = 3

class WebSocketManager:
    """Enhanced WebSocket manager with comprehensive connection handling."""

    def __init__(self, socketio: SocketIO, app=None):
        """Initialize WebSocket manager.

        Args:
            socketio: SocketIO instance
            app: Flask application instance
        """
        self.socketio = socketio
        self.app = app

        # Connection tracking
        self.connections: Dict[str, ConnectionInfo] = {}
        self.user_sessions: Dict[str, Set[str]] = defaultdict(set)
        self.room_members: Dict[str, Set[str]] = defaultdict(set)

        # Message queuing
        self.message_queue: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.failed_messages: deque = deque(maxlen=1000)

        # Configuration
        self.ping_interval = 30  # seconds
        self.ping_timeout = 10  # seconds
        self.message_retention = 3600  # 1 hour
        self.cleanup_interval = 300  # 5 minutes

        # Thread safety
        self.lock = Lock()

        # Health monitoring
        self.health_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_messages_sent": 0,
            "failed_messages": 0,
            "reconnections": 0,
            "rooms_active": 0,
        }

        # Event handlers
        self.connection_handlers: List[Callable] = []
        self.disconnection_handlers: List[Callable] = []
        self.message_handlers: Dict[str, List[Callable]] = defaultdict(list)

        if app:
            self.init_app(app)

        logger.info("WebSocket Manager initialized")

    def init_app(self, app):
        """Initialize with Flask app.

        Args:
            app: Flask application instance
        """
        self.app = app
        self._register_socketio_handlers()
        self._start_background_tasks()
        logger.info("WebSocket Manager initialized with Flask app")

    def _register_socketio_handlers(self):
        """Register SocketIO event handlers."""

        @self.socketio.on("connect")
        def handle_connect(auth=None):
            """Handle client connection."""
            try:
                session_id = request.sid
                user_id = self._extract_user_id(auth)

                # Create connection info
                connection = ConnectionInfo(
                    session_id=session_id,
                    user_id=user_id,
                    connected_at=datetime.now(),
                    last_ping=datetime.now(),
                    status=ConnectionStatus.CONNECTED,
                    rooms=set(),
                    client_info=self._get_client_info(),
                )

                with self.lock:
                    self.connections[session_id] = connection
                    if user_id:
                        self.user_sessions[user_id].add(session_id)
                    self.health_stats["total_connections"] += 1
                    self.health_stats["active_connections"] += 1

                # Send connection confirmation
                emit(
                    "connection_established",
                    {
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat(),
                        "server_time": time.time(),
                    },
                )

                # Deliver queued messages
                self._deliver_queued_messages(session_id)

                # Notify handlers
                for handler in self.connection_handlers:
                    try:
                        handler(connection)
                    except Exception as e:
                        logger.error(f"Connection handler error: {e}")

                logger.info(f"Client connected: {session_id} (user: {user_id})")

            except Exception as e:
                logger.error(f"Connection handling error: {e}")
                emit("connection_error", {"error": str(e)})

        @self.socketio.on("disconnect")
        def handle_disconnect():
            """Handle client disconnection."""
            try:
                session_id = request.sid

                with self.lock:
                    if session_id in self.connections:
                        connection = self.connections[session_id]
                        connection.status = ConnectionStatus.DISCONNECTED

                        if connection.user_id:
                            self.user_sessions[connection.user_id].discard(session_id)
                            if not self.user_sessions[connection.user_id]:
                                del self.user_sessions[connection.user_id]

                        for room in connection.rooms.copy():
                            self._leave_room_internal(session_id, room)

                        # Update stats
                        self.health_stats["active_connections"] -= 1

                        # Notify handlers
                        for handler in self.disconnection_handlers:
                            try:
                                handler(connection)
                            except Exception as e:
                                logger.error(f"Disconnection handler error: {e}")

                        # Will be cleaned up by background task

                        logger.info(f"Client disconnected: {session_id}")

            except Exception as e:
                logger.error(f"Disconnection handling error: {e}")

        @self.socketio.on("ping")
        def handle_ping(data=None):
            """Handle ping from client."""
            try:
                session_id = request.sid

                with self.lock:
                    if session_id in self.connections:
                        self.connections[session_id].last_ping = datetime.now()

                emit(
                    "pong",
                    {
                        "timestamp": datetime.now().isoformat(),
                        "server_time": time.time(),
                    },
                )

            except Exception as e:
                logger.error(f"Ping handling error: {e}")

        @self.socketio.on("join_room")
        def handle_join_room(data):
            """Handle room join request."""
            try:
                session_id = request.sid
                room_name = data.get("room")

                if not room_name:
                    emit("error", {"message": "Room name required"})
                    return

                success = self.join_room(session_id, room_name)

                if success:
                    emit(
                        "room_joined",
                        {"room": room_name, "timestamp": datetime.now().isoformat()},
                    )
                else:
                    emit("error", {"message": "Failed to join room"})

            except Exception as e:
                logger.error(f"Room join error: {e}")
                emit("error", {"message": "Failed to join room"})

        @self.socketio.on("leave_room")
        def handle_leave_room(data):
            """Handle room leave request."""
            try:
                session_id = request.sid
                room_name = data.get("room")

                if not room_name:
                    emit("error", {"message": "Room name required"})
                    return

                success = self.leave_room(session_id, room_name)

                if success:
                    emit(
                        "room_left",
                        {"room": room_name, "timestamp": datetime.now().isoformat()},
                    )
                else:
                    emit("error", {"message": "Failed to leave room"})

            except Exception as e:
                logger.error(f"Room leave error: {e}")
                emit("error", {"message": "Failed to leave room"})

    def _extract_user_id(self, auth) -> Optional[str]:
        """Extract user ID from authentication data.

        Args:
            auth: Authentication data from client

        Returns:
            User ID if available
        """
        if auth and isinstance(auth, dict):
            return auth.get("user_id")

        try:
            from flask_login import current_user

            if current_user.is_authenticated:
                return current_user.id
            return None
        except:
            return None

    def _get_client_info(self) -> Dict[str, Any]:
        """Get client information from request.

        Returns:
            Client information dictionary
        """
        try:
            return {
                "ip_address": request.environ.get(
                    "HTTP_X_FORWARDED_FOR", request.remote_addr
                ),
                "user_agent": request.headers.get("User-Agent", ""),
                "origin": request.headers.get("Origin", ""),
                "timestamp": datetime.now().isoformat(),
            }
        except:
            return {}

    def join_room(self, session_id: str, room_name: str) -> bool:
        """Add session to a room.

        Args:
            session_id: Session ID
            room_name: Room name

        Returns:
            True if successful
        """
        try:
            with self.lock:
                if session_id not in self.connections:
                    return False

                connection = self.connections[session_id]
                connection.rooms.add(room_name)
                self.room_members[room_name].add(session_id)

                # Update room count
                self.health_stats["rooms_active"] = len(self.room_members)

            # Join SocketIO room
            join_room(room_name, sid=session_id)

            logger.debug(f"Session {session_id} joined room {room_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to join room {room_name}: {e}")
            return False

    def leave_room(self, session_id: str, room_name: str) -> bool:
        """Remove session from a room.

        Args:
            session_id: Session ID
            room_name: Room name

        Returns:
            True if successful
        """
        try:
            return self._leave_room_internal(session_id, room_name)
        except Exception as e:
            logger.error(f"Failed to leave room {room_name}: {e}")
            return False

    def _leave_room_internal(self, session_id: str, room_name: str) -> bool:
        """Internal room leave implementation.

        Args:
            session_id: Session ID
            room_name: Room name

        Returns:
            True if successful
        """
        with self.lock:
            if session_id in self.connections:
                self.connections[session_id].rooms.discard(room_name)

            self.room_members[room_name].discard(session_id)
            if not self.room_members[room_name]:
                del self.room_members[room_name]

            # Update room count
            self.health_stats["rooms_active"] = len(self.room_members)

        # Leave SocketIO room
        leave_room(room_name, sid=session_id)

        logger.debug(f"Session {session_id} left room {room_name}")
        return True

    def emit_to_room(
        self,
        room_name: str,
        event: str,
        data: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> bool:
        """Emit message to all clients in a room.

        Args:
            room_name: Room name
            event: Event name
            data: Message data
            priority: Message priority

        Returns:
            True if message was sent
        """
        try:
            # Add metadata
            message_data = {
                **data,
                "timestamp": datetime.now().isoformat(),
                "room": room_name,
                "priority": priority.value,
            }

            # Emit to room
            self.socketio.emit(event, message_data, room=room_name)

            # Update stats
            with self.lock:
                self.health_stats["total_messages_sent"] += 1

            if priority in [MessagePriority.HIGH, MessagePriority.CRITICAL]:
                self._queue_message_for_room(room_name, event, message_data, priority)

            logger.debug(f"Message emitted to room {room_name}: {event}")
            return True

        except Exception as e:
            logger.error(f"Failed to emit to room {room_name}: {e}")
            with self.lock:
                self.health_stats["failed_messages"] += 1
            return False

    def emit_to_user(
        self,
        user_id: str,
        event: str,
        data: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> bool:
        """Emit message to all sessions of a specific user.

        Args:
            user_id: User ID
            event: Event name
            data: Message data
            priority: Message priority

        Returns:
            True if message was sent to at least one session
        """
        try:
            with self.lock:
                user_sessions = self.user_sessions.get(user_id, set()).copy()

            if not user_sessions:
                self._queue_message_for_user(user_id, event, data, priority)
                return False

            success = False
            for session_id in user_sessions:
                try:
                    message_data = {
                        **data,
                        "timestamp": datetime.now().isoformat(),
                        "user_id": user_id,
                        "priority": priority.value,
                    }

                    self.socketio.emit(event, message_data, room=session_id)
                    success = True

                except Exception as e:
                    logger.error(f"Failed to emit to session {session_id}: {e}")

            if success:
                with self.lock:
                    self.health_stats["total_messages_sent"] += 1
            else:
                with self.lock:
                    self.health_stats["failed_messages"] += 1

            return success

        except Exception as e:
            logger.error(f"Failed to emit to user {user_id}: {e}")
            with self.lock:
                self.health_stats["failed_messages"] += 1
            return False

    def _queue_message_for_room(
        self,
        room_name: str,
        event: str,
        data: Dict[str, Any],
        priority: MessagePriority,
    ):
        """Queue message for offline room members.

        Args:
            room_name: Room name
            event: Event name
            data: Message data
            priority: Message priority
        """
        message = QueuedMessage(
            message_id=str(uuid.uuid4()),
            room=room_name,
            event=event,
            data=data,
            priority=priority,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=self.message_retention),
        )

        self.message_queue[f"room:{room_name}"].append(message)

    def _queue_message_for_user(
        self, user_id: str, event: str, data: Dict[str, Any], priority: MessagePriority
    ):
        """Queue message for offline user.

        Args:
            user_id: User ID
            event: Event name
            data: Message data
            priority: Message priority
        """
        message = QueuedMessage(
            message_id=str(uuid.uuid4()),
            room=f"user:{user_id}",
            event=event,
            data=data,
            priority=priority,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=self.message_retention),
        )

        self.message_queue[f"user:{user_id}"].append(message)

    def _deliver_queued_messages(self, session_id: str):
        """Deliver queued messages to newly connected session.

        Args:
            session_id: Session ID
        """
        try:
            with self.lock:
                if session_id not in self.connections:
                    return

                connection = self.connections[session_id]
                user_id = connection.user_id

            # Deliver user-specific messages
            if user_id:
                queue_key = f"user:{user_id}"
                if queue_key in self.message_queue:
                    messages = list(self.message_queue[queue_key])
                    self.message_queue[queue_key].clear()

                    for message in messages:
                        if datetime.now() < message.expires_at:
                            try:
                                self.socketio.emit(
                                    message.event, message.data, room=session_id
                                )
                                logger.debug(
                                    f"Delivered queued message to {session_id}: {message.event}"
                                )
                            except Exception as e:
                                logger.error(f"Failed to deliver queued message: {e}")
                                if message.retry_count < message.max_retries:
                                    message.retry_count += 1
                                    self.message_queue[queue_key].append(message)

            # Deliver room-specific messages
            for room in connection.rooms:
                queue_key = f"room:{room}"
                if queue_key in self.message_queue:
                    messages = list(self.message_queue[queue_key])

                    for message in messages:
                        if datetime.now() < message.expires_at:
                            try:
                                self.socketio.emit(
                                    message.event, message.data, room=session_id
                                )
                                logger.debug(
                                    f"Delivered queued room message to {session_id}: {message.event}"
                                )
                            except Exception as e:
                                logger.error(
                                    f"Failed to deliver queued room message: {e}"
                                )

        except Exception as e:
            logger.error(f"Failed to deliver queued messages: {e}")

    def _start_background_tasks(self):
        """Start background maintenance tasks."""

        def cleanup_task():
            """Background cleanup task."""
            while True:
                try:
                    time.sleep(self.cleanup_interval)
                    self._cleanup_expired_data()
                    self._check_connection_health()
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")

        # Start cleanup thread
        cleanup_thread = Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()

        logger.info("Background tasks started")

    def _cleanup_expired_data(self):
        """Clean up expired connections and messages."""
        current_time = datetime.now()

        with self.lock:
            # Clean up old disconnected connections
            expired_connections = []
            for session_id, connection in self.connections.items():
                if (
                    connection.status == ConnectionStatus.DISCONNECTED
                    and current_time - connection.last_ping > timedelta(hours=1)
                ):
                    expired_connections.append(session_id)

            for session_id in expired_connections:
                del self.connections[session_id]

            # Clean up expired messages
            for queue_key, queue in list(self.message_queue.items()):
                expired_messages = []
                for i, message in enumerate(queue):
                    if current_time > message.expires_at:
                        expired_messages.append(i)

                # Remove expired messages (in reverse order to maintain indices)
                for i in reversed(expired_messages):
                    queue.remove(queue[i])

                # Remove empty queues
                if not queue:
                    del self.message_queue[queue_key]

        if expired_connections:
            logger.info(f"Cleaned up {len(expired_connections)} expired connections")

    def _check_connection_health(self):
        """Check health of active connections."""
        current_time = datetime.now()
        stale_connections = []

        with self.lock:
            for session_id, connection in self.connections.items():
                if (
                    connection.status == ConnectionStatus.CONNECTED
                    and current_time - connection.last_ping
                    > timedelta(seconds=self.ping_timeout * 3)
                ):
                    stale_connections.append(session_id)

        # Ping stale connections
        for session_id in stale_connections:
            try:
                self.socketio.emit(
                    "ping_request",
                    {"timestamp": current_time.isoformat()},
                    room=session_id,
                )
            except Exception as e:
                logger.warning(f"Failed to ping stale connection {session_id}: {e}")

    def get_connection_info(self, session_id: str) -> Optional[ConnectionInfo]:
        """Get connection information.

        Args:
            session_id: Session ID

        Returns:
            Connection information if found
        """
        with self.lock:
            return self.connections.get(session_id)

    def get_room_members(self, room_name: str) -> Set[str]:
        """Get members of a room.

        Args:
            room_name: Room name

        Returns:
            Set of session IDs in the room
        """
        with self.lock:
            return self.room_members.get(room_name, set()).copy()

    def get_user_sessions(self, user_id: str) -> Set[str]:
        """Get all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            Set of session IDs for the user
        """
        with self.lock:
            return self.user_sessions.get(user_id, set()).copy()

    def get_health_stats(self) -> Dict[str, Any]:
        """Get health statistics.

        Returns:
            Health statistics dictionary
        """
        with self.lock:
            stats = self.health_stats.copy()
            stats.update(
                {
                    "queued_messages": sum(len(q) for q in self.message_queue.values()),
                    "failed_messages_queued": len(self.failed_messages),
                    "total_rooms": len(self.room_members),
                    "total_users": len(self.user_sessions),
                }
            )
            return stats

    def add_connection_handler(self, handler: Callable[[ConnectionInfo], None]):
        """Add connection event handler.

        Args:
            handler: Handler function
        """
        self.connection_handlers.append(handler)

    def add_disconnection_handler(self, handler: Callable[[ConnectionInfo], None]):
        """Add disconnection event handler.

        Args:
            handler: Handler function
        """
        self.disconnection_handlers.append(handler)

    def add_message_handler(
        self, event: str, handler: Callable[[str, Dict[str, Any]], None]
    ):
        """Add message event handler.

        Args:
            event: Event name
            handler: Handler function
        """
        self.message_handlers[event].append(handler)

    def disconnect_session(self, session_id: str, reason: str = "Server disconnect"):
        """Disconnect a specific session.

        Args:
            session_id: Session ID to disconnect
            reason: Disconnect reason
        """
        try:
            disconnect(sid=session_id)
            logger.info(f"Disconnected session {session_id}: {reason}")
        except Exception as e:
            logger.error(f"Failed to disconnect session {session_id}: {e}")

    def disconnect_user(self, user_id: str, reason: str = "Server disconnect"):
        """Disconnect all sessions for a user.

        Args:
            user_id: User ID
            reason: Disconnect reason
        """
        try:
            with self.lock:
                user_sessions = self.user_sessions.get(user_id, set()).copy()

            for session_id in user_sessions:
                self.disconnect_session(session_id, reason)

            logger.info(f"Disconnected user {user_id}: {reason}")

        except Exception as e:
            logger.error(f"Failed to disconnect user {user_id}: {e}")

