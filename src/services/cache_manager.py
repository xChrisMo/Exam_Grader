"""
Cache Manager

This module provides a comprehensive caching system with multi-level caching support,
automatic expiration, cleanup mechanisms, and performance monitoring.
"""

import time
import threading
import pickle
import hashlib
import os
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
import json

from src.config.processing_config import ProcessingConfigManager
from utils.logger import logger

class CacheType(Enum):
    """Types of cache storage"""
    MEMORY = "memory"
    DISK = "disk"
    HYBRID = "hybrid"

class CachePolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In, First Out
    TTL = "ttl"  # Time To Live only

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl: Optional[int] = None  # Time to live in seconds
    size: int = 0  # Size in bytes
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl is None:
            return False
        return (datetime.now(timezone.utc) - self.created_at).total_seconds() > self.ttl
    
    def touch(self):
        """Update access information"""
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count += 1

@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expired_removals: int = 0
    total_size: int = 0
    entry_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def miss_rate(self) -> float:
        """Calculate miss rate"""
        return 1.0 - self.hit_rate

class CacheLevel:
    """Individual cache level implementation"""
    
    def __init__(self, name: str, cache_type: CacheType, max_size: int = 1000,
                 max_memory: int = 100 * 1024 * 1024,  # 100MB
                 policy: CachePolicy = CachePolicy.LRU,
                 default_ttl: Optional[int] = None,
                 disk_path: Optional[str] = None):
        self.name = name
        self.cache_type = cache_type
        self.max_size = max_size
        self.max_memory = max_memory
        self.policy = policy
        self.default_ttl = default_ttl
        self.disk_path = Path(disk_path) if disk_path else Path("cache") / name
        
        self._entries: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._lock = threading.RLock()
        
        if self.cache_type in [CacheType.DISK, CacheType.HYBRID]:
            self.disk_path.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            # Check memory cache first
            if key in self._entries:
                entry = self._entries[key]
                
                if entry.is_expired():
                    self._remove_entry(key)
                    self._stats.expired_removals += 1
                    self._stats.misses += 1
                    return None
                
                # Update access info
                entry.touch()
                self._stats.hits += 1
                
                if self.cache_type == CacheType.HYBRID and entry.value is None:
                    entry.value = self._load_from_disk(key)
                
                if self.cache_type == CacheType.DISK:
                    return self._load_from_disk(key)
                
                return entry.value
            
            elif self.cache_type == CacheType.DISK:
                logger.debug(f"Disk cache get for key: {key}")
                value = self._load_from_disk(key)
                logger.debug(f"Loaded from disk: {value is not None}")
                if value is not None:
                    # Create or update metadata entry
                    if key in self._entries:
                        entry = self._entries[key]
                        if entry.is_expired():
                            self._remove_entry(key)
                            self._stats.expired_removals += 1
                            self._stats.misses += 1
                            return None
                        entry.touch()
                    else:
                        entry = CacheEntry(
                            key=key,
                            value=None,  # Don't store in memory for disk cache
                            created_at=datetime.now(timezone.utc),
                            last_accessed=datetime.now(timezone.utc),
                            access_count=1
                        )
                        self._entries[key] = entry
                    
                    self._stats.hits += 1
                    logger.debug(f"Returning disk cache value for {key}")
                    return value
            
            self._stats.misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        with self._lock:
            ttl = ttl or self.default_ttl
            
            # Calculate size
            try:
                size = len(pickle.dumps(value))
            except Exception:
                size = len(str(value).encode('utf-8'))
            
            if not self._make_space(size):
                logger.warning(f"Could not make space for cache entry {key}")
                return False
            
            # Create entry
            entry = CacheEntry(
                key=key,
                value=value if self.cache_type != CacheType.DISK else None,
                created_at=datetime.now(timezone.utc),
                last_accessed=datetime.now(timezone.utc),
                access_count=1,
                ttl=ttl,
                size=size
            )
            
            if self.cache_type in [CacheType.DISK, CacheType.HYBRID]:
                if not self._save_to_disk(key, value):
                    return False
            
            if key in self._entries:
                self._remove_entry(key)
            
            # Add new entry
            self._entries[key] = entry
            self._update_stats()
            
            logger.debug(f"Cached {key} in {self.name} (size: {size} bytes)")
            return True
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        with self._lock:
            if key in self._entries:
                self._remove_entry(key)
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            # Remove disk files
            if self.cache_type in [CacheType.DISK, CacheType.HYBRID]:
                for key in list(self._entries.keys()):
                    self._remove_disk_file(key)
            
            self._entries.clear()
            self._stats = CacheStats()
            logger.info(f"Cleared cache level {self.name}")
    
    def cleanup_expired(self) -> int:
        """Remove expired entries"""
        removed_count = 0
        with self._lock:
            expired_keys = []
            for key, entry in self._entries.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_entry(key)
                removed_count += 1
            
            self._stats.expired_removals += removed_count
            
        if removed_count > 0:
            logger.debug(f"Removed {removed_count} expired entries from {self.name}")
        
        return removed_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'name': self.name,
                'type': self.cache_type.value,
                'policy': self.policy.value,
                'max_size': self.max_size,
                'max_memory': self.max_memory,
                'current_size': len(self._entries),
                'current_memory': self._stats.total_size,
                'hits': self._stats.hits,
                'misses': self._stats.misses,
                'hit_rate': self._stats.hit_rate,
                'evictions': self._stats.evictions,
                'expired_removals': self._stats.expired_removals,
                'memory_usage_percent': (self._stats.total_size / self.max_memory) * 100,
                'size_usage_percent': (len(self._entries) / self.max_size) * 100
            }
    
    def _make_space(self, needed_size: int) -> bool:
        """Make space for new entry"""
        # Check size limit
        if len(self._entries) >= self.max_size:
            if not self._evict_entries(1):
                return False
        
        # Check memory limit
        if self._stats.total_size + needed_size > self.max_memory:
            # Calculate how much to evict
            to_evict = (self._stats.total_size + needed_size) - self.max_memory
            if not self._evict_by_size(to_evict):
                return False
        
        return True
    
    def _evict_entries(self, count: int) -> bool:
        """Evict entries based on policy"""
        if not self._entries:
            return False
        
        entries_to_evict = []
        
        if self.policy == CachePolicy.LRU:
            # Sort by last accessed time
            sorted_entries = sorted(
                self._entries.items(),
                key=lambda x: x[1].last_accessed
            )
            entries_to_evict = sorted_entries[:count]
            
        elif self.policy == CachePolicy.LFU:
            # Sort by access count
            sorted_entries = sorted(
                self._entries.items(),
                key=lambda x: x[1].access_count
            )
            entries_to_evict = sorted_entries[:count]
            
        elif self.policy == CachePolicy.FIFO:
            # Sort by creation time
            sorted_entries = sorted(
                self._entries.items(),
                key=lambda x: x[1].created_at
            )
            entries_to_evict = sorted_entries[:count]
            
        elif self.policy == CachePolicy.TTL:
            # Remove expired entries first
            expired = [(k, v) for k, v in self._entries.items() if v.is_expired()]
            if len(expired) >= count:
                entries_to_evict = expired[:count]
            else:
                non_expired = [(k, v) for k, v in self._entries.items() if not v.is_expired()]
                sorted_entries = sorted(non_expired, key=lambda x: x[1].last_accessed)
                entries_to_evict = expired + sorted_entries[:count - len(expired)]
        
        # Remove selected entries
        for key, _ in entries_to_evict:
            self._remove_entry(key)
            self._stats.evictions += 1
        
        return len(entries_to_evict) > 0
    
    def _evict_by_size(self, target_size: int) -> bool:
        """Evict entries to free up target size"""
        freed_size = 0
        evicted_count = 0
        
        # Sort entries by policy
        if self.policy == CachePolicy.LRU:
            sorted_entries = sorted(
                self._entries.items(),
                key=lambda x: x[1].last_accessed
            )
        elif self.policy == CachePolicy.LFU:
            sorted_entries = sorted(
                self._entries.items(),
                key=lambda x: x[1].access_count
            )
        else:  # FIFO or TTL
            sorted_entries = sorted(
                self._entries.items(),
                key=lambda x: x[1].created_at
            )
        
        for key, entry in sorted_entries:
            if freed_size >= target_size:
                break
            
            freed_size += entry.size
            self._remove_entry(key)
            evicted_count += 1
            self._stats.evictions += 1
        
        logger.debug(f"Evicted {evicted_count} entries, freed {freed_size} bytes")
        return freed_size >= target_size
    
    def _remove_entry(self, key: str):
        """Remove entry from cache"""
        if key in self._entries:
            entry = self._entries[key]
            
            if self.cache_type in [CacheType.DISK, CacheType.HYBRID]:
                self._remove_disk_file(key)
            
            del self._entries[key]
            self._update_stats()
    
    def _save_to_disk(self, key: str, value: Any) -> bool:
        """Save value to disk"""
        try:
            file_path = self.disk_path / f"{self._hash_key(key)}.cache"
            with open(file_path, 'wb') as f:
                pickle.dump(value, f)
            return True
        except Exception as e:
            logger.error(f"Failed to save {key} to disk: {e}")
            return False
    
    def _load_from_disk(self, key: str) -> Optional[Any]:
        """Load value from disk"""
        try:
            file_path = self.disk_path / f"{self._hash_key(key)}.cache"
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    value = pickle.load(f)
                    logger.debug(f"Loaded {key} from disk: {file_path}")
                    return value
        except Exception as e:
            logger.error(f"Failed to load {key} from disk: {e}")
        return None
    
    def _remove_disk_file(self, key: str):
        """Remove disk file for key"""
        try:
            file_path = self.disk_path / f"{self._hash_key(key)}.cache"
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.error(f"Failed to remove disk file for {key}: {e}")
    
    def _hash_key(self, key: str) -> str:
        """Create hash for key to use as filename"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _update_stats(self):
        """Update cache statistics"""
        self._stats.entry_count = len(self._entries)
        self._stats.total_size = sum(entry.size for entry in self._entries.values())

class CacheManager:
    """Multi-level cache manager"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize processing configuration
        self._config_manager = ProcessingConfigManager()
        self._cache_config = self._config_manager.get_cache_config()
        
        self._levels: Dict[str, CacheLevel] = {}
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_interval = self._cache_config.cleanup_interval if self._cache_config.enabled else 300
        self._running = False
        
        if self._cache_config.enabled:
            self._setup_configured_levels()
        else:
            self._setup_default_levels()
        
        if self._cache_config.auto_cleanup_enabled:
            self.start_cleanup_thread()
    
    def _setup_configured_levels(self):
        """Setup cache levels from processing configuration."""
        try:
            size_limits = self._cache_config.size_limits
            
            # L1: Fast memory cache
            l1_config = size_limits.get('default', size_limits.get('ocr_cache', None))
            if l1_config:
                self.add_cache_level(
                    name="l1_memory",
                    cache_type=CacheType.MEMORY,
                    max_size=l1_config.max_entries,
                    max_memory=l1_config.max_size_mb * 1024 * 1024,
                    policy=CachePolicy.LRU,
                    default_ttl=self._cache_config.get_expiration_time('ocr_results')
                )
            
            # L2: LLM cache
            l2_config = size_limits.get('llm_cache', l1_config)
            if l2_config:
                self.add_cache_level(
                    name="l2_memory",
                    cache_type=CacheType.MEMORY,
                    max_size=l2_config.max_entries,
                    max_memory=l2_config.max_size_mb * 1024 * 1024,
                    policy=CachePolicy.LFU,
                    default_ttl=self._cache_config.get_expiration_time('llm_responses')
                )
            
            # L3: File cache (disk)
            l3_config = size_limits.get('file_cache', l1_config)
            if l3_config:
                self.add_cache_level(
                    name="l3_disk",
                    cache_type=CacheType.DISK,
                    max_size=l3_config.max_entries,
                    max_memory=l3_config.max_size_mb * 1024 * 1024,
                    policy=CachePolicy.LRU,
                    default_ttl=self._cache_config.get_expiration_time('file_metadata'),
                    disk_path=str(self.cache_dir / "l3_disk")
                )
            
            # L4: Template cache (hybrid)
            l4_config = size_limits.get('template_cache', l1_config)
            if l4_config:
                self.add_cache_level(
                    name="l4_hybrid",
                    cache_type=CacheType.HYBRID,
                    max_size=l4_config.max_entries,
                    max_memory=l4_config.max_size_mb * 1024 * 1024,
                    policy=CachePolicy.LRU,
                    default_ttl=self._cache_config.get_expiration_time('template_data'),
                    disk_path=str(self.cache_dir / "l4_hybrid")
                )
            
            logger.info("Cache levels configured from ProcessingConfigManager")
            
        except Exception as e:
            logger.error(f"Failed to setup configured cache levels: {e}")
            # Fallback to default configuration
            self._setup_default_levels()
    
    def _setup_default_levels(self):
        """Setup default cache levels"""
        self.add_cache_level(
            name="l1_memory",
            cache_type=CacheType.MEMORY,
            max_size=1000,
            max_memory=50 * 1024 * 1024,  # 50MB
            policy=CachePolicy.LRU,
            default_ttl=3600  # 1 hour
        )
        
        self.add_cache_level(
            name="l2_memory",
            cache_type=CacheType.MEMORY,
            max_size=5000,
            max_memory=200 * 1024 * 1024,  # 200MB
            policy=CachePolicy.LFU,
            default_ttl=7200  # 2 hours
        )
        
        self.add_cache_level(
            name="l3_disk",
            cache_type=CacheType.DISK,
            max_size=50000,
            max_memory=1024 * 1024 * 1024,  # 1GB
            policy=CachePolicy.LRU,
            default_ttl=86400,  # 24 hours
            disk_path=str(self.cache_dir / "l3_disk")
        )
        
        self.add_cache_level(
            name="l4_hybrid",
            cache_type=CacheType.HYBRID,
            max_size=10000,
            max_memory=100 * 1024 * 1024,  # 100MB memory
            policy=CachePolicy.LRU,
            default_ttl=604800,  # 1 week
            disk_path=str(self.cache_dir / "l4_hybrid")
        )
    
    def add_cache_level(self, name: str, cache_type: CacheType, **kwargs):
        """Add a new cache level"""
        if name in self._levels:
            logger.warning(f"Cache level {name} already exists")
            return
        
        self._levels[name] = CacheLevel(name, cache_type, **kwargs)
        logger.info(f"Added cache level: {name} ({cache_type.value})")
    
    def remove_cache_level(self, name: str) -> bool:
        """Remove a cache level"""
        if name in self._levels:
            self._levels[name].clear()
            del self._levels[name]
            logger.info(f"Removed cache level: {name}")
            return True
        return False
    
    def get(self, key: str, cache_type: str = 'default') -> Optional[Any]:
        """Get value from cache, checking levels in order"""
        if cache_type != 'default' and cache_type in self._levels:
            return self._levels[cache_type].get(key)
        
        # Check all levels in order (L1 -> L2 -> L3 -> L4)
        level_order = ['l1_memory', 'l2_memory', 'l3_disk', 'l4_hybrid']
        
        for level_name in level_order:
            if level_name in self._levels:
                value = self._levels[level_name].get(key)
                if value is not None:
                    # Promote to higher level cache (cache warming)
                    self._promote_to_higher_level(key, value, level_name)
                    return value
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            cache_type: str = 'default') -> bool:
        """Set value in cache"""
        if cache_type != 'default' and cache_type in self._levels:
            # Set in specific cache level
            return self._levels[cache_type].set(key, value, ttl)
        
        # Determine best cache level based on value size
        try:
            size = len(pickle.dumps(value))
        except Exception:
            size = len(str(value).encode('utf-8'))
        
        # Choose cache level based on size
        if size < 1024:  # < 1KB -> L1
            target_level = 'l1_memory'
        elif size < 10 * 1024:  # < 10KB -> L2
            target_level = 'l2_memory'
        elif size < 1024 * 1024:  # < 1MB -> L3
            target_level = 'l3_disk'
        else:  # >= 1MB -> L4
            target_level = 'l4_hybrid'
        
        if target_level in self._levels:
            success = self._levels[target_level].set(key, value, ttl)
            if success:
                logger.debug(f"Cached {key} in {target_level} (size: {size} bytes)")
            return success
        
        return False
    
    def delete(self, key: str, cache_type: str = 'all') -> int:
        """Delete key from cache(s)"""
        deleted_count = 0
        
        if cache_type != 'all' and cache_type in self._levels:
            if self._levels[cache_type].delete(key):
                deleted_count = 1
        else:
            for level in self._levels.values():
                if level.delete(key):
                    deleted_count += 1
        
        return deleted_count
    
    def clear(self, cache_type: str = 'all'):
        """Clear cache(s)"""
        if cache_type != 'all' and cache_type in self._levels:
            self._levels[cache_type].clear()
        else:
            for level in self._levels.values():
                level.clear()
        
        logger.info(f"Cleared cache: {cache_type}")
    
    def clear_expired(self) -> int:
        """Clear expired entries from all cache levels"""
        total_removed = 0
        for level in self._levels.values():
            removed = level.cleanup_expired()
            total_removed += removed
        
        if total_removed > 0:
            logger.info(f"Removed {total_removed} expired cache entries")
        
        return total_removed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        stats = {
            'levels': {},
            'total_hits': 0,
            'total_misses': 0,
            'total_entries': 0,
            'total_memory': 0,
            'overall_hit_rate': 0.0
        }
        
        for name, level in self._levels.items():
            level_stats = level.get_stats()
            stats['levels'][name] = level_stats
            stats['total_hits'] += level_stats['hits']
            stats['total_misses'] += level_stats['misses']
            stats['total_entries'] += level_stats['current_size']
            stats['total_memory'] += level_stats['current_memory']
        
        total_requests = stats['total_hits'] + stats['total_misses']
        if total_requests > 0:
            stats['overall_hit_rate'] = stats['total_hits'] / total_requests
        
        return stats
    
    def _promote_to_higher_level(self, key: str, value: Any, current_level: str):
        """Promote frequently accessed items to higher cache levels"""
        level_hierarchy = ['l1_memory', 'l2_memory', 'l3_disk', 'l4_hybrid']
        
        try:
            current_index = level_hierarchy.index(current_level)
            if current_index > 0:  # Can promote
                higher_level = level_hierarchy[current_index - 1]
                if higher_level in self._levels:
                    if self._levels[higher_level].get(key) is None:
                        self._levels[higher_level].set(key, value)
                        logger.debug(f"Promoted {key} from {current_level} to {higher_level}")
        except (ValueError, IndexError):
            pass  # Current level not in hierarchy
    
    def start_cleanup_thread(self):
        """Start background cleanup thread"""
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return
        
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info("Started cache cleanup thread")
    
    def stop_cleanup_thread(self):
        """Stop background cleanup thread"""
        self._running = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        try:
            logger.info("Stopped cache cleanup thread")
        except Exception:
            print("Stopped cache cleanup thread")
    
    def _cleanup_worker(self):
        """Background cleanup worker"""
        while self._running:
            try:
                self.clear_expired()
                time.sleep(self._cleanup_interval)
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def __del__(self):
        """Cleanup on destruction"""
        self.stop_cleanup_thread()

# Global instance
cache_manager = CacheManager()