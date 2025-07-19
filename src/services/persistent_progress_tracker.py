"""Enhanced Progress Tracker with Database Persistence and Recovery."""

import json
import time
import uuid
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from ..database.models import db
from ..database.progress_models import (
    ProgressMetrics,
    ProgressRecovery,
    ProgressSession,
    ProgressUpdate,
)
from ..utils.logging_config import get_logger
from .websocket_manager import MessagePriority, WebSocketManager

# Handle case where get_logger might be None due to import issues
if get_logger is not None:
    logger = get_logger(__name__)
else:
    import logging
    logger = logging.getLogger(__name__)


class PersistentProgressTracker:
    """Enhanced progress tracker with database persistence and recovery capabilities."""
    
    def __init__(self, websocket_manager: Optional[WebSocketManager] = None):
        """Initialize the persistent progress tracker.
        
        Args:
            websocket_manager: Optional WebSocket manager for real-time updates
        """
        self.websocket_manager = websocket_manager
        self._realtime_service = None
        self.lock = Lock()
        self.logger = logger
        
        # In-memory cache for active sessions
        self._active_sessions_cache: Dict[str, ProgressSession] = {}
        self._cache_lock = Lock()
        
        # Performance metrics
        self._metrics_buffer: List[Dict[str, Any]] = []
        self._metrics_lock = Lock()
        
        logger.info("Persistent Progress Tracker initialized")
    
    def set_realtime_service(self, realtime_service):
        """Set the realtime service for progress updates.
        
        Args:
            realtime_service: RealtimeService instance
        """
        self._realtime_service = realtime_service
    
    def create_session(
        self,
        session_id: str,
        total_steps: int,
        total_submissions: int = 1,
        user_id: Optional[str] = None,
        session_type: Optional[str] = None,
        estimated_duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new persistent progress session.
        
        Args:
            session_id: Unique session identifier
            total_steps: Total number of steps in the process
            total_submissions: Total number of submissions to process
            user_id: Optional user ID
            session_type: Type of session (ocr, grading, mapping, etc.)
            estimated_duration: Estimated duration in seconds
            metadata: Additional session metadata
            
        Returns:
            Session ID
        """
        try:
            # Create database session
            progress_session = ProgressSession(
                session_id=session_id,
                user_id=user_id,
                total_steps=total_steps,
                total_submissions=total_submissions,
                session_type=session_type,
                estimated_duration=estimated_duration,
                session_metadata=metadata or {}
            )
            
            db.session.add(progress_session)
            db.session.commit()
            
            # Cache the session
            with self._cache_lock:
                self._active_sessions_cache[session_id] = progress_session
            
            logger.info(f"Created persistent progress session: {session_id}")
            return session_id
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to create progress session {session_id}: {e}")
            raise
    
    def update_progress(
        self,
        session_id: str,
        step_number: int,
        operation: str,
        submission_index: int = 0,
        status: str = "processing",
        details: Optional[str] = None,
        error_message: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> Optional[ProgressUpdate]:
        """Update progress for a session with database persistence.
        
        Args:
            session_id: Session identifier
            step_number: Current step number
            operation: Description of current operation
            submission_index: Current submission index
            status: Current status
            details: Additional details
            error_message: Error message if any
            metrics: Performance metrics
            
        Returns:
            ProgressUpdate object or None if failed
        """
        try:
            # Get or load session
            progress_session = self._get_session(session_id)
            if not progress_session:
                logger.warning(f"Session {session_id} not found")
                return None
            
            # Calculate percentage
            percentage = self._calculate_percentage(
                progress_session, step_number, submission_index
            )
            
            # Calculate estimated time remaining
            estimated_remaining = progress_session.calculate_estimated_remaining()
            
            # Create progress update
            progress_update = ProgressUpdate(
                session_id=session_id,
                step_number=step_number,
                operation=operation,
                submission_index=submission_index,
                percentage=percentage,
                estimated_time_remaining=estimated_remaining,
                status=status,
                details=details,
                error_message=error_message,
                metrics=metrics or {}
            )
            
            # Update session current state
            progress_session.current_step = step_number
            progress_session.current_submission = submission_index
            if status in ["failed", "error"]:
                progress_session.status = "failed"
            
            # Save to database
            db.session.add(progress_update)
            db.session.commit()
            
            # Emit real-time update
            self._emit_progress_update(session_id, progress_update)
            
            # Record metrics if provided
            if metrics:
                self._record_metrics(session_id, metrics)
            
            logger.debug(f"Progress updated for {session_id}: {percentage:.1f}% - {operation}")
            return progress_update
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to update progress for {session_id}: {e}")
            return None
    
    def complete_session(
        self,
        session_id: str,
        status: str = "completed",
        final_message: Optional[str] = None,
        end_time: Optional[datetime] = None
    ) -> bool:
        """Mark a session as completed with persistence.
        
        Args:
            session_id: Session identifier
            status: Final status (completed, failed, cancelled)
            final_message: Final message
            end_time: End time (defaults to now)
            
        Returns:
            True if successful
        """
        try:
            progress_session = self._get_session(session_id)
            if not progress_session:
                logger.warning(f"Session {session_id} not found")
                return False
            
            # Complete the session
            progress_session.complete(status, end_time)
            
            # Create final progress update
            final_update = ProgressUpdate(
                session_id=session_id,
                step_number=progress_session.total_steps,
                operation="Completed",
                submission_index=progress_session.total_submissions - 1,
                percentage=100.0,
                status=status,
                details=final_message
            )
            
            db.session.add(final_update)
            db.session.commit()
            
            # Remove from cache
            with self._cache_lock:
                self._active_sessions_cache.pop(session_id, None)
            
            # Emit completion update
            self._emit_progress_update(session_id, final_update)
            
            logger.info(f"Session {session_id} completed with status: {status}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to complete session {session_id}: {e}")
            return False
    
    def get_session_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Progress data dictionary or None
        """
        try:
            progress_session = self._get_session(session_id)
            if not progress_session:
                return None
            
            # Get latest progress update
            latest_update = (
                db.session.query(ProgressUpdate)
                .filter_by(session_id=session_id)
                .order_by(ProgressUpdate.created_at.desc())
                .first()
            )
            
            result = progress_session.to_dict()
            if latest_update:
                result.update({
                    "latest_operation": latest_update.operation,
                    "latest_details": latest_update.details,
                    "latest_update_time": latest_update.created_at.isoformat(),
                })
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get session progress {session_id}: {e}")
            return None
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get full progress history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of progress updates
        """
        try:
            updates = (
                db.session.query(ProgressUpdate)
                .filter_by(session_id=session_id)
                .order_by(ProgressUpdate.created_at)
                .all()
            )
            
            return [update.to_dict() for update in updates]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get session history {session_id}: {e}")
            return []
    
    def recover_session(
        self,
        session_id: str,
        recovery_type: str = "resume",
        recovery_point: Optional[int] = None,
        recovery_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Recover a failed or interrupted session.
        
        Args:
            session_id: Session identifier
            recovery_type: Type of recovery (resume, restart, rollback)
            recovery_point: Step to recover from
            recovery_data: Additional recovery data
            
        Returns:
            True if recovery initiated successfully
        """
        try:
            progress_session = self._get_session(session_id, include_completed=True)
            if not progress_session:
                logger.warning(f"Session {session_id} not found for recovery")
                return False
            
            # Determine recovery point
            if recovery_point is None:
                if recovery_type == "restart":
                    recovery_point = 0
                else:
                    recovery_point = progress_session.current_step
            
            # Create recovery record
            recovery_record = ProgressRecovery(
                session_id=session_id,
                recovery_type=recovery_type,
                recovery_point=recovery_point,
                recovery_data=recovery_data or {},
                recovery_status="pending"
            )
            
            # Reset session state for recovery
            if recovery_type == "restart":
                progress_session.current_step = 0
                progress_session.current_submission = 0
            elif recovery_type == "rollback":
                progress_session.current_step = max(0, recovery_point)
            
            progress_session.status = "active"
            progress_session.end_time = None
            
            db.session.add(recovery_record)
            db.session.commit()
            
            # Add back to cache
            with self._cache_lock:
                self._active_sessions_cache[session_id] = progress_session
            
            logger.info(f"Recovery initiated for session {session_id}: {recovery_type} from step {recovery_point}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to recover session {session_id}: {e}")
            return False
    
    def get_active_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all active progress sessions.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of active session data
        """
        try:
            query = db.session.query(ProgressSession).filter_by(status="active")
            
            if user_id:
                query = query.filter_by(user_id=user_id)
            
            sessions = query.all()
            return [session.to_dict() for session in sessions]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
    
    def cleanup_old_sessions(self, days_old: int = 7) -> int:
        """Clean up old completed sessions.
        
        Args:
            days_old: Number of days old to consider for cleanup
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Delete old completed sessions and their updates
            deleted_count = (
                db.session.query(ProgressSession)
                .filter(
                    ProgressSession.status.in_(["completed", "failed", "cancelled"]),
                    ProgressSession.end_time < cutoff_date
                )
                .delete(synchronize_session=False)
            )
            
            db.session.commit()
            
            logger.info(f"Cleaned up {deleted_count} old progress sessions")
            return deleted_count
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0
    
    def get_performance_metrics(
        self,
        session_id: Optional[str] = None,
        metric_type: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get performance metrics.
        
        Args:
            session_id: Optional session ID to filter by
            metric_type: Optional metric type to filter by
            hours: Number of hours to look back
            
        Returns:
            List of metrics
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = db.session.query(ProgressMetrics).filter(
                ProgressMetrics.measurement_time >= cutoff_time
            )
            
            if session_id:
                query = query.filter_by(session_id=session_id)
            
            if metric_type:
                query = query.filter_by(metric_type=metric_type)
            
            metrics = query.order_by(ProgressMetrics.measurement_time.desc()).all()
            return [metric.to_dict() for metric in metrics]
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return []
    
    def create_progress_callback(self, session_id: str) -> Callable:
        """Create a progress callback function for AI services.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Callback function
        """
        def progress_callback(progress_data):
            """Callback function that updates progress."""
            try:
                if hasattr(progress_data, 'current_step'):
                    # Handle ProcessingProgress objects
                    self.update_progress(
                        session_id=session_id,
                        step_number=progress_data.current_step,
                        operation=getattr(progress_data, 'current_operation', 'Processing'),
                        submission_index=getattr(progress_data, 'submission_index', 0),
                        status=getattr(progress_data, 'status', 'processing'),
                        details=getattr(progress_data, 'details', None)
                    )
                elif isinstance(progress_data, dict):
                    # Handle dictionary progress data
                    self.update_progress(
                        session_id=session_id,
                        step_number=progress_data.get('current_step', 0),
                        operation=progress_data.get('operation', 'Processing'),
                        submission_index=progress_data.get('submission_index', 0),
                        status=progress_data.get('status', 'processing'),
                        details=progress_data.get('details')
                    )
            except Exception as e:
                logger.error(f"Error in progress callback for {session_id}: {e}")
        
        return progress_callback
    
    def _get_session(
        self, 
        session_id: str, 
        include_completed: bool = False
    ) -> Optional[ProgressSession]:
        """Get session from cache or database.
        
        Args:
            session_id: Session identifier
            include_completed: Whether to include completed sessions
            
        Returns:
            ProgressSession or None
        """
        # Check cache first
        with self._cache_lock:
            if session_id in self._active_sessions_cache:
                return self._active_sessions_cache[session_id]
        
        # Query database
        try:
            query = db.session.query(ProgressSession).filter_by(session_id=session_id)
            
            if not include_completed:
                query = query.filter_by(status="active")
            
            session = query.first()
            
            # Cache active sessions
            if session and session.is_active():
                with self._cache_lock:
                    self._active_sessions_cache[session_id] = session
            
            return session
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    def _calculate_percentage(
        self, 
        session: ProgressSession, 
        step_number: int, 
        submission_index: int
    ) -> float:
        """Calculate progress percentage.
        
        Args:
            session: Progress session
            step_number: Current step number
            submission_index: Current submission index
            
        Returns:
            Progress percentage
        """
        if session.total_steps == 0:
            return 0.0
        
        # Calculate based on submissions and steps
        submission_progress = (submission_index / session.total_submissions) * 100
        step_progress = (step_number / session.total_steps) * (100 / session.total_submissions)
        
        return min(submission_progress + step_progress, 100.0)
    
    def _emit_progress_update(self, session_id: str, progress_update: ProgressUpdate):
        """Emit progress update via available channels.
        
        Args:
            session_id: Session identifier
            progress_update: Progress update data
        """
        update_data = progress_update.to_dict()
        
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
            logger.debug(f"Could not emit progress update for session {session_id}")
    
    def _record_metrics(self, session_id: str, metrics: Dict[str, Any]):
        """Record performance metrics.
        
        Args:
            session_id: Session identifier
            metrics: Metrics data
        """
        try:
            for metric_type, value in metrics.items():
                if isinstance(value, (int, float)):
                    metric = ProgressMetrics(
                        session_id=session_id,
                        metric_type=metric_type,
                        metric_value=float(value),
                        metric_unit=metrics.get(f"{metric_type}_unit", "")
                    )
                    db.session.add(metric)
            
            db.session.commit()
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.warning(f"Failed to record metrics for {session_id}: {e}")


# Global instance
persistent_progress_tracker = PersistentProgressTracker()