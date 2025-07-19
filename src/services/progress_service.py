"""Unified Progress Service that integrates both in-memory and persistent progress trackers."""

import time
from typing import Any, Callable, Dict, List, Optional

from ..utils.logging_config import get_logger
from .persistent_progress_tracker import PersistentProgressTracker
from .progress_tracker import ProgressTracker
from .websocket_manager import WebSocketManager

# Handle case where get_logger might be None due to import issues
if get_logger is not None:
    logger = get_logger(__name__)
else:
    import logging
    logger = logging.getLogger(__name__)


class ProgressService:
    """Unified progress service that manages both in-memory and persistent progress tracking."""
    
    def __init__(
        self,
        websocket_manager: Optional[WebSocketManager] = None,
        enable_persistence: bool = True,
        fallback_to_memory: bool = True
    ):
        """Initialize the progress service.
        
        Args:
            websocket_manager: Optional WebSocket manager for real-time updates
            enable_persistence: Whether to enable persistent progress tracking
            fallback_to_memory: Whether to fallback to in-memory tracking if persistence fails
        """
        self.websocket_manager = websocket_manager
        self.enable_persistence = enable_persistence
        self.fallback_to_memory = fallback_to_memory
        self.logger = logger
        
        # Initialize trackers
        self.persistent_tracker: Optional[PersistentProgressTracker] = None
        self.memory_tracker: Optional[ProgressTracker] = None
        
        self._init_trackers()
        
        logger.info(f"Progress service initialized - Persistence: {enable_persistence}, Fallback: {fallback_to_memory}")
    
    def _init_trackers(self):
        """Initialize progress trackers based on configuration."""
        # Initialize persistent tracker if enabled
        if self.enable_persistence:
            try:
                self.persistent_tracker = PersistentProgressTracker(
                    websocket_manager=self.websocket_manager
                )
                logger.info("Persistent progress tracker initialized")
            except Exception as e:
                logger.error(f"Failed to initialize persistent tracker: {e}")
                if not self.fallback_to_memory:
                    raise
        
        # Initialize memory tracker if needed
        if not self.persistent_tracker or self.fallback_to_memory:
            try:
                self.memory_tracker = ProgressTracker(
                    websocket_manager=self.websocket_manager
                )
                logger.info("In-memory progress tracker initialized")
            except Exception as e:
                logger.error(f"Failed to initialize memory tracker: {e}")
                if not self.persistent_tracker:
                    raise
    
    def set_realtime_service(self, realtime_service):
        """Set the realtime service for both trackers.
        
        Args:
            realtime_service: RealtimeService instance
        """
        if self.persistent_tracker:
            self.persistent_tracker.set_realtime_service(realtime_service)
        
        if self.memory_tracker:
            self.memory_tracker.set_realtime_service(realtime_service)
    
    def create_session(
        self,
        session_id: str,
        total_steps: int,
        total_submissions: int = 1,
        user_id: Optional[str] = None,
        session_type: Optional[str] = None,
        estimated_duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        use_persistence: Optional[bool] = None
    ) -> str:
        """Create a new progress session.
        
        Args:
            session_id: Unique session identifier
            total_steps: Total number of steps in the process
            total_submissions: Total number of submissions to process
            user_id: Optional user ID
            session_type: Type of session (ocr, grading, mapping, etc.)
            estimated_duration: Estimated duration in seconds
            metadata: Additional session metadata
            use_persistence: Override default persistence setting
            
        Returns:
            Session ID
        """
        # Determine which tracker to use
        use_persistent = (
            use_persistence if use_persistence is not None 
            else self.enable_persistence
        )
        
        # Try persistent tracker first
        if use_persistent and self.persistent_tracker:
            try:
                return self.persistent_tracker.create_session(
                    session_id=session_id,
                    total_steps=total_steps,
                    total_submissions=total_submissions,
                    user_id=user_id,
                    session_type=session_type,
                    estimated_duration=estimated_duration,
                    metadata=metadata
                )
            except Exception as e:
                logger.warning(f"Persistent tracker failed, falling back to memory: {e}")
                if not self.fallback_to_memory:
                    raise
        
        # Fallback to memory tracker
        if self.memory_tracker:
            return self.memory_tracker.create_session(
                session_id=session_id,
                total_steps=total_steps,
                total_submissions=total_submissions
            )
        
        raise RuntimeError("No available progress tracker")
    
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
    ) -> bool:
        """Update progress for a session.
        
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
            True if update was successful
        """
        success = False
        
        # Try persistent tracker first
        if self.persistent_tracker:
            try:
                update = self.persistent_tracker.update_progress(
                    session_id=session_id,
                    step_number=step_number,
                    operation=operation,
                    submission_index=submission_index,
                    status=status,
                    details=details,
                    error_message=error_message,
                    metrics=metrics
                )
                success = update is not None
            except Exception as e:
                logger.warning(f"Persistent tracker update failed: {e}")
        
        # Try memory tracker if persistent failed or as backup
        if not success and self.memory_tracker:
            try:
                # Create progress data for memory tracker
                progress_data = {
                    "current_step": step_number,
                    "operation": operation,
                    "submission_index": submission_index,
                    "status": status,
                    "details": details,
                    "error_message": error_message
                }
                
                self.memory_tracker.update_progress(session_id, progress_data)
                success = True
            except Exception as e:
                logger.error(f"Memory tracker update failed: {e}")
        
        return success
    
    def complete_session(
        self,
        session_id: str,
        status: str = "completed",
        final_message: Optional[str] = None
    ) -> bool:
        """Mark a session as completed.
        
        Args:
            session_id: Session identifier
            status: Final status (completed, failed, cancelled)
            final_message: Final message
            
        Returns:
            True if successful
        """
        success = False
        
        # Try persistent tracker first
        if self.persistent_tracker:
            try:
                success = self.persistent_tracker.complete_session(
                    session_id=session_id,
                    status=status,
                    final_message=final_message
                )
            except Exception as e:
                logger.warning(f"Persistent tracker completion failed: {e}")
        
        # Try memory tracker if persistent failed
        if not success and self.memory_tracker:
            try:
                # Memory tracker doesn't have explicit completion, just update status
                final_data = {
                    "status": status,
                    "details": final_message,
                    "completed": True
                }
                self.memory_tracker.update_progress(session_id, final_data)
                success = True
            except Exception as e:
                logger.error(f"Memory tracker completion failed: {e}")
        
        return success
    
    def get_session_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Progress data dictionary or None
        """
        # Try persistent tracker first
        if self.persistent_tracker:
            try:
                progress = self.persistent_tracker.get_session_progress(session_id)
                if progress:
                    return progress
            except Exception as e:
                logger.warning(f"Persistent tracker get progress failed: {e}")
        
        # Try memory tracker
        if self.memory_tracker:
            try:
                return self.memory_tracker.get_latest_progress(session_id)
            except Exception as e:
                logger.error(f"Memory tracker get progress failed: {e}")
        
        return None
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get full progress history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of progress updates
        """
        # Try persistent tracker first (only it has full history)
        if self.persistent_tracker:
            try:
                return self.persistent_tracker.get_session_history(session_id)
            except Exception as e:
                logger.warning(f"Persistent tracker get history failed: {e}")
        
        # Memory tracker has limited history
        if self.memory_tracker:
            try:
                history = self.memory_tracker.get_progress_history(session_id)
                return history if history else []
            except Exception as e:
                logger.error(f"Memory tracker get history failed: {e}")
        
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
        # Only persistent tracker supports recovery
        if self.persistent_tracker:
            try:
                return self.persistent_tracker.recover_session(
                    session_id=session_id,
                    recovery_type=recovery_type,
                    recovery_point=recovery_point,
                    recovery_data=recovery_data
                )
            except Exception as e:
                logger.error(f"Session recovery failed: {e}")
        
        logger.warning(f"Session recovery not available for {session_id}")
        return False
    
    def get_active_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all active progress sessions.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of active session data
        """
        sessions = []
        
        # Get from persistent tracker
        if self.persistent_tracker:
            try:
                sessions.extend(
                    self.persistent_tracker.get_active_sessions(user_id=user_id)
                )
            except Exception as e:
                logger.warning(f"Failed to get persistent active sessions: {e}")
        
        # Get from memory tracker
        if self.memory_tracker:
            try:
                memory_sessions = self.memory_tracker.get_active_sessions()
                # Convert to expected format and filter by user if needed
                for session_id, session_data in memory_sessions.items():
                    if not user_id or session_data.get('user_id') == user_id:
                        sessions.append({
                            'session_id': session_id,
                            'status': 'active',
                            **session_data
                        })
            except Exception as e:
                logger.warning(f"Failed to get memory active sessions: {e}")
        
        return sessions
    
    def cleanup_old_sessions(self, days_old: int = 7) -> int:
        """Clean up old completed sessions.
        
        Args:
            days_old: Number of days old to consider for cleanup
            
        Returns:
            Number of sessions cleaned up
        """
        total_cleaned = 0
        
        # Cleanup persistent tracker
        if self.persistent_tracker:
            try:
                total_cleaned += self.persistent_tracker.cleanup_old_sessions(days_old)
            except Exception as e:
                logger.warning(f"Persistent tracker cleanup failed: {e}")
        
        # Cleanup memory tracker
        if self.memory_tracker:
            try:
                cleaned = self.memory_tracker.cleanup_old_sessions()
                total_cleaned += cleaned
            except Exception as e:
                logger.warning(f"Memory tracker cleanup failed: {e}")
        
        return total_cleaned
    
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
        # Only persistent tracker has detailed metrics
        if self.persistent_tracker:
            try:
                return self.persistent_tracker.get_performance_metrics(
                    session_id=session_id,
                    metric_type=metric_type,
                    hours=hours
                )
            except Exception as e:
                logger.warning(f"Failed to get performance metrics: {e}")
        
        return []
    
    def create_progress_callback(self, session_id: str) -> Callable:
        """Create a progress callback function for AI services.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Callback function
        """
        def progress_callback(progress_data):
            """Unified callback function that updates progress via the service."""
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
                logger.error(f"Error in unified progress callback for {session_id}: {e}")
        
        return progress_callback
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the progress service.
        
        Returns:
            Service status information
        """
        return {
            "persistent_tracker_available": self.persistent_tracker is not None,
            "memory_tracker_available": self.memory_tracker is not None,
            "websocket_manager_available": self.websocket_manager is not None,
            "persistence_enabled": self.enable_persistence,
            "fallback_enabled": self.fallback_to_memory
        }


# Global instance
progress_service = ProgressService()