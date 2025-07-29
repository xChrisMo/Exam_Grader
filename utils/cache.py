"""
Cache System for Exam Grader

This module provides a simple in-memory cache with TTL support and statistics tracking.
"""

import time
import threading
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field
from collections import OrderedDict

from utils.logger import logger

@dataclass
class CacheEntry:
    """Cache entry with value and metadata."""
    value: Any
    created_at: float
    ttl: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def access(self):
        """Record access to this entry."""
        self.access_count += 1
        self.last_accessed = time.time()

class Cache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of entries to store
            default_ttl: Default TTL in seconds (None for no expiration)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0,
            'expired_cleanups': 0
        }
    
    def get(self, key: str) -> Any:
        """Get value from cache."""
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired():
                del self._cache[key]
                self._stats['misses'] += 1
                self._stats['expired_cleanups'] += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.access()
            self._stats['hits'] += 1
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        with self._lock:
            if ttl is None:
                ttl = self.default_ttl
            
            # Create new entry
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl
            )
            
            if key in self._cache:
                del self._cache[key]
            
            # Add new entry
            self._cache[key] = entry
            self._cache.move_to_end(key)
            self._stats['sets'] += 1
            
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats['evictions'] += 1
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats['deletes'] += 1
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    def cleanup(self) -> Dict[str, int]:
        """Remove expired entries and return cleanup stats."""
        with self._lock:
            expired_keys = []
            current_time = time.time()
            
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                self._stats['expired_cleanups'] += 1
            
            cleanup_stats = {
                'expired_removed': len(expired_keys),
                'remaining_entries': len(self._cache)
            }
            
            if expired_keys:
                logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")
            
            return cleanup_stats
    
    def get_stats(self) -> Dict[str, Union[int, float]]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests) if total_requests > 0 else 0
            
            return {
                'total_requests': total_requests,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': round(hit_rate, 3),
                'sets': self._stats['sets'],
                'deletes': self._stats['deletes'],
                'evictions': self._stats['evictions'],
                'expired_cleanups': self._stats['expired_cleanups'],
                'current_size': len(self._cache),
                'max_size': self.max_size
            }
    
    def get_keys(self) -> list:
        """Get list of all keys in cache."""
        with self._lock:
            return list(self._cache.keys())
    
    def get_size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)
    
    def contains(self, key: str) -> bool:
        """Check if key exists in cache (without accessing it)."""
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self._stats['expired_cleanups'] += 1
                return False
            
            return True
    
    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get information about a cache entry."""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self._stats['expired_cleanups'] += 1
                return None
            
            return {
                'key': key,
                'created_at': entry.created_at,
                'ttl': entry.ttl,
                'access_count': entry.access_count,
                'last_accessed': entry.last_accessed,
                'age_seconds': time.time() - entry.created_at,
                'expires_in': (
                    entry.ttl - (time.time() - entry.created_at) 
                    if entry.ttl else None
                )
            }

# Global cache instance
_global_cache = Cache(max_size=1000, default_ttl=3600)  # 1 hour default TTL

def get_cache() -> Cache:
    """Get the global cache instance."""
    return _global_cache

def cache_get(key: str) -> Any:
    """Get value from global cache."""
    return _global_cache.get(key)

def cache_set(key: str, value: Any, ttl: Optional[float] = None) -> None:
    """Set value in global cache."""
    _global_cache.set(key, value, ttl)

def cache_delete(key: str) -> bool:
    """Delete key from global cache."""
    return _global_cache.delete(key)

def cache_clear() -> None:
    """Clear global cache."""
    _global_cache.clear()

def cache_cleanup() -> Dict[str, int]:
    """Cleanup expired entries from global cache."""
    return _global_cache.cleanup()

def cache_stats() -> Dict[str, Union[int, float]]:
    """Get global cache statistics."""
    return _global_cache.get_stats()
