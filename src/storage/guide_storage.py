"""
Storage module for handling parsed marking guides.
"""
from typing import Dict, Optional, Tuple
from .base_storage import BaseStorage

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