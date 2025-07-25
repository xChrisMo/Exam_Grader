"""Performance Optimization Manager for Exam Grader Application.

This module provides comprehensive performance optimization including caching,
database optimization, resource management, and monitoring.
"""
from typing import Any, Dict, List, Optional, Tuple, Callable

import time
import psutil
import threading
import gc
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from functools import wraps

try:
    from utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache only")

try:
    from flask import request, g
    from flask_caching import Cache
except ImportError:
    # Fallback for non-Flask environments
    request = None
    g = None
    Cache = None


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    request_count: int = 0
    total_response_time: float = 0.0
    average_response_time: float = 0.0
    peak_response_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    cache_hit_rate: float = 0.0
    database_query_count: int = 0
    database_query_time: float = 0.0
    active_connections: int = 0
    error_count: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def update_response_time(self, response_time: float):
        """Update response time metrics."""
        self.request_count += 1
        self.total_response_time += response_time
        self.average_response_time = self.total_response_time / self.request_count
        if response_time > self.peak_response_time:
            self.peak_response_time = response_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'request_count': self.request_count,
            'average_response_time': round(self.average_response_time, 3),
            'peak_response_time': round(self.peak_response_time, 3),
            'memory_usage_mb': round(self.memory_usage_mb, 2),
            'cpu_usage_percent': round(self.cpu_usage_percent, 2),
            'cache_hit_rate': round(self.cache_hit_rate, 3),
            'database_query_count': self.database_query_count,
            'database_query_time': round(self.database_query_time, 3),
            'active_connections': self.active_connections,
            'error_count': self.error_count,
            'timestamp': self.timestamp.isoformat()
        }


