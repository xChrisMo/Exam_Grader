"""Simple cache implementation for the Exam Grader application."""
import os
import json
import hashlib
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime
from utils.logger import setup_logger

# Set up logger for this module
logger = setup_logger(__name__)

class Cache:
    """Simple file-based cache implementation."""
    
    def __init__(self, cache_dir: str = "temp/cache"):
        """Initialize cache with directory."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Hash the key to create a safe filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache."""
        cache_path = self._get_cache_path(key)
        cache_data = {
            'key': key,
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
        except (OSError, IOError) as e:
            # Log error but continue operation
            logger.warning(f"Failed to write to cache file {cache_path}: {str(e)}")
        except TypeError as e:
            # Log error for non-serializable data
            logger.warning(f"Failed to serialize cache data: {str(e)}")
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from the cache."""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                return cache_data.get('value')
        except (OSError, IOError) as e:
            # Log error but continue operation
            logger.warning(f"Failed to read cache file {cache_path}: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            # Log error for invalid JSON
            logger.warning(f"Failed to parse cache file {cache_path}: {str(e)}")
            return None
    
    def remove(self, key: str) -> None:
        """Remove a value from the cache."""
        with self._lock:
            cache_path = self._get_cache_path(key)

            # Remove from memory cache
            if key in self._memory_cache:
                del self._memory_cache[key]
                del self._access_times[key]

            # Remove from disk cache
            try:
                if cache_path.exists():
                    cache_path.unlink()
                    logger.debug(f"Removed cache entry for key: {key}")
            except (OSError, IOError) as e:
                logger.warning(f"Failed to remove cache file {cache_path}: {str(e)}")
    
    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            # Clear memory cache
            self._memory_cache.clear()
            self._access_times.clear()

            # Clear disk cache
            try:
                for cache_file in self.cache_dir.glob("*.json"):
                    try:
                        cache_file.unlink()
                    except (OSError, IOError) as e:
                        logger.warning(f"Failed to remove cache file {cache_file}: {str(e)}")
                logger.info("Cache cleared successfully")
            except (OSError, IOError) as e:
                logger.warning(f"Failed to access cache directory {self.cache_dir}: {str(e)}")
    
    def get_all_keys(self) -> list[str]:
        """Get all keys currently in the cache."""
        keys = []
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                        if 'key' in cache_data:
                            keys.append(cache_data['key'])
                except (OSError, IOError, json.JSONDecodeError) as e:
                    logger.warning(f"Failed to read or parse cache file {cache_file}: {str(e)}")
        except (OSError, IOError) as e:
            logger.warning(f"Failed to access cache directory {self.cache_dir}: {str(e)}")
        return keys

    def get_stats(self) -> Dict[str, Any]:
        """Get enhanced cache statistics."""
        with self._lock:
            try:
                cache_files = list(self.cache_dir.glob("*.json"))
                total_size = sum(f.stat().st_size for f in cache_files)

                # Count expired entries
                expired_count = 0
                for cache_file in cache_files:
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                        if 'timestamp' in cache_data and self._is_expired(cache_data['timestamp']):
                            expired_count += 1
                    except (OSError, IOError, json.JSONDecodeError):
                        expired_count += 1  # Count corrupted files as expired

                return {
                    'total_size_bytes': total_size,
                    'total_size_mb': round(total_size / (1024 * 1024), 2),
                    'max_size_mb': round(self.max_size_bytes / (1024 * 1024), 2),
                    'file_count': len(cache_files),
                    'expired_count': expired_count,
                    'memory_cache_size': len(self._memory_cache),
                    'memory_cache_max_size': self._memory_cache_max_size,
                    'ttl_hours': round(self.ttl_seconds / 3600, 2),
                    'usage_percentage': round((total_size / self.max_size_bytes) * 100, 2) if self.max_size_bytes > 0 else 0
                }
            except (OSError, IOError) as e:
                logger.warning(f"Failed to get cache stats: {str(e)}")
                return {
                    'total_size_bytes': 0,
                    'total_size_mb': 0,
                    'max_size_mb': round(self.max_size_bytes / (1024 * 1024), 2),
                    'file_count': 0,
                    'expired_count': 0,
                    'memory_cache_size': 0,
                    'memory_cache_max_size': self._memory_cache_max_size,
                    'ttl_hours': round(self.ttl_seconds / 3600, 2),
                    'usage_percentage': 0
                }

    def cleanup(self) -> Dict[str, int]:
        """Manually trigger cache cleanup and return statistics."""
        with self._lock:
            expired_removed = self._cleanup_expired_entries()
            size_removed = self._enforce_size_limit()

            return {
                'expired_removed': expired_removed,
                'size_limit_removed': size_removed,
                'total_removed': expired_removed + size_removed
            }

    def warm_cache(self, keys: List[str]) -> int:
        """Pre-load specified keys into memory cache."""
        loaded_count = 0
        with self._lock:
            for key in keys:
                if key not in self._memory_cache:
                    value = self.get(key)  # This will load into memory cache
                    if value is not None:
                        loaded_count += 1

        logger.debug(f"Warmed cache with {loaded_count} entries")
        return loaded_count
