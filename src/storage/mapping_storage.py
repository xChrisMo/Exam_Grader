"""
Storage service for criteria mapping results.

This module provides functionality to store and retrieve mapping results
between marking guide criteria and student submission content.
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from utils.logger import logger

class MappingStorage:
    """
    Storage service for mapping results.

    This class provides methods to:
    - Store mapping results
    - Retrieve mapping results
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the mapping storage service.

        Args:
            storage_dir: Directory to store mapping results (default: './mappings')
        """
        self.storage_dir = storage_dir or os.path.join(os.getcwd(), 'mappings')

        # Create directory if it doesn't exist
        os.makedirs(self.storage_dir, exist_ok=True)

        logger.info(f"Mapping storage initialized at {self.storage_dir}")

    def _generate_key(self, guide_content: str, submission_content: str) -> str:
        """
        Generate a unique key for a guide-submission pair.

        Args:
            guide_content: Content of the marking guide
            submission_content: Content of the student submission

        Returns:
            str: Unique hash key
        """
        combined = f"{guide_content[:1000]}:::{submission_content[:1000]}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def _generate_filename(self, key: str) -> str:
        """
        Generate a filename for a mapping result.

        Args:
            key: Unique key for the mapping

        Returns:
            str: Generated filename
        """
        return f"mapping_{key}.json"

    def store_result(
        self,
        guide_content: str,
        submission_content: str,
        mapping_result: Dict[str, Any]
    ) -> bool:
        """
        Store a mapping result.

        Args:
            guide_content: Content of the marking guide
            submission_content: Content of the student submission
            mapping_result: Mapping result to store

        Returns:
            bool: True if stored successfully, False otherwise
        """
        try:
            key = self._generate_key(guide_content, submission_content)
            filename = self._generate_filename(key)
            filepath = os.path.join(self.storage_dir, filename)

            # Add key to metadata if not present
            if 'metadata' not in mapping_result:
                mapping_result['metadata'] = {}
            mapping_result['metadata']['key'] = key
            mapping_result['metadata']['timestamp'] = __import__('datetime').datetime.now().isoformat()

            # Write result to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(mapping_result, f, indent=2)

            logger.info(f"Stored mapping result at {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to store mapping result: {str(e)}")
            return False

    def get_result(
        self,
        guide_content: str,
        submission_content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a stored mapping result.

        Args:
            guide_content: Content of the marking guide
            submission_content: Content of the student submission

        Returns:
            Optional[Dict]: Mapping result if found, None otherwise
        """
        try:
            key = self._generate_key(guide_content, submission_content)
            filename = self._generate_filename(key)
            filepath = os.path.join(self.storage_dir, filename)

            if not os.path.exists(filepath):
                logger.info(f"No cached mapping result found for key {key[:8]}...")
                return None

            with open(filepath, 'r', encoding='utf-8') as f:
                mapping_result = json.load(f)
                logger.info(f"Found cached mapping result at {filepath}")
                return mapping_result

        except Exception as e:
            logger.error(f"Error retrieving mapping result: {str(e)}")
            return None

    def clear_all(self) -> bool:
        """
        Clear all stored mapping results (legacy method).

        Returns:
            bool: True if successful, False otherwise
        """
        return self.clear()

    def clear(self) -> bool:
        """
        Clear all stored mapping results.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get all JSON files
            json_files = [f for f in os.listdir(self.storage_dir) if f.endswith('.json')]

            if not json_files:
                logger.info("No mapping results to clear")
                return True

            # Delete each file
            for filename in json_files:
                filepath = os.path.join(self.storage_dir, filename)
                try:
                    os.remove(filepath)
                    logger.info(f"Deleted mapping result file: {filepath}")
                except Exception as e:
                    logger.warning(f"Failed to delete file {filepath}: {str(e)}")

            logger.info(f"Cleared all mapping results")
            return True

        except Exception as e:
            logger.error(f"Error clearing mapping results: {str(e)}")
            return False