class MemoryCache:
    """High-performance in-memory cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """Initialize memory cache.
        
        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock()
        
        logger.info(f"Memory cache initialized (max_size: {max_size}, default_ttl: {default_ttl}s)")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            value, expiry = self._cache[key]
            
            # Check if expired
            if time.time() > expiry:
                self._remove_key(key)
                return None
            
            # Update access time
            self._access_times[key] = time.time()
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if set successfully
        """
        with self._lock:
            # Check if we need to evict items
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            ttl = ttl or self.default_ttl
            expiry = time.time() + ttl
            
            self._cache[key] = (value, expiry)
            self._access_times[key] = time.time()
            
            return True
    
    def delete(self, key: str) -> bool:
        """Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
        """
        with self._lock:
            if key in self._cache:
                self._remove_key(key)
                return True
            return False
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, (value, expiry) in self._cache.items():
                if current_time > expiry:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_key(key)
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Cache statistics
        """
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': getattr(self, '_hit_rate', 0.0),
                'memory_usage': self._estimate_memory_usage()
            }
    
    def _remove_key(self, key: str):
        """Remove key from cache and access times."""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
    
    def _evict_lru(self):
        """Evict least recently used item."""
        if not self._access_times:
            return
        
        # Find least recently used key
        lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]
        self._remove_key(lru_key)
    
    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes."""
        import sys
        total_size = 0
        
        for key, (value, expiry) in self._cache.items():
            total_size += sys.getsizeof(key)
            total_size += sys.getsizeof(value)
            total_size += sys.getsizeof(expiry)
        
        return total_size


class DatabaseOptimizer:
    """Database query optimization and monitoring."""
    
    def __init__(self):
        """Initialize database optimizer."""
        self.query_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'average_time': 0.0,
            'max_time': 0.0,
            'last_executed': None
        })
        self.slow_query_threshold = 1.0  # seconds
        self.slow_queries: deque = deque(maxlen=100)
        self._lock = threading.Lock()
        
        logger.info("Database optimizer initialized")
    
    def track_query(self, query: str, execution_time: float, params: Optional[Dict] = None):
        """Track database query performance.
        
        Args:
            query: SQL query string
            execution_time: Query execution time in seconds
            params: Query parameters
        """
        with self._lock:
            # Normalize query for tracking
            normalized_query = self._normalize_query(query)
            
            stats = self.query_stats[normalized_query]
            stats['count'] += 1
            stats['total_time'] += execution_time
            stats['average_time'] = stats['total_time'] / stats['count']
            stats['max_time'] = max(stats['max_time'], execution_time)
            stats['last_executed'] = datetime.utcnow()
            
            # Track slow queries
            if execution_time > self.slow_query_threshold:
                self.slow_queries.append({
                    'query': query,
                    'execution_time': execution_time,
                    'params': params,
                    'timestamp': datetime.utcnow()
                })
                
                logger.warning(f"Slow query detected ({execution_time:.3f}s): {query[:100]}...")
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get query performance statistics.
        
        Returns:
            Query statistics
        """
        with self._lock:
            total_queries = sum(stats['count'] for stats in self.query_stats.values())
            total_time = sum(stats['total_time'] for stats in self.query_stats.values())
            
            # Get top slow queries
            top_slow = sorted(
                [(query, stats) for query, stats in self.query_stats.items()],
                key=lambda x: x[1]['average_time'],
                reverse=True
            )[:10]
            
            return {
                'total_queries': total_queries,
                'total_time': round(total_time, 3),
                'average_time': round(total_time / max(total_queries, 1), 3),
                'slow_query_count': len(self.slow_queries),
                'top_slow_queries': [
                    {
                        'query': query[:100] + '...' if len(query) > 100 else query,
                        'count': stats['count'],
                        'average_time': round(stats['average_time'], 3),
                        'max_time': round(stats['max_time'], 3)
                    }
                    for query, stats in top_slow
                ]
            }
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for tracking purposes.
        
        Args:
            query: SQL query string
            
        Returns:
            Normalized query string
        """
        # Remove extra whitespace and normalize case
        normalized = ' '.join(query.strip().split())
        
        # Replace parameter placeholders with generic markers
        import re
        normalized = re.sub(r'\$\d+|\?|%s', '?', normalized)
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        
        return normalized.upper()


class ResourceMonitor:
    """System resource monitoring."""
    
    def __init__(self, monitoring_interval: int = 60):
        """Initialize resource monitor.
        
        Args:
            monitoring_interval: Monitoring interval in seconds
        """
        self.monitoring_interval = monitoring_interval
        self.metrics_history: deque = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        logger.info(f"Resource monitor initialized (interval: {monitoring_interval}s)")
    
    def start_monitoring(self):
        """Start resource monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        logger.info("Resource monitoring stopped")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics.
        
        Returns:
            Current system metrics
        """
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            memory_percent = memory.percent
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Network metrics (if available)
            try:
                network = psutil.net_io_counters()
                network_sent = network.bytes_sent
                network_recv = network.bytes_recv
            except:
                network_sent = network_recv = 0
            
            # Process metrics
            process = psutil.Process()
            process_memory = process.memory_info().rss / (1024 * 1024)
            process_cpu = process.cpu_percent()
            
            return {
                'cpu_percent': round(cpu_percent, 2),
                'cpu_count': cpu_count,
                'memory_mb': round(memory_mb, 2),
                'memory_percent': round(memory_percent, 2),
                'disk_percent': round(disk_percent, 2),
                'network_sent': network_sent,
                'network_recv': network_recv,
                'process_memory_mb': round(process_memory, 2),
                'process_cpu_percent': round(process_cpu, 2),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {}
    
    def get_metrics_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics history.
        
        Args:
            hours: Number of hours of history to return
            
        Returns:
            List of historical metrics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return [
            metrics for metrics in self.metrics_history
            if datetime.fromisoformat(metrics['timestamp']) > cutoff_time
        ]
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._monitoring:
            try:
                metrics = self.get_current_metrics()
                if metrics:
                    self.metrics_history.append(metrics)
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(self.monitoring_interval)


class PerformanceOptimizer:
    """Main performance optimization manager."""
    
    def __init__(self, app=None, redis_url: Optional[str] = None):
        """Initialize performance optimizer.
        
        Args:
            app: Flask application instance
            redis_url: Redis connection URL
        """
        self.app = app
        self.memory_cache = MemoryCache()
        self.database_optimizer = DatabaseOptimizer()
        self.resource_monitor = ResourceMonitor()
        self.metrics = PerformanceMetrics()
        
        # Initialize Redis cache if available
        self.redis_cache = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_cache = redis.from_url(redis_url)
                self.redis_cache.ping()
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {str(e)}")
        
        # Initialize Flask-Caching if available
        self.flask_cache = None
        if app and Cache:
            try:
                cache_config = {
                    'CACHE_TYPE': 'redis' if self.redis_cache else 'simple',
                    'CACHE_DEFAULT_TIMEOUT': 3600
                }
                if self.redis_cache:
                    cache_config['CACHE_REDIS_URL'] = redis_url
                
                self.flask_cache = Cache(app, config=cache_config)
                logger.info("Flask cache initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Flask cache: {str(e)}")
        
        # Performance tracking
        self._request_start_times: Dict[str, float] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        if app:
            self.init_app(app)
        
        logger.info("Performance optimizer initialized")
    
    def init_app(self, app):
        """Initialize with Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Register request hooks
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring()
        
        # Schedule periodic cleanup
        self._schedule_cleanup()
        
        logger.info("Performance optimizer integrated with Flask app")
    
    def cache_get(self, key: str, use_redis: bool = True) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            use_redis: Whether to use Redis cache
            
        Returns:
            Cached value or None
        """
        # Try Redis first if available
        if use_redis and self.redis_cache:
            try:
                value = self.redis_cache.get(key)
                if value is not None:
                    self._cache_hits += 1
                    import pickle
                    return pickle.loads(value)
            except Exception as e:
                logger.warning(f"Redis cache get error: {str(e)}")
        
        # Fall back to memory cache
        value = self.memory_cache.get(key)
        if value is not None:
            self._cache_hits += 1
            return value
        
        self._cache_misses += 1
        return None
    
    def cache_set(self, key: str, value: Any, ttl: Optional[int] = None, use_redis: bool = True) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            use_redis: Whether to use Redis cache
            
        Returns:
            True if set successfully
        """
        success = False
        
        # Set in Redis if available
        if use_redis and self.redis_cache:
            try:
                import pickle
                serialized_value = pickle.dumps(value)
                if ttl:
                    self.redis_cache.setex(key, ttl, serialized_value)
                else:
                    self.redis_cache.set(key, serialized_value)
                success = True
            except Exception as e:
                logger.warning(f"Redis cache set error: {str(e)}")
        
        # Always set in memory cache as backup
        self.memory_cache.set(key, value, ttl)
        
        return success
    
    def cache_delete(self, key: str, use_redis: bool = True) -> bool:
        """Delete key from cache.
        
        Args:
            key: Cache key
            use_redis: Whether to use Redis cache
            
        Returns:
            True if key was deleted
        """
        success = False
        
        # Delete from Redis if available
        if use_redis and self.redis_cache:
            try:
                self.redis_cache.delete(key)
                success = True
            except Exception as e:
                logger.warning(f"Redis cache delete error: {str(e)}")
        
        # Delete from memory cache
        self.memory_cache.delete(key)
        
        return success
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report.
        
        Returns:
            Performance report
        """
        # Update current metrics
        current_system_metrics = self.resource_monitor.get_current_metrics()
        self.metrics.memory_usage_mb = current_system_metrics.get('process_memory_mb', 0)
        self.metrics.cpu_usage_percent = current_system_metrics.get('process_cpu_percent', 0)
        
        # Calculate cache hit rate
        total_cache_requests = self._cache_hits + self._cache_misses
        self.metrics.cache_hit_rate = (
            self._cache_hits / max(total_cache_requests, 1)
        )
        
        return {
            'performance_metrics': self.metrics.to_dict(),
            'cache_stats': {
                'memory_cache': self.memory_cache.get_stats(),
                'redis_available': self.redis_cache is not None,
                'hit_rate': round(self.metrics.cache_hit_rate, 3)
            },
            'database_stats': self.database_optimizer.get_query_stats(),
            'system_metrics': current_system_metrics,
            'resource_history': self.resource_monitor.get_metrics_history(1)
        }
    
    def _before_request(self):
        """Handle before request."""
        if request:
            request_id = id(request)
            self._request_start_times[request_id] = time.time()
    
    def _after_request(self, response):
        """Handle after request.
        
        Args:
            response: Flask response object
            
        Returns:
            Modified response object
        """
        if request:
            request_id = id(request)
            start_time = self._request_start_times.pop(request_id, None)
            
            if start_time:
                response_time = time.time() - start_time
                self.metrics.update_response_time(response_time)
                
                # Log slow requests
                if response_time > 2.0:  # 2 seconds threshold
                    logger.warning(f"Slow request: {request.path} ({response_time:.3f}s)")
        
        return response
    
    def _schedule_cleanup(self):
        """Schedule periodic cleanup tasks."""
        def cleanup_task():
            try:
                # Clean up expired cache entries
                expired_count = self.memory_cache.cleanup_expired()
                if expired_count > 0:
                    logger.debug(f"Cleaned up {expired_count} expired cache entries")
                
                # Force garbage collection periodically
                gc.collect()
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {str(e)}")
            
            # Schedule next cleanup
            if self.app:
                threading.Timer(300, cleanup_task).start()  # 5 minutes
        
        # Start initial cleanup timer
        threading.Timer(300, cleanup_task).start()


# Decorators for performance optimization
def cached(timeout: int = 3600, key_prefix: str = ''):
    """Decorator for caching function results.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Key prefix for cache
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            import hashlib
            key_data = f"{key_prefix}:{f.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try to get from cache
            optimizer = get_performance_optimizer()
            if optimizer:
                cached_result = optimizer.cache_get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            
            if optimizer:
                optimizer.cache_set(cache_key, result, timeout)
            
            return result
        
        return decorated_function
    
    return decorator


def monitor_performance(f: Callable) -> Callable:
    """Decorator for monitoring function performance.
    
    Args:
        f: Function to monitor
        
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = f(*args, **kwargs)
            return result
        except Exception as e:
            # Track errors
            optimizer = get_performance_optimizer()
            if optimizer:
                optimizer.metrics.error_count += 1
            raise
        finally:
            execution_time = time.time() - start_time
            
            # Log slow functions
            if execution_time > 1.0:  # 1 second threshold
                logger.warning(f"Slow function: {f.__name__} ({execution_time:.3f}s)")
    
    return decorated_function


# Global performance optimizer instance
performance_optimizer = None


def init_performance_optimizer(app=None, redis_url: Optional[str] = None) -> PerformanceOptimizer:
    """Initialize global performance optimizer.
    
    Args:
        app: Flask application instance
        redis_url: Redis connection URL
        
    Returns:
        PerformanceOptimizer instance
    """
    global performance_optimizer
    performance_optimizer = PerformanceOptimizer(app, redis_url)
    return performance_optimizer


def get_performance_optimizer() -> Optional[PerformanceOptimizer]:
    """Get global performance optimizer instance.
    
    Returns:
        PerformanceOptimizer instance or None
    """
    return performance_optimizer