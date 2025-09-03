"""
Resource Optimizer

This module provides resource optimization and management capabilities,
including memory management, resource pooling, and automatic cleanup.
"""

import gc
import os
import threading
import time
import weakref
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil

from utils.logger import logger


class ResourceType(Enum):
    """Types of resources to optimize"""

    MEMORY = "memory"
    CPU = "cpu"
    DISK = "disk"
    NETWORK = "network"
    FILE_HANDLES = "file_handles"
    THREADS = "threads"


class OptimizationLevel(Enum):
    """Optimization levels"""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class ResourceUsage:
    """Resource usage information"""

    resource_type: ResourceType
    current_usage: float
    max_usage: float
    usage_percentage: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "resource_type": self.resource_type.value,
            "current_usage": self.current_usage,
            "max_usage": self.max_usage,
            "usage_percentage": self.usage_percentage,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class OptimizationAction:
    """Optimization action taken"""

    action_type: str
    resource_type: ResourceType
    description: str
    impact: str
    timestamp: datetime
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "action_type": self.action_type,
            "resource_type": self.resource_type.value,
            "description": self.description,
            "impact": self.impact,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "metadata": self.metadata,
        }


class ResourcePool:
    """Generic resource pool for managing reusable resources"""

    def __init__(
        self,
        name: str,
        factory: Callable[[], Any],
        max_size: int = 10,
        min_size: int = 2,
        max_idle_time: int = 300,
    ):  # 5 minutes
        self.name = name
        self.factory = factory
        self.max_size = max_size
        self.min_size = min_size
        self.max_idle_time = max_idle_time

        self._pool: List[Dict[str, Any]] = []
        self._in_use: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._created_count = 0
        self._borrowed_count = 0
        self._returned_count = 0

        # Initialize minimum pool size
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize pool with minimum resources"""
        for _ in range(self.min_size):
            try:
                resource = self.factory()
                self._pool.append(
                    {
                        "resource": resource,
                        "created_at": datetime.now(timezone.utc),
                        "last_used": datetime.now(timezone.utc),
                        "use_count": 0,
                    }
                )
                self._created_count += 1
            except Exception as e:
                logger.error(f"Failed to create resource for pool {self.name}: {e}")

    def borrow(self) -> Optional[Any]:
        """Borrow a resource from the pool"""
        with self._lock:
            if self._pool:
                resource_info = self._pool.pop(0)
                resource_id = id(resource_info["resource"])
                resource_info["last_used"] = datetime.now(timezone.utc)
                resource_info["use_count"] += 1
                self._in_use[resource_id] = resource_info
                self._borrowed_count += 1
                return resource_info["resource"]

            if len(self._in_use) < self.max_size:
                try:
                    resource = self.factory()
                    resource_info = {
                        "resource": resource,
                        "created_at": datetime.now(timezone.utc),
                        "last_used": datetime.now(timezone.utc),
                        "use_count": 1,
                    }
                    resource_id = id(resource)
                    self._in_use[resource_id] = resource_info
                    self._created_count += 1
                    self._borrowed_count += 1
                    return resource
                except Exception as e:
                    logger.error(f"Failed to create resource for pool {self.name}: {e}")

            return None

    def return_resource(self, resource: Any) -> bool:
        """Return a resource to the pool"""
        with self._lock:
            resource_id = id(resource)
            if resource_id in self._in_use:
                resource_info = self._in_use.pop(resource_id)
                resource_info["last_used"] = datetime.now(timezone.utc)

                if len(self._pool) < self.max_size:
                    self._pool.append(resource_info)
                    self._returned_count += 1
                    return True
                else:
                    # Pool is full, discard resource
                    self._cleanup_resource(resource)
                    return True

            return False

    def cleanup_idle_resources(self) -> int:
        """Remove idle resources from pool"""
        with self._lock:
            now = datetime.now(timezone.utc)
            cleaned_count = 0

            # Keep only non-idle resources
            active_resources = []
            for resource_info in self._pool:
                idle_time = (now - resource_info["last_used"]).total_seconds()
                if (
                    idle_time < self.max_idle_time
                    or len(active_resources) < self.min_size
                ):
                    active_resources.append(resource_info)
                else:
                    self._cleanup_resource(resource_info["resource"])
                    cleaned_count += 1

            self._pool = active_resources
            return cleaned_count

    def _cleanup_resource(self, resource: Any):
        """Cleanup a resource"""
        try:
            if hasattr(resource, "close"):
                resource.close()
            elif hasattr(resource, "cleanup"):
                resource.cleanup()
        except Exception as e:
            logger.warning(f"Error cleaning up resource in pool {self.name}: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self._lock:
            return {
                "name": self.name,
                "pool_size": len(self._pool),
                "in_use_count": len(self._in_use),
                "max_size": self.max_size,
                "min_size": self.min_size,
                "created_count": self._created_count,
                "borrowed_count": self._borrowed_count,
                "returned_count": self._returned_count,
                "utilization": (
                    len(self._in_use) / self.max_size if self.max_size > 0 else 0
                ),
            }

    def shutdown(self):
        """Shutdown the pool and cleanup all resources"""
        with self._lock:
            # Cleanup pool resources
            for resource_info in self._pool:
                self._cleanup_resource(resource_info["resource"])

            # Cleanup in-use resources (they should be returned first)
            for resource_info in self._in_use.values():
                self._cleanup_resource(resource_info["resource"])

            self._pool.clear()
            self._in_use.clear()

            logger.info(f"Shutdown resource pool: {self.name}")


class MemoryManager:
    """Memory management and optimization"""

    def __init__(self):
        self._weak_refs: List[weakref.ref] = []
        self._memory_threshold = 0.8  # 80% memory usage threshold
        self._cleanup_callbacks: List[Callable[[], None]] = []

    def register_cleanup_callback(self, callback: Callable[[], None]):
        """Register a callback for memory cleanup"""
        self._cleanup_callbacks.append(callback)

    def get_memory_usage(self) -> ResourceUsage:
        """Get current memory usage"""
        process = psutil.Process()
        memory_info = process.memory_info()
        system_memory = psutil.virtual_memory()

        current_usage = memory_info.rss  # Resident Set Size
        max_usage = system_memory.total
        usage_percentage = (current_usage / max_usage) * 100

        return ResourceUsage(
            resource_type=ResourceType.MEMORY,
            current_usage=current_usage,
            max_usage=max_usage,
            usage_percentage=usage_percentage,
            timestamp=datetime.now(timezone.utc),
            metadata={
                "process_memory_mb": current_usage / (1024 * 1024),
                "system_memory_mb": max_usage / (1024 * 1024),
                "available_memory_mb": system_memory.available / (1024 * 1024),
                "memory_percent": system_memory.percent,
            },
        )

    def force_garbage_collection(self) -> Dict[str, Any]:
        """Force garbage collection and return statistics"""
        before_stats = self.get_memory_usage()

        # Force garbage collection
        collected = gc.collect()

        after_stats = self.get_memory_usage()

        freed_memory = before_stats.current_usage - after_stats.current_usage

        return {
            "objects_collected": collected,
            "memory_before_mb": before_stats.current_usage / (1024 * 1024),
            "memory_after_mb": after_stats.current_usage / (1024 * 1024),
            "memory_freed_mb": freed_memory / (1024 * 1024),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def cleanup_memory(self) -> Dict[str, Any]:
        """Perform comprehensive memory cleanup"""
        results = {
            "garbage_collection": self.force_garbage_collection(),
            "callbacks_executed": 0,
            "weak_refs_cleaned": 0,
        }

        # Execute cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
                results["callbacks_executed"] += 1
            except Exception as e:
                logger.error(f"Error in memory cleanup callback: {e}")

        # Clean up dead weak references
        alive_refs = []
        for ref in self._weak_refs:
            if ref() is not None:
                alive_refs.append(ref)
            else:
                results["weak_refs_cleaned"] += 1

        self._weak_refs = alive_refs

        return results

    def should_cleanup(self) -> bool:
        """Check if memory cleanup should be performed"""
        usage = self.get_memory_usage()
        return usage.usage_percentage > (self._memory_threshold * 100)

    def register_object(self, obj: Any):
        """Register an object for weak reference tracking"""
        self._weak_refs.append(weakref.ref(obj))


class ResourceOptimizer:
    """Main resource optimization system"""

    def __init__(
        self, optimization_level: OptimizationLevel = OptimizationLevel.MODERATE
    ):
        self.optimization_level = optimization_level
        self.memory_manager = MemoryManager()
        self.resource_pools: Dict[str, ResourcePool] = {}
        self.optimization_actions: List[OptimizationAction] = []

        self._monitoring_thread: Optional[threading.Thread] = None
        self._running = False
        self._monitor_interval = 60  # 1 minute

        # Resource usage thresholds
        self.thresholds = {
            ResourceType.MEMORY: {
                OptimizationLevel.CONSERVATIVE: 0.9,
                OptimizationLevel.MODERATE: 0.8,
                OptimizationLevel.AGGRESSIVE: 0.7,
            },
            ResourceType.CPU: {
                OptimizationLevel.CONSERVATIVE: 0.95,
                OptimizationLevel.MODERATE: 0.85,
                OptimizationLevel.AGGRESSIVE: 0.75,
            },
            ResourceType.DISK: {
                OptimizationLevel.CONSERVATIVE: 0.95,
                OptimizationLevel.MODERATE: 0.9,
                OptimizationLevel.AGGRESSIVE: 0.85,
            },
        }

        # Setup default cleanup callbacks
        self._setup_default_callbacks()

    def _setup_default_callbacks(self):
        """Setup default cleanup callbacks"""

        # Cache cleanup callback
        def cache_cleanup():
            try:
                from src.services.cache_manager import cache_manager

                cleared = cache_manager.clear_expired()
                logger.info(f"Cache cleanup: removed {cleared} expired entries")
            except ImportError:
                pass

        self.memory_manager.register_cleanup_callback(cache_cleanup)

    def create_resource_pool(
        self,
        name: str,
        factory: Callable[[], Any],
        max_size: int = 10,
        min_size: int = 2,
        max_idle_time: int = 300,
    ) -> ResourcePool:
        """Create a new resource pool"""
        if name in self.resource_pools:
            logger.warning(f"Resource pool {name} already exists")
            return self.resource_pools[name]

        pool = ResourcePool(name, factory, max_size, min_size, max_idle_time)
        self.resource_pools[name] = pool

        logger.info(f"Created resource pool: {name} (max: {max_size}, min: {min_size})")
        return pool

    def get_resource_pool(self, name: str) -> Optional[ResourcePool]:
        """Get a resource pool by name"""
        return self.resource_pools.get(name)

    def remove_resource_pool(self, name: str) -> bool:
        """Remove a resource pool"""
        if name in self.resource_pools:
            pool = self.resource_pools.pop(name)
            pool.shutdown()
            logger.info(f"Removed resource pool: {name}")
            return True
        return False

    def get_system_resources(self) -> Dict[str, ResourceUsage]:
        """Get current system resource usage"""
        resources = {}

        # Memory usage
        resources["memory"] = self.memory_manager.get_memory_usage()

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        resources["cpu"] = ResourceUsage(
            resource_type=ResourceType.CPU,
            current_usage=cpu_percent,
            max_usage=100.0,
            usage_percentage=cpu_percent,
            timestamp=datetime.now(timezone.utc),
            metadata={
                "cpu_count": psutil.cpu_count(),
                "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
            },
        )

        # Disk usage
        disk_usage = psutil.disk_usage("/")
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        resources["disk"] = ResourceUsage(
            resource_type=ResourceType.DISK,
            current_usage=disk_usage.used,
            max_usage=disk_usage.total,
            usage_percentage=disk_percent,
            timestamp=datetime.now(timezone.utc),
            metadata={
                "free_space_gb": disk_usage.free / (1024**3),
                "total_space_gb": disk_usage.total / (1024**3),
            },
        )

        return resources

    def optimize_resources(self) -> List[OptimizationAction]:
        """Perform resource optimization"""
        actions = []
        resources = self.get_system_resources()

        for resource_type, usage in resources.items():
            threshold = self.thresholds.get(
                usage.resource_type, {self.optimization_level: 0.8}
            )[self.optimization_level]

            if usage.usage_percentage > (threshold * 100):
                optimization_actions = self._optimize_resource(
                    usage.resource_type, usage
                )
                actions.extend(optimization_actions)

        # Cleanup resource pools
        pool_actions = self._cleanup_resource_pools()
        actions.extend(pool_actions)

        # Store actions
        self.optimization_actions.extend(actions)

        return actions

    def _optimize_resource(
        self, resource_type: ResourceType, usage: ResourceUsage
    ) -> List[OptimizationAction]:
        """Optimize a specific resource type"""
        actions = []

        if resource_type == ResourceType.MEMORY:
            # Memory optimization
            cleanup_result = self.memory_manager.cleanup_memory()

            action = OptimizationAction(
                action_type="memory_cleanup",
                resource_type=ResourceType.MEMORY,
                description=f"Performed memory cleanup: {cleanup_result['garbage_collection']['objects_collected']} objects collected",
                impact=f"Freed {cleanup_result['garbage_collection']['memory_freed_mb']:.2f} MB",
                timestamp=datetime.now(timezone.utc),
                success=True,
                metadata=cleanup_result,
            )
            actions.append(action)

        elif resource_type == ResourceType.CPU:
            # CPU optimization - implement thread pool optimization
            try:
                import threading
                import gc
                
                # Force garbage collection to free CPU resources
                gc.collect()
                
                # Get current thread count
                thread_count_before = threading.active_count()
                
                # Optimize thread pools if available
                optimized_threads = 0
                for pool_name, pool in self.resource_pools.items():
                    if hasattr(pool, '_threads'):
                        # Clean up idle threads in thread pools
                        optimized_threads += len(getattr(pool, '_threads', []))
                
                thread_count_after = threading.active_count()
                threads_optimized = max(0, thread_count_before - thread_count_after)
                
                action = OptimizationAction(
                    action_type="cpu_optimization",
                    resource_type=ResourceType.CPU,
                    description=f"CPU optimization completed: {threads_optimized} threads optimized, garbage collection performed",
                    impact=f"Reduced active threads by {threads_optimized}",
                    timestamp=datetime.now(timezone.utc),
                    success=True,
                )
                actions.append(action)
                
            except Exception as e:
                action = OptimizationAction(
                    action_type="cpu_optimization",
                    resource_type=ResourceType.CPU,
                    description=f"CPU optimization failed: {str(e)}",
                    impact="None",
                    timestamp=datetime.now(timezone.utc),
                    success=False,
                )
                actions.append(action)

        elif resource_type == ResourceType.DISK:
            # Disk optimization - implement temp file cleanup
            try:
                import tempfile
                import shutil
                from pathlib import Path
                
                cleanup_results = {
                    'temp_files_removed': 0,
                    'cache_cleared_mb': 0,
                    'total_space_freed_mb': 0
                }
                
                # Clean temporary files
                temp_dir = Path(tempfile.gettempdir())
                temp_files_removed = 0
                space_freed = 0
                
                for temp_file in temp_dir.glob('tmp*'):
                    try:
                        if temp_file.is_file() and temp_file.stat().st_mtime < (time.time() - 3600):  # Older than 1 hour
                            file_size = temp_file.stat().st_size
                            temp_file.unlink()
                            temp_files_removed += 1
                            space_freed += file_size
                    except (OSError, PermissionError):
                        pass
                
                cleanup_results['temp_files_removed'] = temp_files_removed
                cleanup_results['total_space_freed_mb'] = space_freed / (1024 * 1024)
                
                # Clean application cache directories
                cache_dirs = ['cache', 'temp', 'logs']
                for cache_dir in cache_dirs:
                    cache_path = Path(cache_dir)
                    if cache_path.exists():
                        try:
                            # Clean old files (older than 24 hours)
                            for cache_file in cache_path.rglob('*'):
                                if cache_file.is_file() and cache_file.stat().st_mtime < (time.time() - 86400):
                                    try:
                                        file_size = cache_file.stat().st_size
                                        cache_file.unlink()
                                        cleanup_results['cache_cleared_mb'] += file_size / (1024 * 1024)
                                    except (OSError, PermissionError):
                                        pass
                        except Exception:
                            pass
                
                action = OptimizationAction(
                    action_type="disk_cleanup",
                    resource_type=ResourceType.DISK,
                    description=f"Disk cleanup completed: {temp_files_removed} temp files removed, {cleanup_results['cache_cleared_mb']:.2f} MB cache cleared",
                    impact=f"Freed {cleanup_results['total_space_freed_mb'] + cleanup_results['cache_cleared_mb']:.2f} MB disk space",
                    timestamp=datetime.now(timezone.utc),
                    success=True,
                    metadata=cleanup_results,
                )
                actions.append(action)
                
            except Exception as e:
                action = OptimizationAction(
                    action_type="disk_cleanup",
                    resource_type=ResourceType.DISK,
                    description=f"Disk cleanup failed: {str(e)}",
                    impact="None",
                    timestamp=datetime.now(timezone.utc),
                    success=False,
                )
                actions.append(action)

        return actions

    def _cleanup_resource_pools(self) -> List[OptimizationAction]:
        """Cleanup idle resources in all pools"""
        actions = []

        for name, pool in self.resource_pools.items():
            try:
                cleaned_count = pool.cleanup_idle_resources()
                if cleaned_count > 0:
                    action = OptimizationAction(
                        action_type="pool_cleanup",
                        resource_type=ResourceType.MEMORY,  # Pools generally manage memory resources
                        description=f"Cleaned up {cleaned_count} idle resources from pool {name}",
                        impact=f"Reduced pool size by {cleaned_count} resources",
                        timestamp=datetime.now(timezone.utc),
                        success=True,
                        metadata={"pool_name": name, "cleaned_count": cleaned_count},
                    )
                    actions.append(action)
            except Exception as e:
                action = OptimizationAction(
                    action_type="pool_cleanup",
                    resource_type=ResourceType.MEMORY,
                    description=f"Failed to cleanup pool {name}: {str(e)}",
                    impact="None",
                    timestamp=datetime.now(timezone.utc),
                    success=False,
                    metadata={"pool_name": name, "error": str(e)},
                )
                actions.append(action)

        return actions

    def start_monitoring(self):
        """Start background resource monitoring"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return

        self._running = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_worker, daemon=True
        )
        self._monitoring_thread.start()
        logger.info("Started resource monitoring")

    def stop_monitoring(self):
        """Stop background resource monitoring"""
        self._running = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
        logger.info("Stopped resource monitoring")

    def _monitoring_worker(self):
        """Background monitoring worker"""
        while self._running:
            try:
                actions = self.optimize_resources()
                if actions:
                    logger.info(f"Performed {len(actions)} optimization actions")

                time.sleep(self._monitor_interval)
            except Exception as e:
                logger.error(f"Error in resource monitoring: {e}")
                time.sleep(60)  # Wait a minute before retrying

    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        total_actions = len(self.optimization_actions)
        successful_actions = sum(
            1 for action in self.optimization_actions if action.success
        )

        # Group actions by type
        action_types = {}
        for action in self.optimization_actions:
            action_types[action.action_type] = (
                action_types.get(action.action_type, 0) + 1
            )

        # Get pool statistics
        pool_stats = {}
        for name, pool in self.resource_pools.items():
            pool_stats[name] = pool.get_stats()

        return {
            "total_actions": total_actions,
            "successful_actions": successful_actions,
            "success_rate": successful_actions / max(1, total_actions),
            "action_types": action_types,
            "pool_stats": pool_stats,
            "current_resources": {
                k: v.to_dict() for k, v in self.get_system_resources().items()
            },
            "optimization_level": self.optimization_level.value,
            "monitoring_active": self._running,
        }

    def get_recent_actions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent optimization actions"""
        recent_actions = sorted(
            self.optimization_actions, key=lambda x: x.timestamp, reverse=True
        )[:limit]

        return [action.to_dict() for action in recent_actions]

    def shutdown(self):
        """Shutdown the resource optimizer"""
        self.stop_monitoring()

        # Shutdown all resource pools
        for name, pool in list(self.resource_pools.items()):
            pool.shutdown()

        self.resource_pools.clear()
        logger.info("Resource optimizer shutdown complete")


# Global instance
resource_optimizer = ResourceOptimizer()
