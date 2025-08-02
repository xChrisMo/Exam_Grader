"""
Resource Cleanup Service

This module provides comprehensive resource management and cleanup capabilities,
including automatic temporary file cleanup, memory management, and proper
resource release on service shutdown.
"""

import os
import time
import threading
import tempfile
import shutil
import gc
import psutil
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
import weakref

from utils.logger import logger

class CleanupType(Enum):
    """Types of cleanup operations"""
    TEMPORARY_FILES = "temporary_files"
    CACHE_CLEANUP = "cache_cleanup"
    MEMORY_CLEANUP = "memory_cleanup"
    LOG_ROTATION = "log_rotation"
    EXPIRED_SESSIONS = "expired_sessions"
    ORPHANED_PROCESSES = "orphaned_processes"
    DATABASE_CLEANUP = "database_cleanup"

class CleanupPriority(Enum):
    """Priority levels for cleanup operations"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class CleanupResult:
    """Result of a cleanup operation"""
    cleanup_type: CleanupType
    success: bool
    items_cleaned: int
    bytes_freed: int
    duration_ms: float
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'cleanup_type': self.cleanup_type.value,
            'success': self.success,
            'items_cleaned': self.items_cleaned,
            'bytes_freed': self.bytes_freed,
            'duration_ms': self.duration_ms,
            'error_message': self.error_message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class ResourceTracker:
    """Tracks resource usage and cleanup needs"""
    resource_type: str
    current_count: int = 0
    max_count: int = 1000
    current_size: int = 0  # in bytes
    max_size: int = 100 * 1024 * 1024  # 100MB
    last_cleanup: Optional[datetime] = None
    cleanup_threshold: float = 0.8  # 80% threshold
    
    def needs_cleanup(self) -> bool:
        """Check if cleanup is needed"""
        count_ratio = self.current_count / self.max_count
        size_ratio = self.current_size / self.max_size
        return max(count_ratio, size_ratio) > self.cleanup_threshold

class TemporaryFileManager:
    """Manages temporary files and directories"""
    
    def __init__(self, base_temp_dir: Optional[str] = None):
        self.base_temp_dir = Path(base_temp_dir) if base_temp_dir else Path(tempfile.gettempdir())
        self.tracked_files: Set[Path] = set()
        self.tracked_dirs: Set[Path] = set()
        self.file_age_threshold = timedelta(hours=24)  # 24 hours
        self.size_threshold = 100 * 1024 * 1024  # 100MB
        self._lock = threading.RLock()
    
    def create_temp_file(self, suffix: str = "", prefix: str = "tmp", 
                        directory: Optional[str] = None) -> Path:
        """Create a tracked temporary file"""
        with self._lock:
            if directory:
                temp_dir = Path(directory)
                temp_dir.mkdir(parents=True, exist_ok=True)
            else:
                temp_dir = self.base_temp_dir
            
            # Create temporary file
            fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=str(temp_dir))
            os.close(fd)  # Close the file descriptor
            
            temp_file = Path(temp_path)
            self.tracked_files.add(temp_file)
            
            logger.debug(f"Created temporary file: {temp_file}")
            return temp_file
    
    def create_temp_dir(self, suffix: str = "", prefix: str = "tmp",
                       directory: Optional[str] = None) -> Path:
        """Create a tracked temporary directory"""
        with self._lock:
            if directory:
                parent_dir = Path(directory)
                parent_dir.mkdir(parents=True, exist_ok=True)
            else:
                parent_dir = self.base_temp_dir
            
            temp_dir = Path(tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=str(parent_dir)))
            self.tracked_dirs.add(temp_dir)
            
            logger.debug(f"Created temporary directory: {temp_dir}")
            return temp_dir
    
    def register_temp_path(self, path: Path):
        """Register an existing path for cleanup tracking"""
        with self._lock:
            if path.is_file():
                self.tracked_files.add(path)
            elif path.is_dir():
                self.tracked_dirs.add(path)
            
            logger.debug(f"Registered temporary path: {path}")
    
    def cleanup_temp_files(self, max_age: Optional[timedelta] = None) -> CleanupResult:
        """Clean up temporary files"""
        start_time = time.time()
        max_age = max_age or self.file_age_threshold
        current_time = datetime.now(timezone.utc)
        
        items_cleaned = 0
        bytes_freed = 0
        errors = []
        
        with self._lock:
            # Clean up tracked files
            files_to_remove = set()
            for file_path in self.tracked_files:
                try:
                    if file_path.exists():
                        # Check age
                        file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_age > max_age:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            files_to_remove.add(file_path)
                            items_cleaned += 1
                            bytes_freed += file_size
                            logger.debug(f"Cleaned up temporary file: {file_path}")
                    else:
                        files_to_remove.add(file_path)
                except Exception as e:
                    errors.append(f"Error cleaning file {file_path}: {e}")
                    logger.error(f"Error cleaning temporary file {file_path}: {e}")
            
            self.tracked_files -= files_to_remove
            
            # Clean up tracked directories
            dirs_to_remove = set()
            for dir_path in self.tracked_dirs:
                try:
                    if dir_path.exists():
                        dir_age = current_time - datetime.fromtimestamp(dir_path.stat().st_mtime)
                        if dir_age > max_age or not any(dir_path.iterdir()):
                            dir_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                            shutil.rmtree(dir_path)
                            dirs_to_remove.add(dir_path)
                            items_cleaned += 1
                            bytes_freed += dir_size
                            logger.debug(f"Cleaned up temporary directory: {dir_path}")
                    else:
                        dirs_to_remove.add(dir_path)
                except Exception as e:
                    errors.append(f"Error cleaning directory {dir_path}: {e}")
                    logger.error(f"Error cleaning temporary directory {dir_path}: {e}")
            
            self.tracked_dirs -= dirs_to_remove
        
        duration_ms = (time.time() - start_time) * 1000
        
        return CleanupResult(
            cleanup_type=CleanupType.TEMPORARY_FILES,
            success=len(errors) == 0,
            items_cleaned=items_cleaned,
            bytes_freed=bytes_freed,
            duration_ms=duration_ms,
            error_message="; ".join(errors) if errors else None,
            details={
                'files_tracked': len(self.tracked_files),
                'dirs_tracked': len(self.tracked_dirs),
                'max_age_hours': max_age.total_seconds() / 3600
            }
        )
    
    def cleanup_system_temp(self, pattern: str = "tmp*") -> CleanupResult:
        """Clean up system temporary directory"""
        start_time = time.time()
        items_cleaned = 0
        bytes_freed = 0
        errors = []
        
        try:
            temp_dir = Path(tempfile.gettempdir())
            current_time = datetime.now(timezone.utc)
            
            for item in temp_dir.glob(pattern):
                try:
                    if item.is_file():
                        file_age = current_time - datetime.fromtimestamp(item.stat().st_mtime)
                        if file_age > self.file_age_threshold:
                            file_size = item.stat().st_size
                            item.unlink()
                            items_cleaned += 1
                            bytes_freed += file_size
                    elif item.is_dir():
                        dir_age = current_time - datetime.fromtimestamp(item.stat().st_mtime)
                        if dir_age > self.file_age_threshold:
                            try:
                                dir_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                                shutil.rmtree(item)
                                items_cleaned += 1
                                bytes_freed += dir_size
                            except OSError:
                                # Directory not empty or in use, skip
                                pass
                except Exception as e:
                    errors.append(f"Error cleaning {item}: {e}")
                    
        except Exception as e:
            errors.append(f"Error accessing temp directory: {e}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        return CleanupResult(
            cleanup_type=CleanupType.TEMPORARY_FILES,
            success=len(errors) == 0,
            items_cleaned=items_cleaned,
            bytes_freed=bytes_freed,
            duration_ms=duration_ms,
            error_message="; ".join(errors) if errors else None,
            details={
                'pattern': pattern,
                'temp_dir': str(temp_dir)
            }
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get temporary file manager statistics"""
        with self._lock:
            total_size = 0
            
            # Calculate size of tracked files
            for file_path in self.tracked_files:
                try:
                    if file_path.exists():
                        total_size += file_path.stat().st_size
                except Exception:
                    pass
            
            # Calculate size of tracked directories
            for dir_path in self.tracked_dirs:
                try:
                    if dir_path.exists():
                        total_size += sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                except Exception:
                    pass
            
            return {
                'tracked_files': len(self.tracked_files),
                'tracked_dirs': len(self.tracked_dirs),
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'base_temp_dir': str(self.base_temp_dir),
                'age_threshold_hours': self.file_age_threshold.total_seconds() / 3600
            }

