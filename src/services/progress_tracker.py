"""
Progress Tracking Service for Real-time AI Processing Updates
Provides WebSocket-based progress updates and status tracking for the unified AI workflow.
"""

import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from threading import Lock

from utils.logger import logger
from .websocket_manager import WebSocketManager, MessagePriority

@dataclass
class ProgressUpdate:
    """Data class for progress updates"""
    session_id: str
    progress_id: str
    current_step: int
    total_steps: int
    current_operation: str
    submission_index: int
    total_submissions: int
    percentage: float
    estimated_time_remaining: Optional[float] = None
    status: str = "processing"  # processing, completed, error, paused
    details: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class ProgressTracker:
    """
    Progress tracking service for AI processing operations.
    Manages real-time progress updates and status tracking.
    """
    
    def __init__(self, websocket_manager: Optional[WebSocketManager] = None):
        """Initialize the progress tracker"""
        self.active_sessions: Dict[str, Dict] = {}
        self.progress_history: Dict[str, List[ProgressUpdate]] = {}
        self.session_lock = Lock()
        self.websocket_manager = websocket_manager
        self._realtime_service = None  # Will be set by realtime service
        
        logger.info("Progress Tracker initialized")
    
    def create_session(self, session_id: str, total_submissions: int) -> str:
        """
        Create a new progress tracking session.
        
        Args:
            session_id: Unique session identifier
            total_submissions: Total number of submissions to process
            
        Returns:
            str: Progress tracking ID
        """
        progress_id = str(uuid.uuid4())
        
        with self.session_lock:
            self.active_sessions[progress_id] = {
                'session_id': session_id,
                'progress_id': progress_id,
                'total_submissions': total_submissions,
                'start_time': time.time(),
                'status': 'initialized',
                'current_step': 0,
                'total_steps': 2 + total_submissions,  # Guide analysis + submissions + finalization
                'last_update': time.time()
            }
            
            self.progress_history[progress_id] = []
        
        logger.info(f"Created progress session {progress_id} for {total_submissions} submissions")
        return progress_id
    
    def update_progress(
        self, progress_id: str, current_step: int, current_operation: str, submission_index: int = 0, status: str = "processing", details: Optional[str] = None, percentage: Optional[float] = None
    ) -> ProgressUpdate:
        """
        Update progress for a session.
        
        Args:
            progress_id: Progress tracking ID
            current_step: Current step number
            current_operation: Description of current operation
            submission_index: Current submission index (0-based)
            status: Current status
            details: Additional details
            percentage: Optional pre-calculated percentage
            
        Returns:
            ProgressUpdate: The created progress update
        """
        with self.session_lock:
            if progress_id not in self.active_sessions:
                logger.warning(f"Progress ID {progress_id} not found")
                return None
            
            session = self.active_sessions[progress_id]
            session['current_step'] = current_step
            session['status'] = status
            session['last_update'] = time.time()
            
            # Use provided percentage or calculate it
            if percentage is None:
                calculated_percentage = (current_step / session['total_steps']) * 100
            else:
                calculated_percentage = percentage
            
            # Estimate time remaining
            elapsed_time = time.time() - session['start_time']
            estimated_time_remaining = None
            if current_step > 0 and status == "processing":
                avg_time_per_step = elapsed_time / current_step
                remaining_steps = session['total_steps'] - current_step
                estimated_time_remaining = avg_time_per_step * remaining_steps
            
            # Create progress update
            progress_update = ProgressUpdate(
                session_id=session['session_id'],
                progress_id=progress_id,
                current_step=current_step,
                total_steps=session['total_steps'],
                current_operation=current_operation,
                submission_index=submission_index,
                total_submissions=session['total_submissions'],
                percentage=min(calculated_percentage, 100.0),
                estimated_time_remaining=estimated_time_remaining,
                status=status,
                details=details
            )
            
            # Store in history
            self.progress_history[progress_id].append(progress_update)
            
            # Keep only last 50 updates per session
            if len(self.progress_history[progress_id]) > 50:
                self.progress_history[progress_id] = self.progress_history[progress_id][-50:]
        
        # Emit real-time update via WebSocket manager or fallback
        self._emit_progress_update(session['session_id'], progress_update)
        
        logger.debug(f"Progress update for {progress_id}: Step {current_step}/{session['total_steps']} ({calculated_percentage:.1f}%) - {current_operation}")
        return progress_update
    
    def set_realtime_service(self, realtime_service):
        """Set the realtime service for progress updates.
        
        Args:
            realtime_service: RealtimeService instance
        """
        self._realtime_service = realtime_service
    
    def _emit_progress_update(self, session_id: str, progress_update: ProgressUpdate):
        """Emit progress update via available channels.
        
        Args:
            session_id: Session ID
            progress_update: Progress update data
        """
        update_data = asdict(progress_update)
        
        # Try WebSocket manager first
        if self.websocket_manager:
            room = f'progress_{session_id}'
            success = self.websocket_manager.emit_to_room(
                room, 'progress_update', update_data, MessagePriority.NORMAL
            )
            if success:
                return
        
        # Try realtime service
        if self._realtime_service:
            try:
                self._realtime_service.emit_progress_update(session_id, update_data)
                return
            except Exception as e:
                logger.warning(f"Failed to emit via realtime service: {e}")
        
        # Fallback to direct SocketIO
        try:
            from flask_socketio import emit
            emit('progress_update', update_data, 
                 room=f'progress_{session_id}', namespace='/')
        except (ImportError, RuntimeError):
            # SocketIO not available or not in request context
            logger.debug(f"Could not emit progress update for session {session_id}")
    
    def complete_session(self, progress_id: str, success: bool = True, message: str = None) -> ProgressUpdate:
        """
        Mark a session as completed.
        
        Args:
            progress_id: Progress tracking ID
            success: Whether the operation was successful
            message: Completion message
            
        Returns:
            ProgressUpdate: Final progress update
        """
        with self.session_lock:
            if progress_id not in self.active_sessions:
                logger.warning(f"Progress ID {progress_id} not found")
                return None
            
            session = self.active_sessions[progress_id]
            status = "completed" if success else "error"
            
            progress_update = self.update_progress(
                progress_id=progress_id,
                current_step=session['total_steps'],
                current_operation="Processing completed" if success else "Processing failed",
                submission_index=session['total_submissions'],
                status=status,
                details=message,
                percentage=100.0 # Ensure 100% on completion
            )
            
            session['completed_at'] = time.time()
            session['final_status'] = status
        
        logger.info(f"Session {progress_id} completed with status: {status}")
        return progress_update
    
    def get_progress(self, progress_id: str) -> Optional[ProgressUpdate]:
        """
        Get the latest progress for a session.
        
        Args:
            progress_id: Progress tracking ID
            
        Returns:
            ProgressUpdate: Latest progress update or None
        """
        with self.session_lock:
            if progress_id not in self.progress_history:
                return None
            
            history = self.progress_history[progress_id]
            return history[-1] if history else None
    
    def get_progress_history(self, progress_id: str) -> List[ProgressUpdate]:
        """
        Get the full progress history for a session.
        
        Args:
            progress_id: Progress tracking ID
            
        Returns:
            List[ProgressUpdate]: List of progress updates
        """
        with self.session_lock:
            return self.progress_history.get(progress_id, []).copy()
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """
        Clean up old completed sessions.
        
        Args:
            max_age_hours: Maximum age in hours for keeping completed sessions
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        with self.session_lock:
            sessions_to_remove = []
            
            for progress_id, session in self.active_sessions.items():
                # Remove sessions that are completed and old
                if 'completed_at' in session:
                    age = current_time - session['completed_at']
                    if age > max_age_seconds:
                        sessions_to_remove.append(progress_id)
                elif current_time - session['last_update'] > max_age_seconds:
                    sessions_to_remove.append(progress_id)
            
            for progress_id in sessions_to_remove:
                del self.active_sessions[progress_id]
                if progress_id in self.progress_history:
                    del self.progress_history[progress_id]
                logger.info(f"Cleaned up old session: {progress_id}")
    
    def get_active_sessions(self) -> Dict[str, Dict]:
        """Get all active sessions"""
        with self.session_lock:
            return self.active_sessions.copy()
    
    def get_session_stats(self) -> Dict:
        """Get statistics about progress tracking"""
        with self.session_lock:
            active_count = len([s for s in self.active_sessions.values() if 'completed_at' not in s])
            completed_count = len([s for s in self.active_sessions.values() if 'completed_at' in s])
            
            return {
                'active_sessions': active_count,
                'completed_sessions': completed_count,
                'total_sessions': len(self.active_sessions),
                'total_history_entries': sum(len(h) for h in self.progress_history.values())
            }
    
    def create_progress_callback(self, progress_id: str) -> Callable:
        """
        Create a progress callback function for use with AI services.
        
        Args:
            progress_id: Progress tracking ID
            
        Returns:
            Callable: Progress callback function
        """
        def progress_callback(progress_data):
            """Callback function that updates progress"""
            if hasattr(progress_data, 'current_step'):
                # Handle ProcessingProgress objects
                self.update_progress(
                    progress_id=progress_id,
                    current_step=progress_data.current_step,
                    current_operation=progress_data.current_operation,
                    submission_index=progress_data.submission_index,
                    status=progress_data.status,
                    details=progress_data.details,
                    percentage=progress_data.percentage # Pass the percentage
                )
            elif isinstance(progress_data, dict):
                # Handle dictionary progress data
                self.update_progress(
                    progress_id=progress_id,
                    current_step=progress_data.get('current_step', 0),
                    current_operation=progress_data.get('current_operation', 'Processing...'),
                    submission_index=progress_data.get('submission_index', 0),
                    status=progress_data.get('status', 'processing'),
                    details=progress_data.get('details')
                )
        
        return progress_callback
    
    def to_json(self, progress_update: ProgressUpdate) -> str:
        """Convert progress update to JSON string"""
        return json.dumps(asdict(progress_update), default=str)
    
    def from_json(self, json_str: str) -> ProgressUpdate:
        """Create progress update from JSON string"""
        data = json.loads(json_str)
        return ProgressUpdate(**data)

# Global progress tracker instance
progress_tracker = ProgressTracker()
