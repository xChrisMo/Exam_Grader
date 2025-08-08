"""
Performance Optimization and Caching Service

Provides caching, query optimization, background job processing,
and memory management for training processes.
"""

import json
import time
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from functools import wraps
from pathlib import Path
import pickle
import gzip
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import queue
import weakref
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict

from utils.logger import logger


class CacheLevel(Enum):
    """Cache levels for different types of data"""
    MEMORY = "memory"
    DISK = "disk"
    HYBRID = "hybrid"


class CacheStrategy(Enum):
    """Cache eviction strategies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    FIFO = "fifo"  # First In First Out


@dataclass
class CacheConfig:
    """Cache configuration"""
    max_memory_size: int = 100 * 1024 * 1024  # 100MB
    max_disk_size: int = 1024 * 1024 * 1024   # 1GB
    default_ttl: int = 3600  # 1 hour
    strategy: CacheStrategy = CacheStrategy.LRU
    compression: bool = True
    persistence: bool = True


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    cache_hits: int = 0
    cache_misses: int = 0
    cache_size: int = 0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    active_threads: int = 0
    queue_size: int = 0
    average_response_time: float = 0.0


class MemoryCache:
    """In-memory cache with LRU eviction"""
    
    def __init__(self, max_size: int, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_times = {}
        self.creation_times = {}
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self.lock:
            if key not in self.cache:
                return None
            
            # Check TTL
            if time.time() - self.creation_times[key] > self.ttl:
                self._remove(key)
                return None
            
            # Update access time
            self.access_times[key] = time.time()
            return self.cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Set item in cache"""
        with self.lock:
            current_time = time.time()
            
            # Remove existing item if present
            if key in self.cache:
                self._remove(key)
            
            # Check if we need to evict items
            while len(self.cache) >= self.max_size:
                self._evict_lru()
            
            # Add new item
            self.cache[key] = value
            self.access_times[key] = current_time
            self.creation_times[key] = current_time
    
    def remove(self, key: str) -> bool:
        """Remove item from cache"""
        with self.lock:
            return self._remove(key)
    
    def clear(self) -> None:
        """Clear all cache items"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.creation_times.clear()
    
    def size(self) -> int:
        """Get cache size"""
        return len(self.cache)
    
    def _remove(self, key: str) -> bool:
        """Internal remove method"""
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
            del self.creation_times[key]
            return True
        return False
    
    def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if not self.cache:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove(lru_key)


class DiskCache:
    """Disk-based cache with compression"""
    
    def __init__(self, cache_dir: str, max_size: int, compression: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self.compression = compression
        self.lock = threading.RLock()
        
        # Index file for metadata
        self.index_file = self.cache_dir / "cache_index.json"
        self.index = self._load_index()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from disk cache"""
        with self.lock:
            if key not in self.index:
                return None
            
            entry = self.index[key]
            file_path = self.cache_dir / entry['filename']
            
            if not file_path.exists():
                # Clean up stale index entry
                del self.index[key]
                self._save_index()
                return None
            
            try:
                # Read and deserialize data
                if self.compression:
                    with gzip.open(file_path, 'rb') as f:
                        data = pickle.load(f)
                else:
                    with open(file_path, 'rb') as f:
                        data = pickle.load(f)
                
                # Update access time
                entry['last_access'] = time.time()
                self._save_index()
                
                return data
                
            except Exception as e:
                logger.error(f"Error reading cache file {file_path}: {e}")
                self._remove_file(key)
                return None
    
    def set(self, key: str, value: Any) -> None:
        """Set item in disk cache"""
        with self.lock:
            # Remove existing item if present
            if key in self.index:
                self._remove_file(key)
            
            # Check disk space and evict if necessary
            self._ensure_space()
            
            # Generate filename
            filename = f"cache_{hashlib.md5(key.encode()).hexdigest()}.pkl"
            if self.compression:
                filename += ".gz"
            
            file_path = self.cache_dir / filename
            
            try:
                # Write data to disk
                if self.compression:
                    with gzip.open(file_path, 'wb') as f:
                        pickle.dump(value, f)
                else:
                    with open(file_path, 'wb') as f:
                        pickle.dump(value, f)
                
                # Update index
                current_time = time.time()
                self.index[key] = {
                    'filename': filename,
                    'size': file_path.stat().st_size,
                    'created': current_time,
                    'last_access': current_time
                }
                self._save_index()
                
            except Exception as e:
                logger.error(f"Error writing cache file {file_path}: {e}")
                if file_path.exists():
                    file_path.unlink()
    
    def remove(self, key: str) -> bool:
        """Remove item from disk cache"""
        with self.lock:
            return self._remove_file(key)
    
    def clear(self) -> None:
        """Clear all cache items"""
        with self.lock:
            for key in list(self.index.keys()):
                self._remove_file(key)
    
    def size(self) -> int:
        """Get cache size in bytes"""
        return sum(entry['size'] for entry in self.index.values())
    
    def _load_index(self) -> Dict:
        """Load cache index from disk"""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cache index: {e}")
        
        return {}
    
    def _save_index(self) -> None:
        """Save cache index to disk"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache index: {e}")
    
    def _remove_file(self, key: str) -> bool:
        """Remove cache file and index entry"""
        if key not in self.index:
            return False
        
        entry = self.index[key]
        file_path = self.cache_dir / entry['filename']
        
        try:
            if file_path.exists():
                file_path.unlink()
            del self.index[key]
            self._save_index()
            return True
        except Exception as e:
            logger.error(f"Error removing cache file {file_path}: {e}")
            return False
    
    def _ensure_space(self) -> None:
        """Ensure there's enough disk space by evicting old items"""
        current_size = self.size()
        
        while current_size > self.max_size * 0.8:  # Keep 20% buffer
            if not self.index:
                break
            
            # Find oldest accessed item
            oldest_key = min(self.index.keys(), 
                           key=lambda k: self.index[k]['last_access'])
            
            old_size = self.index[oldest_key]['size']
            self._remove_file(oldest_key)
            current_size -= old_size


