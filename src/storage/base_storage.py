"""
Base storage implementation using the cache utility.
"""
from typing import Dict, Optional, Tuple, Any
import os
import json
from datetime import datetime, timedelta
import hashlib
from utils.cache import Cache
from utils.logger import Logger

logger = Logger().get_logger()

class BaseStorage:
    """Base class for storage implementations using cache utility."""
    
    def __init__(self, cache_prefix: str):
        """
        Initialize storage with a cache prefix.
        
        Args:
            cache_prefix: Prefix for cache keys to avoid collisions
        """
        self.cache = Cache()
        self.prefix = cache_prefix
        logger.debug(f"Initialized storage with prefix: {cache_prefix}")
        
    def _generate_key(self, file_content: bytes) -> str:
        """Generate a unique key for the content."""
        file_hash = hashlib.sha256(file_content).hexdigest()
        return f"{self.prefix}_{file_hash}"
        
    def store(self, file_content: bytes, filename: str, data: Dict) -> str:
        """
        Store data in cache.
        
        Args:
            file_content: Raw bytes of the file
            filename: Original filename
            data: Data to store
            
        Returns:
            Cache key used to store the data
        """
        key = self._generate_key(file_content)
        cache_data = {
            'filename': filename,
            'data': data,
            'timestamp': datetime.now().isoformat()  # Store timestamp for age calculation
        }
        
        try:
            self.cache.set(key, cache_data)
            logger.debug(f"Stored data in cache with key: {key}")
            return key
        except Exception as e:
            logger.error(f"Failed to store data: {str(e)}")
            raise
            
    def get(self, file_content: bytes) -> Optional[Tuple[Dict, str]]:
        """
        Retrieve data from cache.
        
        Args:
            file_content: Raw bytes of the file
            
        Returns:
            Tuple of (stored data dict, filename) if found, None if not found
        """
        key = self._generate_key(file_content)
        try:
            cache_data = self.cache.get(key)
            if cache_data:
                logger.debug(f"Retrieved data from cache with key: {key}")
                return cache_data['data'], cache_data['filename']
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve data: {str(e)}")
            return None
            
    def remove(self, file_content: bytes) -> None:
        """
        Remove data from cache.
        
        Args:
            file_content: Raw bytes of the file
        """
        key = self._generate_key(file_content)
        try:
            self.cache.remove(key)
            logger.debug(f"Removed data from cache with key: {key}")
        except Exception as e:
            logger.error(f"Failed to remove data: {str(e)}")
            
    def clear(self) -> None:
        """Clear all cached data."""
        try:
            self.cache.clear()
            logger.debug("Cleared all cached data")
        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics with file age information."""
        try:
            stats = self.cache.get_stats()
            
            # Get file ages
            now = datetime.now()
            newest_age = float('inf')
            oldest_age = 0
            
            # Scan cache directory for files with our prefix
            cache_dir = self.cache.cache_dir
            for filename in os.listdir(cache_dir):
                if filename.startswith(self.prefix) and filename.endswith('.json'):
                    filepath = os.path.join(cache_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            data = json.loads(f.read())
                            if 'timestamp' in data:
                                file_time = datetime.fromisoformat(data['timestamp'])
                                age_days = (now - file_time).total_seconds() / (24 * 3600)
                                newest_age = min(newest_age, age_days)
                                oldest_age = max(oldest_age, age_days)
                    except (OSError, FileNotFoundError) as e:
                        logger.warning(f"Failed to access cache file {filename}: {str(e)}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse cache file {filename}: {str(e)}")
                    except ValueError as e:
                        logger.warning(f"Invalid timestamp format in cache file {filename}: {str(e)}")
            
            # Add file age information to stats
            stats['newest_file_days'] = newest_age if newest_age != float('inf') else 0
            stats['oldest_file_days'] = oldest_age
            
            return stats
        except (OSError, FileNotFoundError) as e:
            logger.error(f"Failed to access cache directory: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'file_count': 0,
                'max_size_mb': 100,
                'cleanup_threshold': 0.9,
                'newest_file_days': 0,
                'oldest_file_days': 0
            }

    def is_available(self) -> bool:
        """Check if the storage is available by checking if there's any data for this prefix."""
        try:
            # This is a simplified check. A more robust check might involve
            # trying to list keys or checking a specific 'heartbeat' key.
            # For now, we assume if the cache is operational, it's 'available'.
            # To check if there's *any* data, we might need a method in Cache
            # to check for keys by prefix or just check if the cache is not empty.
            # Assuming cache.get_all_keys() returns keys, we can check for prefix.
            all_keys = self.cache.get_all_keys()
            for key in all_keys:
                if key.startswith(self.prefix):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking storage availability for {self.prefix}: {str(e)}")
            return False