class MemoryCleanupManager:
    """Manages memory cleanup operations"""
    
    def __init__(self):
        self.cleanup_callbacks: List[Callable[[], int]] = []
        self.weak_references: List[weakref.ref] = []
        self.memory_threshold = 0.85  # 85% memory usage threshold
        self.last_cleanup = datetime.now(timezone.utc)
        self.cleanup_interval = timedelta(minutes=5)
    
    def register_cleanup_callback(self, callback: Callable[[], int]):
        """Register a callback that returns bytes freed"""
        self.cleanup_callbacks.append(callback)
        logger.debug("Registered memory cleanup callback")
    
    def register_weak_reference(self, obj: Any):
        """Register an object for weak reference tracking"""
        self.weak_references.append(weakref.ref(obj))
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage information"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            system_memory = psutil.virtual_memory()
            
            return {
                'process_memory_mb': memory_info.rss / (1024 * 1024),
                'process_memory_percent': process.memory_percent(),
                'system_memory_total_mb': system_memory.total / (1024 * 1024),
                'system_memory_available_mb': system_memory.available / (1024 * 1024),
                'system_memory_percent': system_memory.percent,
                'memory_threshold_percent': self.memory_threshold * 100
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {}
    
    def needs_cleanup(self) -> bool:
        """Check if memory cleanup is needed"""
        try:
            memory_info = self.get_memory_usage()
            return memory_info.get('system_memory_percent', 0) > (self.memory_threshold * 100)
        except Exception:
            return False
    
    def cleanup_memory(self) -> CleanupResult:
        """Perform memory cleanup"""
        start_time = time.time()
        total_freed = 0
        callbacks_executed = 0
        errors = []
        
        # Force garbage collection
        try:
            collected = gc.collect()
            logger.debug(f"Garbage collection collected {collected} objects")
        except Exception as e:
            errors.append(f"Garbage collection error: {e}")
        
        # Execute cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                freed = callback()
                total_freed += freed
                callbacks_executed += 1
                logger.debug(f"Cleanup callback freed {freed} bytes")
            except Exception as e:
                errors.append(f"Cleanup callback error: {e}")
                logger.error(f"Error in memory cleanup callback: {e}")
        
        # Clean up dead weak references
        alive_refs = []
        dead_count = 0
        for ref in self.weak_references:
            if ref() is not None:
                alive_refs.append(ref)
            else:
                dead_count += 1
        
        self.weak_references = alive_refs
        
        self.last_cleanup = datetime.now(timezone.utc)
        duration_ms = (time.time() - start_time) * 1000
        
        return CleanupResult(
            cleanup_type=CleanupType.MEMORY_CLEANUP,
            success=len(errors) == 0,
            items_cleaned=callbacks_executed + dead_count,
            bytes_freed=total_freed,
            duration_ms=duration_ms,
            error_message="; ".join(errors) if errors else None,
            details={
                'callbacks_executed': callbacks_executed,
                'dead_references_cleaned': dead_count,
                'gc_objects_collected': collected if 'collected' in locals() else 0
            }
        )

class ResourceCleanupService:
    """Main resource cleanup service"""
    
    def __init__(self):
        self.temp_file_manager = TemporaryFileManager()
        self.memory_cleanup_manager = MemoryCleanupManager()
        self.resource_trackers: Dict[str, ResourceTracker] = {}
        self.cleanup_results: List[CleanupResult] = []
        self.max_results_history = 1000
        
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
        self._cleanup_interval = 300  # 5 minutes
        self._shutdown_callbacks: List[Callable[[], None]] = []
        
        # Setup default resource trackers
        self._setup_default_trackers()
        
        # Register default cleanup callbacks
        self._register_default_callbacks()
    
    def _setup_default_trackers(self):
        """Setup default resource trackers"""
        self.resource_trackers.update({
            'temp_files': ResourceTracker('temp_files', max_count=1000, max_size=500 * 1024 * 1024),
            'cache_entries': ResourceTracker('cache_entries', max_count=10000, max_size=1024 * 1024 * 1024),
            'log_files': ResourceTracker('log_files', max_count=100, max_size=100 * 1024 * 1024),
            'sessions': ResourceTracker('sessions', max_count=1000, max_size=50 * 1024 * 1024)
        })
    
    def _register_default_callbacks(self):
        """Register default cleanup callbacks"""
        # Cache cleanup callback
        def cache_cleanup():
            try:
                from src.services.cache_manager import cache_manager
                cleared = cache_manager.clear_expired()
                return cleared * 1024  # Estimate 1KB per entry
            except ImportError:
                return 0
        
        self.memory_cleanup_manager.register_cleanup_callback(cache_cleanup)
    
    def register_shutdown_callback(self, callback: Callable[[], None]):
        """Register a callback to be called on shutdown"""
        self._shutdown_callbacks.append(callback)
        logger.debug("Registered shutdown callback")
    
    def create_temp_file(self, suffix: str = "", prefix: str = "tmp") -> Path:
        """Create a temporary file"""
        return self.temp_file_manager.create_temp_file(suffix, prefix)
    
    def create_temp_dir(self, suffix: str = "", prefix: str = "tmp") -> Path:
        """Create a temporary directory"""
        return self.temp_file_manager.create_temp_dir(suffix, prefix)
    
    def register_temp_path(self, path: Path):
        """Register a path for cleanup tracking"""
        self.temp_file_manager.register_temp_path(path)
    
    def cleanup_temporary_files(self, max_age: Optional[timedelta] = None) -> CleanupResult:
        """Clean up temporary files"""
        result = self.temp_file_manager.cleanup_temp_files(max_age)
        self._record_cleanup_result(result)
        return result
    
    def cleanup_system_temp(self, pattern: str = "tmp*") -> CleanupResult:
        """Clean up system temporary directory"""
        result = self.temp_file_manager.cleanup_system_temp(pattern)
        self._record_cleanup_result(result)
        return result
    
    def cleanup_memory(self) -> CleanupResult:
        """Clean up memory"""
        result = self.memory_cleanup_manager.cleanup_memory()
        self._record_cleanup_result(result)
        return result
    
    def cleanup_logs(self, log_dir: str = "logs", max_age_days: int = 30) -> CleanupResult:
        """Clean up old log files"""
        start_time = time.time()
        items_cleaned = 0
        bytes_freed = 0
        errors = []
        
        try:
            log_path = Path(log_dir)
            if not log_path.exists():
                return CleanupResult(
                    cleanup_type=CleanupType.LOG_ROTATION,
                    success=True,
                    items_cleaned=0,
                    bytes_freed=0,
                    duration_ms=0,
                    details={'log_dir': str(log_path), 'status': 'directory_not_found'}
                )
            
            max_age = timedelta(days=max_age_days)
            current_time = datetime.now(timezone.utc)
            
            for log_file in log_path.rglob("*.log*"):
                try:
                    if log_file.is_file():
                        file_age = current_time - datetime.fromtimestamp(log_file.stat().st_mtime)
                        if file_age > max_age:
                            file_size = log_file.stat().st_size
                            log_file.unlink()
                            items_cleaned += 1
                            bytes_freed += file_size
                            logger.debug(f"Cleaned up old log file: {log_file}")
                except Exception as e:
                    errors.append(f"Error cleaning log file {log_file}: {e}")
                    
        except Exception as e:
            errors.append(f"Error accessing log directory: {e}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        result = CleanupResult(
            cleanup_type=CleanupType.LOG_ROTATION,
            success=len(errors) == 0,
            items_cleaned=items_cleaned,
            bytes_freed=bytes_freed,
            duration_ms=duration_ms,
            error_message="; ".join(errors) if errors else None,
            details={
                'log_dir': log_dir,
                'max_age_days': max_age_days
            }
        )
        
        self._record_cleanup_result(result)
        return result
    
    def perform_full_cleanup(self) -> List[CleanupResult]:
        """Perform comprehensive cleanup"""
        results = []
        
        logger.info("Starting full system cleanup")
        
        # Clean temporary files
        results.append(self.cleanup_temporary_files())
        
        # Clean system temp
        results.append(self.cleanup_system_temp())
        
        if self.memory_cleanup_manager.needs_cleanup():
            results.append(self.cleanup_memory())
        
        # Clean logs
        results.append(self.cleanup_logs())
        
        try:
            from src.services.cache_manager import cache_manager
            cleared = cache_manager.clear_expired()
            if cleared > 0:
                cache_result = CleanupResult(
                    cleanup_type=CleanupType.CACHE_CLEANUP,
                    success=True,
                    items_cleaned=cleared,
                    bytes_freed=cleared * 1024,  # Estimate
                    duration_ms=0,
                    details={'cache_entries_cleared': cleared}
                )
                results.append(cache_result)
                self._record_cleanup_result(cache_result)
        except ImportError:
            pass
        
        total_items = sum(r.items_cleaned for r in results)
        total_bytes = sum(r.bytes_freed for r in results)
        
        logger.info(f"Full cleanup completed: {total_items} items cleaned, "
                   f"{total_bytes / (1024 * 1024):.2f} MB freed")
        
        return results
    
    def start_background_cleanup(self):
        """Start background cleanup thread"""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return
        
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info("Started background resource cleanup")
    
    def stop_background_cleanup(self):
        """Stop background cleanup thread"""
        self._running = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        logger.info("Stopped background resource cleanup")
    
    def _cleanup_worker(self):
        """Background cleanup worker"""
        while self._running:
            try:
                needs_cleanup = any(tracker.needs_cleanup() for tracker in self.resource_trackers.values())
                
                if needs_cleanup or self.memory_cleanup_manager.needs_cleanup():
                    logger.info("Background cleanup triggered")
                    self.perform_full_cleanup()
                
                time.sleep(self._cleanup_interval)
                
            except Exception as e:
                logger.error(f"Error in background cleanup: {e}")
                time.sleep(60)  # Wait longer on error
    
    def shutdown(self):
        """Shutdown the cleanup service and perform final cleanup"""
        logger.info("Shutting down resource cleanup service")
        
        # Stop background cleanup
        self.stop_background_cleanup()
        
        # Execute shutdown callbacks
        for callback in self._shutdown_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in shutdown callback: {e}")
        
        # Perform final cleanup
        final_results = self.perform_full_cleanup()
        
        logger.info("Resource cleanup service shutdown complete")
        return final_results
    
    def _record_cleanup_result(self, result: CleanupResult):
        """Record cleanup result"""
        self.cleanup_results.append(result)
        
        # Limit history size
        if len(self.cleanup_results) > self.max_results_history:
            self.cleanup_results = self.cleanup_results[-self.max_results_history:]
    
    def get_cleanup_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics"""
        if not self.cleanup_results:
            return {
                'total_cleanups': 0,
                'total_items_cleaned': 0,
                'total_bytes_freed': 0,
                'success_rate': 0.0,
                'by_type': {},
                'recent_results': []
            }
        
        total_cleanups = len(self.cleanup_results)
        successful_cleanups = sum(1 for r in self.cleanup_results if r.success)
        total_items = sum(r.items_cleaned for r in self.cleanup_results)
        total_bytes = sum(r.bytes_freed for r in self.cleanup_results)
        
        # Group by cleanup type
        by_type = {}
        for result in self.cleanup_results:
            cleanup_type = result.cleanup_type.value
            if cleanup_type not in by_type:
                by_type[cleanup_type] = {
                    'count': 0,
                    'items_cleaned': 0,
                    'bytes_freed': 0,
                    'success_count': 0
                }
            
            by_type[cleanup_type]['count'] += 1
            by_type[cleanup_type]['items_cleaned'] += result.items_cleaned
            by_type[cleanup_type]['bytes_freed'] += result.bytes_freed
            if result.success:
                by_type[cleanup_type]['success_count'] += 1
        
        for type_stats in by_type.values():
            type_stats['success_rate'] = type_stats['success_count'] / type_stats['count']
        
        return {
            'total_cleanups': total_cleanups,
            'successful_cleanups': successful_cleanups,
            'success_rate': successful_cleanups / total_cleanups,
            'total_items_cleaned': total_items,
            'total_bytes_freed': total_bytes,
            'total_mb_freed': total_bytes / (1024 * 1024),
            'by_type': by_type,
            'recent_results': [r.to_dict() for r in self.cleanup_results[-10:]],
            'temp_file_stats': self.temp_file_manager.get_stats(),
            'memory_stats': self.memory_cleanup_manager.get_memory_usage(),
            'background_cleanup_active': self._running
        }

# Global instance
resource_cleanup_service = ResourceCleanupService()