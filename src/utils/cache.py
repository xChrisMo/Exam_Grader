import json
import os
import shutil
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from src.config.config_manager import ConfigManager
from src.utils.logger import Logger

logger = Logger().get_logger()

class Cache:
    def __init__(self):
        config = ConfigManager().config
        self.cache_dir = os.path.join(config.temp_dir, 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.default_ttl = timedelta(hours=24)  # Default cache time-to-live
        self.max_cache_size = 100 * 1024 * 1024  # 100MB max cache size
        self.cleanup_threshold = 0.9  # Cleanup when 90% of max size is reached
    
    def _get_cache_path(self, key: str) -> str:
        """Get the cache file path for a given key."""
        return os.path.join(self.cache_dir, f"{key}.json")
    
    def _get_cache_size(self) -> int:
        """Get total size of cache directory in bytes."""
        total_size = 0
        for dirpath, _, filenames in os.walk(self.cache_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size
    
    def _cleanup_cache(self) -> None:
        """Clean up cache by removing oldest files when size threshold is reached."""
        try:
            current_size = self._get_cache_size()
            if current_size < self.max_cache_size * self.cleanup_threshold:
                return
            
            logger.info(f"Cache size ({current_size / 1024 / 1024:.2f}MB) exceeds threshold, starting cleanup")
            
            # Get all cache files with their last access times
            cache_files = []
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.cache_dir, filename)
                    cache_files.append({
                        'path': filepath,
                        'atime': os.path.getatime(filepath)
                    })
            
            # Sort by access time (oldest first)
            cache_files.sort(key=lambda x: x['atime'])
            
            # Remove files until we're below the threshold
            removed_size = 0
            for file_info in cache_files:
                if current_size - removed_size < self.max_cache_size * self.cleanup_threshold:
                    break
                
                file_size = os.path.getsize(file_info['path'])
                os.remove(file_info['path'])
                removed_size += file_size
                logger.info(f"Removed cache file: {os.path.basename(file_info['path'])}")
            
            logger.info(f"Cache cleanup complete. Removed {removed_size / 1024 / 1024:.2f}MB")
        except Exception as e:
            logger.error(f"Error during cache cleanup: {str(e)}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        cache_path = self._get_cache_path(key)
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Check if cache is expired
            cache_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cache_time > self.default_ttl:
                os.remove(cache_path)
                logger.info(f"Removed expired cache entry: {key}")
                return None
            
            # Update last access time
            os.utime(cache_path, None)
            
            return data['value']
        except Exception as e:
            logger.error(f"Error reading cache: {str(e)}")
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the cache."""
        cache_path = self._get_cache_path(key)
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'value': value
            }
            with open(cache_path, 'w') as f:
                json.dump(data, f)
            
            # Check if cleanup is needed
            self._cleanup_cache()
        except Exception as e:
            logger.error(f"Error writing to cache: {str(e)}")
    
    def clear(self) -> None:
        """Clear all cached data."""
        try:
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info("Cache cleared successfully")
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
    
    def remove(self, key: str) -> None:
        """Remove a specific item from the cache."""
        cache_path = self._get_cache_path(key)
        try:
            if os.path.exists(cache_path):
                os.remove(cache_path)
                logger.info(f"Removed cache entry: {key}")
        except Exception as e:
            logger.error(f"Error removing cache item: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            total_size = self._get_cache_size()
            file_count = len([f for f in os.listdir(self.cache_dir) if f.endswith('.json')])
            
            return {
                'total_size_bytes': total_size,
                'total_size_mb': total_size / 1024 / 1024,
                'file_count': file_count,
                'max_size_mb': self.max_cache_size / 1024 / 1024,
                'cleanup_threshold': self.cleanup_threshold
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {} 