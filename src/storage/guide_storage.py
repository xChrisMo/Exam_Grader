"""
Storage module for handling parsed marking guides.
"""
import logging
from typing import Dict, Optional, Tuple, List
from .base_storage import BaseStorage

logger = logging.getLogger(__name__)

class GuideStorage(BaseStorage):
    """Handles storage and retrieval of parsed marking guides."""

    def __init__(self):
        super().__init__('guide')

    def store_guide(self, file_content: bytes, filename: str, guide_data: Dict) -> str:
        """
        Store marking guide data.

        Args:
            file_content: Raw bytes of the guide file
            filename: Original filename
            guide_data: Parsed guide data dictionary

        Returns:
            Cache key used to store the guide
        """
        return self.store(file_content, filename, guide_data)

    def get_guide(self, file_content: bytes) -> Optional[Tuple[Dict, str]]:
        """
        Retrieve stored guide if it exists.

        Args:
            file_content: Raw bytes of the guide file

        Returns:
            Tuple of (guide data dict, filename) if found, None if not found
        """
        return self.get(file_content)

    def clear_storage(self):
        """Clear all stored guides (legacy method)."""
        self.clear()

    def clear(self):
        """Clear all stored guides."""
        super().clear()

    def get_storage_stats(self) -> Dict:
        """Get storage statistics."""
        return self.get_stats()

    def get_all_guides(self) -> List[Dict]:
        """
        Get all stored guides.

        Returns:
            List of guide dictionaries with metadata
        """
        guides = []
        try:
            # Get all cache keys
            all_keys = self.cache.get_all_keys()

            # Filter keys that belong to guides (start with our prefix)
            guide_keys = [key for key in all_keys if key.startswith(self.prefix)]

            logger.info(f"Found {len(guide_keys)} guide keys in storage")

            for key in guide_keys:
                try:
                    # Get the cached data
                    cache_data = self.cache.get(key)
                    if cache_data:
                        # Extract guide information
                        guide_info = {
                            'id': key,
                            'name': cache_data.get('filename', 'Unknown'),
                            'filename': cache_data.get('filename', 'Unknown'),
                            'description': f'Stored guide from {cache_data.get("timestamp", "unknown time")}',
                            'raw_content': cache_data.get('data', {}).get('raw_content', ''),
                            'questions': cache_data.get('data', {}).get('questions', []),
                            'total_marks': cache_data.get('data', {}).get('total_marks', 0),
                            'created_at': cache_data.get('timestamp', ''),
                            'created_by': 'Storage',
                            'is_session_guide': False
                        }
                        guides.append(guide_info)
                        logger.debug(f"Added guide: {guide_info['filename']}")
                except Exception as e:
                    logger.warning(f"Failed to process guide key {key}: {str(e)}")
                    continue

            logger.info(f"Successfully loaded {len(guides)} guides from storage")
            return guides

        except Exception as e:
            logger.error(f"Failed to get all guides: {str(e)}")
            return []

    def get_guide_data(self, guide_id: str) -> Optional[Dict]:
        """
        Get specific guide data by ID.

        Args:
            guide_id: The guide ID (cache key)

        Returns:
            Guide data dictionary if found, None otherwise
        """
        try:
            cache_data = self.cache.get(guide_id)
            if cache_data:
                return {
                    'id': guide_id,
                    'name': cache_data.get('filename', 'Unknown'),
                    'filename': cache_data.get('filename', 'Unknown'),
                    'description': f'Stored guide from {cache_data.get("timestamp", "unknown time")}',
                    'raw_content': cache_data.get('data', {}).get('raw_content', ''),
                    'questions': cache_data.get('data', {}).get('questions', []),
                    'total_marks': cache_data.get('data', {}).get('total_marks', 0),
                    'created_at': cache_data.get('timestamp', ''),
                    'created_by': 'Storage',
                    'is_session_guide': False
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get guide data for {guide_id}: {str(e)}")
            return None

    def delete_guide(self, guide_id: str) -> bool:
        """
        Delete a specific guide by ID.

        Args:
            guide_id: The guide ID (cache key) to delete

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            # Check if guide exists
            if self.cache.get(guide_id):
                # Delete from cache
                self.cache.remove(guide_id)
                logger.info(f"Successfully deleted guide: {guide_id}")
                return True
            else:
                logger.warning(f"Guide not found for deletion: {guide_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete guide {guide_id}: {str(e)}")
            return False