class BackgroundJobProcessor:
    """Background job processing for long-running tasks"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.thread_executor = ThreadPoolExecutor(max_workers=max_workers, 
                                                 thread_name_prefix="bg_job")
        self.process_executor = ProcessPoolExecutor(max_workers=max_workers//2)
        self.job_queue = queue.Queue()
        self.active_jobs = {}
        self.completed_jobs = {}
        self.job_counter = 0
        self.lock = threading.Lock()
    
    def submit_job(self, func: Callable, args: tuple = (), kwargs: Dict = None, 
                   job_type: str = "thread", priority: int = 0) -> str:
        """
        Submit a background job
        
        Args:
            func: Function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            job_type: "thread" or "process"
            priority: Job priority (higher = more priority)
            
        Returns:
            Job ID for tracking
        """
        if kwargs is None:
            kwargs = {}
        
        with self.lock:
            self.job_counter += 1
            job_id = f"job_{self.job_counter}_{int(time.time())}"
        
        job_info = {
            'id': job_id,
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'job_type': job_type,
            'priority': priority,
            'submitted_at': time.time(),
            'status': 'queued'
        }
        
        # Submit to appropriate executor
        if job_type == "process":
            future = self.process_executor.submit(func, *args, **kwargs)
        else:
            future = self.thread_executor.submit(func, *args, **kwargs)
        
        job_info['future'] = future
        job_info['status'] = 'running'
        
        with self.lock:
            self.active_jobs[job_id] = job_info
        
        # Add completion callback
        future.add_done_callback(lambda f: self._job_completed(job_id, f))
        
        logger.info(f"Background job submitted: {job_id} ({job_type})")
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a background job"""
        with self.lock:
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id].copy()
                job.pop('future', None)  # Remove future object
                job.pop('func', None)    # Remove function object
                return job
            
            if job_id in self.completed_jobs:
                return self.completed_jobs[job_id].copy()
        
        return None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a background job"""
        with self.lock:
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                if job['future'].cancel():
                    job['status'] = 'cancelled'
                    self.completed_jobs[job_id] = job
                    del self.active_jobs[job_id]
                    return True
        
        return False
    
    def get_queue_stats(self) -> Dict:
        """Get background job queue statistics"""
        with self.lock:
            return {
                'active_jobs': len(self.active_jobs),
                'completed_jobs': len(self.completed_jobs),
                'thread_pool_size': self.thread_executor._max_workers,
                'process_pool_size': self.process_executor._max_workers
            }
    
    def _job_completed(self, job_id: str, future):
        """Handle job completion"""
        with self.lock:
            if job_id not in self.active_jobs:
                return
            
            job = self.active_jobs[job_id]
            job['completed_at'] = time.time()
            job['duration'] = job['completed_at'] - job['submitted_at']
            
            try:
                job['result'] = future.result()
                job['status'] = 'completed'
            except Exception as e:
                job['error'] = str(e)
                job['status'] = 'failed'
                logger.error(f"Background job {job_id} failed: {e}")
            
            # Move to completed jobs
            job.pop('future', None)
            job.pop('func', None)
            self.completed_jobs[job_id] = job
            del self.active_jobs[job_id]
            
            logger.info(f"Background job completed: {job_id} ({job['status']})")


class PerformanceOptimizer:
    """
    Main performance optimization service
    """
    
    def __init__(self, cache_config: Optional[CacheConfig] = None):
        """Initialize performance optimizer"""
        self.config = cache_config or CacheConfig()
        
        # Initialize caches
        self.memory_cache = MemoryCache(
            max_size=1000,  # Max items, not bytes
            ttl=self.config.default_ttl
        )
        
        self.disk_cache = DiskCache(
            cache_dir="cache/training",
            max_size=self.config.max_disk_size,
            compression=self.config.compression
        )
        
        # Background job processor
        self.job_processor = BackgroundJobProcessor()
        
        # Performance metrics
        self.metrics = PerformanceMetrics()
        self.metrics_lock = threading.Lock()
        
        # Query optimization
        self.query_cache = {}
        self.query_stats = defaultdict(list)
    
    def cached(self, 
               ttl: Optional[int] = None,
               cache_level: CacheLevel = CacheLevel.HYBRID,
               key_func: Optional[Callable] = None):
        """
        Decorator for caching function results
        
        Args:
            ttl: Time to live in seconds
            cache_level: Cache level to use
            key_func: Function to generate cache key
            
        Returns:
            Decorated function with caching
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self._generate_cache_key(func.__name__, args, kwargs)
                
                # Try to get from cache
                result = self._get_cached(cache_key, cache_level)
                if result is not None:
                    with self.metrics_lock:
                        self.metrics.cache_hits += 1
                    return result
                
                # Cache miss - execute function
                with self.metrics_lock:
                    self.metrics.cache_misses += 1
                
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Update response time metric
                with self.metrics_lock:
                    self.metrics.average_response_time = (
                        (self.metrics.average_response_time * 0.9) + 
                        (execution_time * 0.1)
                    )
                
                # Cache the result
                self._set_cached(cache_key, result, cache_level, ttl)
                
                return result
            
            return wrapper
        return decorator
    
    def background_task(self, job_type: str = "thread", priority: int = 0):
        """
        Decorator for background task execution
        
        Args:
            job_type: "thread" or "process"
            priority: Task priority
            
        Returns:
            Decorated function that returns job ID
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                job_id = self.job_processor.submit_job(
                    func, args, kwargs, job_type, priority
                )
                return {'job_id': job_id, 'status': 'submitted'}
            
            return wrapper
        return decorator
    
    def optimize_query(self, query_name: str, query_func: Callable, 
                      cache_ttl: int = 300) -> Callable:
        """
        Optimize database queries with caching and monitoring
        
        Args:
            query_name: Name for the query
            query_func: Query function to optimize
            cache_ttl: Cache TTL in seconds
            
        Returns:
            Optimized query function
        """
        @wraps(query_func)
        def optimized_query(*args, **kwargs):
            # Generate cache key for query
            cache_key = f"query_{query_name}_{self._generate_cache_key('', args, kwargs)}"
            
            # Try cache first
            result = self._get_cached(cache_key, CacheLevel.MEMORY)
            if result is not None:
                return result
            
            # Execute query with timing
            start_time = time.time()
            result = query_func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Track query performance
            self.query_stats[query_name].append(execution_time)
            
            # Keep only last 100 measurements
            if len(self.query_stats[query_name]) > 100:
                self.query_stats[query_name] = self.query_stats[query_name][-100:]
            
            # Cache result
            self._set_cached(cache_key, result, CacheLevel.MEMORY, cache_ttl)
            
            # Log slow queries
            if execution_time > 1.0:  # Slower than 1 second
                logger.warning(f"Slow query detected: {query_name} took {execution_time:.2f}s")
            
            return result
        
        return optimized_query
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self.metrics_lock:
            metrics = {
                'cache_metrics': {
                    'hits': self.metrics.cache_hits,
                    'misses': self.metrics.cache_misses,
                    'hit_rate': (self.metrics.cache_hits / 
                               max(1, self.metrics.cache_hits + self.metrics.cache_misses) * 100),
                    'memory_cache_size': self.memory_cache.size(),
                    'disk_cache_size': self.disk_cache.size()
                },
                'job_metrics': self.job_processor.get_queue_stats(),
                'query_metrics': {
                    name: {
                        'count': len(times),
                        'avg_time': sum(times) / len(times) if times else 0,
                        'max_time': max(times) if times else 0,
                        'min_time': min(times) if times else 0
                    }
                    for name, times in self.query_stats.items()
                },
                'system_metrics': {
                    'average_response_time': self.metrics.average_response_time,
                    'memory_usage': self._get_memory_usage(),
                    'cpu_usage': self._get_cpu_usage()
                }
            }
        
        return metrics
    
    def clear_cache(self, cache_level: Optional[CacheLevel] = None) -> None:
        """Clear cache at specified level"""
        if cache_level is None or cache_level == CacheLevel.MEMORY:
            self.memory_cache.clear()
        
        if cache_level is None or cache_level == CacheLevel.DISK:
            self.disk_cache.clear()
        
        if cache_level is None:
            self.query_cache.clear()
        
        logger.info(f"Cache cleared: {cache_level.value if cache_level else 'all'}")
    
    def preload_cache(self, data_loader: Callable, keys: List[str]) -> None:
        """Preload cache with commonly accessed data"""
        def preload_job():
            for key in keys:
                try:
                    data = data_loader(key)
                    self._set_cached(f"preload_{key}", data, CacheLevel.HYBRID)
                except Exception as e:
                    logger.error(f"Error preloading cache key {key}: {e}")
        
        self.job_processor.submit_job(preload_job, job_type="thread")
        logger.info(f"Cache preload started for {len(keys)} keys")
    
    def _generate_cache_key(self, func_name: str, args: tuple, kwargs: Dict) -> str:
        """Generate cache key from function name and arguments"""
        key_data = {
            'func': func_name,
            'args': str(args),
            'kwargs': sorted(kwargs.items()) if kwargs else []
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached(self, key: str, cache_level: CacheLevel) -> Optional[Any]:
        """Get item from appropriate cache level"""
        if cache_level in [CacheLevel.MEMORY, CacheLevel.HYBRID]:
            result = self.memory_cache.get(key)
            if result is not None:
                return result
        
        if cache_level in [CacheLevel.DISK, CacheLevel.HYBRID]:
            result = self.disk_cache.get(key)
            if result is not None:
                # Promote to memory cache for hybrid strategy
                if cache_level == CacheLevel.HYBRID:
                    self.memory_cache.set(key, result)
                return result
        
        return None
    
    def _set_cached(self, key: str, value: Any, cache_level: CacheLevel, 
                   ttl: Optional[int] = None) -> None:
        """Set item in appropriate cache level"""
        if cache_level in [CacheLevel.MEMORY, CacheLevel.HYBRID]:
            self.memory_cache.set(key, value)
        
        if cache_level in [CacheLevel.DISK, CacheLevel.HYBRID]:
            self.disk_cache.set(key, value)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except ImportError:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            return 0.0


# Global instance
performance_optimizer = PerformanceOptimizer()