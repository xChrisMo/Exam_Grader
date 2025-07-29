"""
Query Result Caching for Performance Optimization.

This module provides caching mechanisms for database queries and expensive operations
to improve application performance.
"""
from typing import Any, Dict, Optional, Callable

import hashlib
import json
import time
from functools import wraps
from datetime import datetime, timedelta

try:
    FLASK_CACHING_AVAILABLE = True
except ImportError:
    FLASK_CACHING_AVAILABLE = False
    Cache = None

from utils.logger import logger

class QueryCache:
    """Simple in-memory cache for query results."""
    
    def __init__(self, default_timeout: int = 300, max_size: int = 1000):
        """Initialize query cache.
        
        Args:
            default_timeout: Default cache timeout in seconds
            max_size: Maximum number of cached items
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_timeout = default_timeout
        self.max_size = max_size
        self.access_times: Dict[str, float] = {}
        
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function name and arguments."""
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {}
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        if 'expires_at' not in cache_entry:
            return True
        return datetime.now() > cache_entry['expires_at']
    
    def _cleanup_expired(self):
        """Remove expired entries from cache."""
        current_time = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time > entry.get('expires_at', current_time)
        ]
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def _evict_lru(self):
        """Evict least recently used items if cache is full."""
        if len(self.cache) >= self.max_size:
            # Remove 20% of least recently used items
            num_to_remove = max(1, self.max_size // 5)
            sorted_keys = sorted(self.access_times.items(), key=lambda x: x[1])
            
            for key, _ in sorted_keys[:num_to_remove]:
                self.cache.pop(key, None)
                self.access_times.pop(key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if self._is_expired(entry):
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
            return None
        
        # Update access time
        self.access_times[key] = time.time()
        return entry['value']
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """Set value in cache."""
        self._cleanup_expired()
        self._evict_lru()
        
        timeout = timeout or self.default_timeout
        expires_at = datetime.now() + timedelta(seconds=timeout)
        
        self.cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': datetime.now()
        }
        self.access_times[key] = time.time()
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self.cache:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_total_requests', 1), 1),
            'entries': list(self.cache.keys())
        }

# Global cache instance
_query_cache = QueryCache()

def cached_query(timeout: int = 300, key_prefix: str = ""):
    """Decorator for caching query results.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Optional prefix for cache keys
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            func_name = f"{key_prefix}{func.__module__}.{func.__name__}"
            cache_key = _query_cache._generate_key(func_name, args, kwargs)
            
            cached_result = _query_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func_name}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func_name}, executing...")
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Cache the result
            _query_cache.set(cache_key, result, timeout)
            
            logger.debug(f"Cached result for {func_name} (execution: {execution_time:.3f}s)")
            return result
        
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str) -> int:
    """Invalidate cache entries matching a pattern.
    
    Args:
        pattern: Pattern to match against cache keys
        
    Returns:
        Number of invalidated entries
    """
    invalidated = 0
    keys_to_remove = []
    
    for key in _query_cache.cache.keys():
        if pattern in key:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        if _query_cache.delete(key):
            invalidated += 1
    
    logger.info(f"Invalidated {invalidated} cache entries matching pattern: {pattern}")
    return invalidated

def get_cache_stats() -> Dict[str, Any]:
    """Get global cache statistics."""
    return _query_cache.get_stats()

def clear_cache() -> None:
    """Clear all cached data."""
    _query_cache.clear()
    logger.info("Cache cleared")

# Performance monitoring decorator
def monitor_performance(log_slow_queries: bool = True, slow_threshold: float = 1.0):
    """Decorator to monitor function performance.
    
    Args:
        log_slow_queries: Whether to log slow function calls
        slow_threshold: Threshold in seconds for considering a call slow
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                
                if log_slow_queries and execution_time > slow_threshold:
                    logger.warning(
                        f"Slow function call: {func.__module__}.{func.__name__} "
                        f"took {execution_time:.3f}s"
                    )
                elif execution_time > 0.1:  # Log anything over 100ms at debug level
                    logger.debug(
                        f"Function call: {func.__module__}.{func.__name__} "
                        f"took {execution_time:.3f}s"
                    )
        
        return wrapper
    return decorator
