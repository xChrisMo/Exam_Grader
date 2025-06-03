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
from .validators import DataValidator, ValidationError, validate_and_sanitize_input

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
        
    def store(self, file_content: bytes, filename: str, data: Dict, data_type: str = 'metadata') -> str:
        """
        Store data in cache with validation.

        Args:
            file_content: Raw bytes of the file
            filename: Original filename
            data: Data to store
            data_type: Type of data for validation ('guide', 'submission', 'results', 'metadata')

        Returns:
            Cache key used to store the data

        Raises:
            ValidationError: If data validation fails
        """
        try:
            # Validate file content
            DataValidator.validate_file_content(file_content)

            # Validate filename
            DataValidator.validate_filename(filename)

            # Validate and sanitize data
            validated_data = validate_and_sanitize_input(data, data_type)

            key = self._generate_key(file_content)
            cache_data = {
                'filename': filename,
                'data': validated_data,
                'timestamp': datetime.now().isoformat(),
                'data_type': data_type,
                'file_size': len(file_content)
            }

            # Final validation of cache data
            DataValidator.validate_json_data(cache_data)

            self.cache.set(key, cache_data)
            logger.debug(f"Stored validated data in cache with key: {key}")
            return key

        except ValidationError:
            logger.error(f"Validation failed for data storage")
            raise
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

    def get_by_id(self, storage_id: str) -> Optional[Dict]:
        """
        Retrieve data by storage ID.

        Args:
            storage_id: The storage ID (cache key)

        Returns:
            Stored data if found, None otherwise
        """
        try:
            cache_data = self.cache.get(storage_id)
            if cache_data:
                logger.debug(f"Retrieved data by ID: {storage_id}")
                return cache_data
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve data by ID {storage_id}: {str(e)}")
            return None

    def remove_by_id(self, storage_id: str) -> bool:
        """
        Remove data by storage ID.

        Args:
            storage_id: The storage ID (cache key)

        Returns:
            True if removed successfully, False otherwise
        """
        try:
            # Check if data exists
            if self.cache.get(storage_id):
                self.cache.remove(storage_id)
                logger.debug(f"Removed data by ID: {storage_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove data by ID {storage_id}: {str(e)}")
            return False
            
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
        """Check if the storage is available by testing cache operations."""
        try:
            # Test if we can perform basic cache operations
            test_key = f"{self.prefix}_availability_test"
            test_data = {'test': True, 'timestamp': datetime.now().isoformat()}

            # Try to write and read a test value
            self.cache.set(test_key, test_data)
            retrieved_data = self.cache.get(test_key)

            # Clean up test data
            self.cache.remove(test_key)

            # Return True if we successfully wrote and read the test data
            return retrieved_data is not None and retrieved_data.get('test') is True

        except Exception as e:
            logger.error(f"Error checking storage availability for {self.prefix}: {str(e)}")
            return False

    def has_data(self) -> bool:
        """Check if there's any data stored with this prefix."""
        try:
            all_keys = self.cache.get_all_keys()
            return any(key.startswith(self.prefix) for key in all_keys)
        except Exception as e:
            logger.error(f"Error checking for data with prefix {self.prefix}: {str(e)}")
            return False