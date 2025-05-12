"""
Progress tracking service for long-running operations.

This module provides functionality to track and report progress for
long-running operations like LLM calls and OCR processing.
"""

import os
import json
import time
import uuid
from typing import Dict, Optional, List, Any
from pathlib import Path
from threading import Lock

from utils.logger import logger

# Lock for thread-safe operations
_progress_lock = Lock()

class ProgressService:
    """
    Service for tracking progress of long-running operations.
    
    This class provides methods to:
    - Create progress trackers for operations
    - Update progress status
    - Retrieve current progress
    - Clean up completed or stale progress trackers
    """
    
    def __init__(self, progress_dir: str = "temp/progress"):
        """
        Initialize the progress service.
        
        Args:
            progress_dir: Directory to store progress files
        """
        self.progress_dir = Path(progress_dir)
        self.progress_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Progress service initialized with directory: {progress_dir}")
        
        # Clean up stale progress files on initialization
        self._cleanup_stale_progress()
    
    def create_tracker(self, operation_type: str, task_name: str, total_steps: int = 100) -> str:
        """
        Create a new progress tracker.
        
        Args:
            operation_type: Type of operation (e.g., 'llm', 'ocr')
            task_name: Name of the task being tracked
            total_steps: Total number of steps in the operation
            
        Returns:
            str: Unique ID for the progress tracker
        """
        tracker_id = str(uuid.uuid4())
        
        progress_data = {
            "id": tracker_id,
            "operation_type": operation_type,
            "task_name": task_name,
            "status": "initializing",
            "message": f"Starting {task_name}...",
            "current_step": 0,
            "total_steps": total_steps,
            "percent_complete": 0,
            "start_time": time.time(),
            "last_update_time": time.time(),
            "estimated_completion_time": None,
            "completed": False,
            "success": None,
            "error": None,
            "result": None
        }
        
        self._save_progress(tracker_id, progress_data)
        logger.info(f"Created progress tracker {tracker_id} for {operation_type}: {task_name}")
        
        return tracker_id
    
    def update_progress(self, tracker_id: str, current_step: int = None, 
                       status: str = None, message: str = None, 
                       completed: bool = None, success: bool = None,
                       error: str = None, result: Any = None) -> bool:
        """
        Update the progress of an operation.
        
        Args:
            tracker_id: ID of the progress tracker
            current_step: Current step in the operation
            status: Current status (e.g., 'processing', 'completed')
            message: Human-readable progress message
            completed: Whether the operation is complete
            success: Whether the operation was successful
            error: Error message if operation failed
            result: Result data if operation succeeded
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        progress_data = self._load_progress(tracker_id)
        if not progress_data:
            logger.error(f"Failed to update progress: tracker {tracker_id} not found")
            return False
        
        # Update progress data
        if current_step is not None:
            progress_data["current_step"] = current_step
            total_steps = progress_data["total_steps"]
            progress_data["percent_complete"] = min(100, int((current_step / total_steps) * 100))
            
            # Calculate estimated completion time
            if current_step > 0 and current_step < total_steps:
                elapsed_time = time.time() - progress_data["start_time"]
                time_per_step = elapsed_time / current_step
                remaining_steps = total_steps - current_step
                estimated_remaining_time = time_per_step * remaining_steps
                progress_data["estimated_completion_time"] = time.time() + estimated_remaining_time
        
        if status is not None:
            progress_data["status"] = status
        
        if message is not None:
            progress_data["message"] = message
        
        if completed is not None:
            progress_data["completed"] = completed
            if completed:
                progress_data["percent_complete"] = 100
                progress_data["current_step"] = progress_data["total_steps"]
        
        if success is not None:
            progress_data["success"] = success
        
        if error is not None:
            progress_data["error"] = error
        
        if result is not None:
            progress_data["result"] = result
        
        progress_data["last_update_time"] = time.time()
        
        # Save updated progress
        self._save_progress(tracker_id, progress_data)
        logger.debug(f"Updated progress tracker {tracker_id}: {status or progress_data['status']}")
        
        return True
    
    def get_progress(self, tracker_id: str) -> Optional[Dict]:
        """
        Get the current progress of an operation.
        
        Args:
            tracker_id: ID of the progress tracker
            
        Returns:
            Optional[Dict]: Progress data if found, None otherwise
        """
        return self._load_progress(tracker_id)
    
    def get_all_active_progress(self, operation_type: Optional[str] = None) -> List[Dict]:
        """
        Get all active progress trackers.
        
        Args:
            operation_type: Filter by operation type (e.g., 'llm', 'ocr')
            
        Returns:
            List[Dict]: List of active progress trackers
        """
        active_trackers = []
        
        for file_path in self.progress_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    progress_data = json.load(f)
                
                # Skip completed trackers older than 1 hour
                if progress_data.get("completed", False):
                    if time.time() - progress_data.get("last_update_time", 0) > 3600:
                        continue
                
                # Filter by operation type if specified
                if operation_type and progress_data.get("operation_type") != operation_type:
                    continue
                
                active_trackers.append(progress_data)
            except Exception as e:
                logger.error(f"Error reading progress file {file_path}: {str(e)}")
        
        return active_trackers
    
    def delete_tracker(self, tracker_id: str) -> bool:
        """
        Delete a progress tracker.
        
        Args:
            tracker_id: ID of the progress tracker
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        file_path = self.progress_dir / f"{tracker_id}.json"
        
        with _progress_lock:
            if file_path.exists():
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted progress tracker {tracker_id}")
                    return True
                except Exception as e:
                    logger.error(f"Error deleting progress file {file_path}: {str(e)}")
                    return False
            else:
                logger.warning(f"Progress tracker {tracker_id} not found for deletion")
                return False
    
    def _save_progress(self, tracker_id: str, progress_data: Dict) -> None:
        """Save progress data to file."""
        file_path = self.progress_dir / f"{tracker_id}.json"
        
        with _progress_lock:
            try:
                with open(file_path, "w") as f:
                    json.dump(progress_data, f, indent=2)
            except Exception as e:
                logger.error(f"Error saving progress to {file_path}: {str(e)}")
    
    def _load_progress(self, tracker_id: str) -> Optional[Dict]:
        """Load progress data from file."""
        file_path = self.progress_dir / f"{tracker_id}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading progress from {file_path}: {str(e)}")
            return None
    
    def _cleanup_stale_progress(self, max_age_hours: int = 24) -> None:
        """Clean up stale progress files."""
        max_age_seconds = max_age_hours * 3600
        current_time = time.time()
        
        for file_path in self.progress_dir.glob("*.json"):
            try:
                file_age = current_time - os.path.getmtime(file_path)
                
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    logger.debug(f"Removed stale progress file: {file_path.name}")
                else:
                    # Check if it's a completed tracker older than 1 hour
                    try:
                        with open(file_path, "r") as f:
                            progress_data = json.load(f)
                        
                        if progress_data.get("completed", False):
                            if current_time - progress_data.get("last_update_time", 0) > 3600:
                                os.remove(file_path)
                                logger.debug(f"Removed completed progress file: {file_path.name}")
                    except:
                        # If we can't read the file, consider it stale
                        os.remove(file_path)
                        logger.debug(f"Removed unreadable progress file: {file_path.name}")
            except Exception as e:
                logger.error(f"Error cleaning up progress file {file_path}: {str(e)}")

# Create a singleton instance
progress_service = ProgressService()
