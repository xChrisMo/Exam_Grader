"""
Loading states and progress management for the Exam Grader application.
"""

import threading
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from utils.logger import setup_logger

logger = setup_logger(__name__)


class LoadingState(Enum):
    """Enumeration of loading states."""

    IDLE = "idle"
    LOADING = "loading"
    PROCESSING = "processing"
    UPLOADING = "uploading"
    ANALYZING = "analyzing"
    MAPPING = "mapping"
    GRADING = "grading"
    SAVING = "saving"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class ProgressInfo:
    """Progress information for operations."""

    operation_id: str
    operation_name: str
    state: LoadingState
    current_step: int
    total_steps: int
    progress_percent: float
    message: str
    start_time: float
    elapsed_time: float
    estimated_remaining: Optional[float] = None
    sub_operations: List[Dict] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result["state"] = self.state.value
        result["sub_operations"] = self.sub_operations or []
        return result


class LoadingManager:
    """Manages loading states and progress for multiple operations."""

    def __init__(self):
        self._operations: Dict[str, ProgressInfo] = {}
        self._lock = threading.RLock()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()

    def start_operation(
        self,
        operation_id: str,
        operation_name: str,
        total_steps: int = 100,
        initial_message: str = "Starting...",
    ) -> ProgressInfo:
        """
        Start a new operation with progress tracking.

        Args:
            operation_id: Unique identifier for the operation
            operation_name: Human-readable name for the operation
            total_steps: Total number of steps in the operation
            initial_message: Initial status message

        Returns:
            ProgressInfo object for the operation
        """
        with self._lock:
            progress = ProgressInfo(
                operation_id=operation_id,
                operation_name=operation_name,
                state=LoadingState.LOADING,
                current_step=0,
                total_steps=total_steps,
                progress_percent=0.0,
                message=initial_message,
                start_time=time.time(),
                elapsed_time=0.0,
                sub_operations=[],
            )

            self._operations[operation_id] = progress
            logger.info(f"Started operation: {operation_name} (ID: {operation_id})")
            return progress

    def update_progress(
        self,
        operation_id: str,
        current_step: Optional[int] = None,
        message: Optional[str] = None,
        state: Optional[LoadingState] = None,
        increment: bool = False,
    ) -> Optional[ProgressInfo]:
        """
        Update progress for an operation.

        Args:
            operation_id: ID of the operation to update
            current_step: Current step number (or None to keep current)
            message: Status message (or None to keep current)
            state: New loading state (or None to keep current)
            increment: Whether to increment current_step by 1

        Returns:
            Updated ProgressInfo or None if operation not found
        """
        with self._lock:
            if operation_id not in self._operations:
                logger.warning(
                    f"Operation {operation_id} not found for progress update"
                )
                return None

            progress = self._operations[operation_id]

            # Update fields
            if increment:
                progress.current_step += 1
            elif current_step is not None:
                progress.current_step = current_step

            if message is not None:
                progress.message = message

            if state is not None:
                progress.state = state

            # Calculate progress percentage
            if progress.total_steps > 0:
                progress.progress_percent = min(
                    100.0, (progress.current_step / progress.total_steps) * 100
                )

            # Update timing
            progress.elapsed_time = time.time() - progress.start_time

            # Estimate remaining time
            if progress.current_step > 0 and progress.progress_percent < 100:
                avg_time_per_step = progress.elapsed_time / progress.current_step
                remaining_steps = progress.total_steps - progress.current_step
                progress.estimated_remaining = avg_time_per_step * remaining_steps

            logger.debug(
                f"Updated operation {operation_id}: {progress.progress_percent:.1f}% - {message}"
            )
            return progress

    def add_sub_operation(
        self, operation_id: str, sub_operation: Dict[str, Any]
    ) -> bool:
        """
        Add a sub-operation to track nested progress.

        Args:
            operation_id: Parent operation ID
            sub_operation: Sub-operation information

        Returns:
            True if successful, False if operation not found
        """
        with self._lock:
            if operation_id not in self._operations:
                return False

            progress = self._operations[operation_id]
            if progress.sub_operations is None:
                progress.sub_operations = []

            progress.sub_operations.append(sub_operation)
            return True

    def complete_operation(
        self, operation_id: str, final_message: str = "Completed", success: bool = True
    ) -> Optional[ProgressInfo]:
        """
        Mark an operation as complete.

        Args:
            operation_id: ID of the operation to complete
            final_message: Final status message
            success: Whether the operation completed successfully

        Returns:
            Final ProgressInfo or None if operation not found
        """
        with self._lock:
            if operation_id not in self._operations:
                return None

            progress = self._operations[operation_id]
            progress.current_step = progress.total_steps
            progress.progress_percent = 100.0
            progress.message = final_message
            progress.state = LoadingState.COMPLETE if success else LoadingState.ERROR
            progress.elapsed_time = time.time() - progress.start_time
            progress.estimated_remaining = 0.0

            logger.info(
                f"Completed operation {operation_id}: {final_message} in {progress.elapsed_time:.1f}s"
            )
            return progress

    def fail_operation(
        self, operation_id: str, error_message: str
    ) -> Optional[ProgressInfo]:
        """
        Mark an operation as failed.

        Args:
            operation_id: ID of the operation that failed
            error_message: Error message

        Returns:
            Final ProgressInfo or None if operation not found
        """
        with self._lock:
            if operation_id not in self._operations:
                return None

            progress = self._operations[operation_id]
            progress.state = LoadingState.ERROR
            progress.error_message = error_message
            progress.message = f"Error: {error_message}"
            progress.elapsed_time = time.time() - progress.start_time

            logger.error(f"Operation {operation_id} failed: {error_message}")
            return progress

    def get_operation(self, operation_id: str) -> Optional[ProgressInfo]:
        """Get progress information for an operation."""
        with self._lock:
            return self._operations.get(operation_id)

    def get_all_operations(self) -> Dict[str, ProgressInfo]:
        """Get all current operations."""
        with self._lock:
            return self._operations.copy()

    def get_active_operations(self) -> Dict[str, ProgressInfo]:
        """Get only active (non-complete, non-error) operations."""
        with self._lock:
            return {
                op_id: progress
                for op_id, progress in self._operations.items()
                if progress.state
                not in [
                    LoadingState.COMPLETE,
                    LoadingState.ERROR,
                    LoadingState.CANCELLED,
                ]
            }

    def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel an operation.

        Args:
            operation_id: ID of the operation to cancel

        Returns:
            True if successful, False if operation not found
        """
        with self._lock:
            if operation_id not in self._operations:
                return False

            progress = self._operations[operation_id]
            progress.state = LoadingState.CANCELLED
            progress.message = "Operation cancelled"
            progress.elapsed_time = time.time() - progress.start_time

            logger.info(f"Cancelled operation {operation_id}")
            return True

    def cleanup_old_operations(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up old completed operations.

        Args:
            max_age_seconds: Maximum age in seconds for completed operations

        Returns:
            Number of operations cleaned up
        """
        current_time = time.time()
        cleaned_count = 0

        with self._lock:
            operations_to_remove = []

            for op_id, progress in self._operations.items():
                if progress.state in [
                    LoadingState.COMPLETE,
                    LoadingState.ERROR,
                    LoadingState.CANCELLED,
                ]:
                    age = current_time - progress.start_time
                    if age > max_age_seconds:
                        operations_to_remove.append(op_id)

            for op_id in operations_to_remove:
                del self._operations[op_id]
                cleaned_count += 1

            self._last_cleanup = current_time

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old operations")

        return cleaned_count

    def auto_cleanup(self):
        """Automatically cleanup old operations if needed."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self.cleanup_old_operations()


# Global loading manager instance
loading_manager = LoadingManager()


def create_loading_response(
    operation_id: str, message: str = "Processing...", include_progress: bool = True
) -> Dict[str, Any]:
    """
    Create a standardized loading response for API endpoints.

    Args:
        operation_id: ID of the operation
        message: Loading message
        include_progress: Whether to include progress information

    Returns:
        Loading response dictionary
    """
    response = {"loading": True, "operation_id": operation_id, "message": message}

    if include_progress:
        progress = loading_manager.get_operation(operation_id)
        if progress:
            response["progress"] = progress.to_dict()

    return response


def get_loading_state_for_template(operation_ids: List[str] = None) -> Dict[str, Any]:
    """
    Get loading state information for template rendering.

    Args:
        operation_ids: Specific operation IDs to include (or None for all active)

    Returns:
        Loading state information for templates
    """
    if operation_ids:
        operations = {
            op_id: loading_manager.get_operation(op_id)
            for op_id in operation_ids
            if loading_manager.get_operation(op_id)
        }
    else:
        operations = loading_manager.get_active_operations()

    # Convert to template-friendly format
    loading_states = {}
    for op_id, progress in operations.items():
        if progress:
            loading_states[op_id] = {
                "name": progress.operation_name,
                "state": progress.state.value,
                "progress": progress.progress_percent,
                "message": progress.message,
                "elapsed": progress.elapsed_time,
                "estimated_remaining": progress.estimated_remaining,
            }

    return {
        "loading_operations": loading_states,
        "has_active_operations": len(loading_states) > 0,
        "total_active_operations": len(loading_states),
    }
