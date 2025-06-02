"""Storage module for handling parsed submission results."""
import json
import os
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
import hashlib
from datetime import datetime
from utils.logger import setup_logger

# Set up logger for this module
logger = setup_logger(__name__)

class SubmissionStorage:
    """Handles storage and retrieval of parsed submission results."""

    def __init__(self, storage_dir: str = 'output/submissions',
                 max_storage_mb: int = 500,
                 expiration_days: int = 30):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_storage_bytes = max_storage_mb * 1024 * 1024  # Convert MB to bytes
        self.expiration_seconds = expiration_days * 24 * 60 * 60  # Convert days to seconds

    def _generate_file_hash(self, file_content: bytes) -> str:
        """Generate a unique hash for the file content."""
        return hashlib.sha256(file_content).hexdigest()

    def _get_storage_size(self) -> int:
        """Get total size of stored results in bytes."""
        total_size = 0
        for file in self.storage_dir.glob('*.json'):
            try:
                total_size += os.path.getsize(file)
            except (OSError, FileNotFoundError) as e:
                logger.warning(f"Error getting size of {file}: {str(e)}")
        return total_size

    def _cleanup_old_files(self, required_space: int = 0):
        """
        Remove expired files and ensure enough storage space.

        Args:
            required_space: Additional space needed in bytes
        """
        current_time = time.time()
        files_info = []

        # Collect file information
        for file in self.storage_dir.glob('*.json'):
            try:
                mtime = os.path.getmtime(file)
                size = os.path.getsize(file)
                files_info.append((file, mtime, size))
            except (OSError, FileNotFoundError) as e:
                logger.warning(f"Error accessing file {file}: {str(e)}")
                continue

        # Sort by modification time (oldest first)
        files_info.sort(key=lambda x: x[1])

        # Remove expired files
        for file, mtime, _ in files_info[:]:
            if current_time - mtime > self.expiration_seconds:
                try:
                    os.remove(file)
                    files_info.remove((file, mtime, _))
                    logger.info(f"Removed expired file: {file}")
                except (OSError, FileNotFoundError) as e:
                    logger.warning(f"Error removing expired file {file}: {str(e)}")

        # If we still need space, remove oldest files
        current_size = sum(size for _, _, size in files_info)
        needed_space = current_size + required_space - self.max_storage_bytes

        if needed_space > 0:
            for file, _, size in files_info:
                try:
                    os.remove(file)
                    needed_space -= size
                    if needed_space <= 0:
                        break
                except Exception:
                    pass

    def store_results(self, file_content: bytes, filename: str, results: Dict,
                     raw_text: str) -> str:
        """
        Store submission results.

        Args:
            file_content: Raw bytes of the submitted file
            filename: Original filename
            results: Parsed results dictionary
            raw_text: Raw extracted text

        Returns:
            File hash that can be used to retrieve results
        """
        file_hash = self._generate_file_hash(file_content)

        data = {
            'filename': filename,
            'results': results,
            'raw_text': raw_text,
            'timestamp': time.time()
        }

        # Convert to JSON string to check size
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        data_size = len(json_data.encode('utf-8'))

        # Clean up if needed
        self._cleanup_old_files(data_size)

        # Check if we can store the new file
        if data_size > self.max_storage_bytes:
            raise ValueError(f"Result size ({data_size} bytes) exceeds maximum storage limit")

        # Store the results
        output_file = self.storage_dir / f"{file_hash}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_data)

        return file_hash

    def get_results(self, file_content: bytes) -> Optional[Tuple[Dict, str, str]]:
        """
        Retrieve stored results for a file if they exist.

        Args:
            file_content: Raw bytes of the submitted file

        Returns:
            Tuple of (results dict, raw text, filename) if found, None if not found
        """
        file_hash = self._generate_file_hash(file_content)
        result_file = self.storage_dir / f"{file_hash}.json"

        if not result_file.exists():
            return None

        try:
            current_time = time.time()

            with open(result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if result has expired
            if current_time - data.get('timestamp', 0) > self.expiration_seconds:
                try:
                    os.remove(result_file)
                    logger.info(f"Removed expired result file: {result_file}")
                except (OSError, FileNotFoundError) as e:
                    logger.warning(f"Error removing expired result file {result_file}: {str(e)}")
                return None

            return data['results'], data['raw_text'], data['filename']

        except (json.JSONDecodeError, OSError, FileNotFoundError) as e:
            logger.error(f"Error retrieving submission results: {str(e)}")
            return None

    def clear_storage(self):
        """Clear all stored results (legacy method)."""
        self.clear()

    def clear(self):
        """Clear all stored results."""
        for file in self.storage_dir.glob('*.json'):
            try:
                os.remove(file)
                logger.info(f"Removed file during storage clear: {file}")
            except (OSError, FileNotFoundError) as e:
                logger.warning(f"Error removing file during clear {file}: {str(e)}")

    def get_storage_stats(self) -> Dict:
        """Get storage statistics."""
        stats = {
            'total_size_mb': 0,
            'file_count': 0,
            'max_size_mb': self.max_storage_bytes / (1024 * 1024),
            'expiration_days': self.expiration_seconds / (24 * 60 * 60)
        }

        current_time = time.time()
        for file in self.storage_dir.glob('*.json'):
            try:
               
                stats['file_count'] += 1
                stats['total_size_mb'] += os.path.getsize(file) / (1024 * 1024)

                # Check age of oldest and newest files
                mtime = os.path.getmtime(file)
                age_days = (current_time - mtime) / (24 * 60 * 60)

                if 'oldest_file_days' not in stats or age_days > stats['oldest_file_days']:
                    stats['oldest_file_days'] = age_days
                if 'newest_file_days' not in stats or age_days < stats['newest_file_days']:
                    stats['newest_file_days'] = age_days

                return stats
            except Exception as e:
                logger.warning(f"Error getting storage stats: {str(e)}")
                continue

    def is_available(self) -> bool:
        """Check if the storage is available by attempting to write and delete a dummy file."""
        try:
            # Attempt to create a dummy file
            dummy_file_path = self.storage_dir / ".availability_test"
            with open(dummy_file_path, 'w') as f:
                f.write("test")
            os.remove(dummy_file_path)
            return True
        except Exception as e:
            logger.error(f"SubmissionStorage is not available: {e}")
            return False

    def get_latest_submission(self) -> Optional[Dict]:
        """
        Get the most recent submission from storage.

        Returns:
            Dictionary containing submission details if found, None otherwise
        """
        current_time = time.time()
        latest_submission = None
        latest_timestamp = 0

        for file in self.storage_dir.glob('*.json'):
            try:
                mtime = os.path.getmtime(file)
                if mtime > latest_timestamp:
                    latest_timestamp = mtime

                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Check if result has expired
                    if current_time - data.get('timestamp', 0) <= self.expiration_seconds:
                        latest_submission = {
                            'filename': data['filename'],
                            'content': data['raw_text'],
                            'results': data['results'],
                            'upload_time': datetime.fromtimestamp(data['timestamp']),
                            'file_size': os.path.getsize(file)
                        }

            except Exception as e:
                logger.warning(f"Error processing file {file}: {str(e)}")
                continue

        return latest_submission