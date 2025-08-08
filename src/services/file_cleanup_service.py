"""
File Cleanup Service for Exam Grader Application.

Provides automated cleanup of temporary files, old uploads, and orphaned files.
"""

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from utils.logger import logger


@dataclass
class CleanupStats:
    """Statistics for cleanup operations."""

    files_scanned: int = 0
    files_deleted: int = 0
    bytes_freed: int = 0
    errors: int = 0
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "files_scanned": self.files_scanned,
            "files_deleted": self.files_deleted,
            "bytes_freed": self.bytes_freed,
            "bytes_freed_mb": round(self.bytes_freed / (1024 * 1024), 2),
            "errors": self.errors,
            "duration_seconds": round(self.duration_seconds, 2),
        }


class FileCleanupService:
    """
    Service for automated file cleanup and maintenance.

    Features:
    - Cleanup temporary files
    - Remove old uploads
    - Delete orphaned files
    - Scheduled cleanup tasks
    - Configurable retention policies
    """

    def __init__(self, config):
        """
        Initialize file cleanup service.

        Args:
            config: Application configuration
        """
        self.config = config
        self.temp_dir = Path(config.files.temp_dir)
        self.upload_dir = Path(config.files.upload_dir)
        self.output_dir = Path(config.files.output_dir)

        # Cleanup policies
        self.temp_file_max_age_hours = 24  # 24 hours for temp files
        self.upload_file_max_age_days = config.files.storage_expiration_days
        self.orphaned_file_max_age_hours = 48  # 48 hours for orphaned files

        # Cleanup thread
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        self._cleanup_interval = (
            config.files.cleanup_interval_hours * 3600
        )  # Convert to seconds

    def start_scheduled_cleanup(self):
        """Start scheduled cleanup in background thread."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            logger.warning("Cleanup thread already running")
            return

        self._stop_cleanup.clear()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker, name="FileCleanupWorker", daemon=True
        )
        self._cleanup_thread.start()
        logger.info(
            f"Started scheduled file cleanup (interval: {self._cleanup_interval}s)"
        )

    def stop_scheduled_cleanup(self):
        """Stop scheduled cleanup."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=30)
            logger.info("Stopped scheduled file cleanup")

    def stop(self):
        """Stop the file cleanup service (alias for stop_scheduled_cleanup)."""
        self.stop_scheduled_cleanup()

    def _cleanup_worker(self):
        """Background worker for scheduled cleanup."""
        while not self._stop_cleanup.is_set():
            try:
                # Perform cleanup
                stats = self.cleanup_all()

                if stats.files_deleted > 0:
                    logger.info(
                        f"Scheduled cleanup completed: {stats.files_deleted} files deleted, "
                        f"{stats.bytes_freed_mb}MB freed"
                    )

            except Exception as e:
                logger.error(f"Error in scheduled cleanup: {str(e)}")

            self._stop_cleanup.wait(self._cleanup_interval)

    def cleanup_all(self) -> CleanupStats:
        """
        Perform comprehensive cleanup of all file types.

        Returns:
            Cleanup statistics
        """
        start_time = time.time()
        total_stats = CleanupStats()

        logger.info("Starting comprehensive file cleanup")

        # Cleanup temporary files
        temp_stats = self.cleanup_temp_files()
        total_stats.files_scanned += temp_stats.files_scanned
        total_stats.files_deleted += temp_stats.files_deleted
        total_stats.bytes_freed += temp_stats.bytes_freed
        total_stats.errors += temp_stats.errors

        # Cleanup old uploads
        upload_stats = self.cleanup_old_uploads()
        total_stats.files_scanned += upload_stats.files_scanned
        total_stats.files_deleted += upload_stats.files_deleted
        total_stats.bytes_freed += upload_stats.bytes_freed
        total_stats.errors += upload_stats.errors

        # Cleanup orphaned files
        orphan_stats = self.cleanup_orphaned_files()
        total_stats.files_scanned += orphan_stats.files_scanned
        total_stats.files_deleted += orphan_stats.files_deleted
        total_stats.bytes_freed += orphan_stats.bytes_freed
        total_stats.errors += orphan_stats.errors

        total_stats.duration_seconds = time.time() - start_time

        if total_stats.files_deleted > 0 or total_stats.errors > 0:
            logger.info(
                f"Cleanup completed: {total_stats.files_deleted} files deleted, "
                f"{total_stats.bytes_freed_mb:.1f}MB freed"
                f"{', ' + str(total_stats.errors) + ' errors' if total_stats.errors > 0 else ''}"
            )
        else:
            logger.debug(
                f"Cleanup completed: no files to clean (scanned {total_stats.files_scanned} files)"
            )

        return total_stats

    def cleanup_temp_files(self) -> CleanupStats:
        """
        Clean up temporary files older than configured age.

        Returns:
            Cleanup statistics
        """
        stats = CleanupStats()
        cutoff_time = datetime.now() - timedelta(hours=self.temp_file_max_age_hours)

        logger.info(
            f"Cleaning up temp files older than {self.temp_file_max_age_hours} hours"
        )

        if not self.temp_dir.exists():
            return stats

        try:
            for file_path in self.temp_dir.rglob("*"):
                if file_path.is_file():
                    stats.files_scanned += 1

                    try:
                        # Check file age
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                        if file_mtime < cutoff_time:
                            file_size = file_path.stat().st_size
                            file_path.unlink()

                            stats.files_deleted += 1
                            stats.bytes_freed += file_size

                            logger.debug(f"Deleted temp file: {file_path}")

                    except Exception as e:
                        stats.errors += 1
                        logger.warning(
                            f"Failed to delete temp file {file_path}: {str(e)}"
                        )

            # Remove empty directories
            self._remove_empty_directories(self.temp_dir)

        except Exception as e:
            logger.error(f"Error during temp file cleanup: {str(e)}")
            stats.errors += 1

        logger.info(
            f"Temp file cleanup: {stats.files_deleted} files deleted, "
            f"{stats.bytes_freed / (1024*1024):.2f}MB freed"
        )
        return stats

    def cleanup_old_uploads(self) -> CleanupStats:
        """
        Clean up old upload files based on database records.

        Returns:
            Cleanup statistics
        """
        stats = CleanupStats()
        cutoff_date = datetime.now(timezone.utc) - timedelta(
            days=self.upload_file_max_age_days
        )

        logger.info(
            f"Cleaning up uploads older than {self.upload_file_max_age_days} days"
        )

        try:
            # Import here to avoid circular imports
            from src.database.models import MarkingGuide, Submission, db

            try:
                from flask import has_app_context

                if not has_app_context():
                    logger.warning(
                        "No Flask app context available, skipping database cleanup"
                    )
                    return stats
            except ImportError:
                logger.warning("Flask not available, skipping database cleanup")
                return stats

            # Find old submissions
            old_submissions = Submission.query.filter(
                Submission.created_at < cutoff_date
            ).all()

            for submission in old_submissions:
                stats.files_scanned += 1

                if submission.file_path and Path(submission.file_path).exists():
                    try:
                        file_path = Path(submission.file_path)
                        file_size = file_path.stat().st_size
                        file_path.unlink()

                        # Clear file path in database but keep metadata
                        submission.file_path = ""

                        stats.files_deleted += 1
                        stats.bytes_freed += file_size

                        logger.debug(f"Deleted old submission file: {file_path}")

                    except Exception as e:
                        stats.errors += 1
                        logger.warning(
                            f"Failed to delete submission file {submission.file_path}: {str(e)}"
                        )

            # Find old marking guides
            old_guides = MarkingGuide.query.filter(
                MarkingGuide.created_at < cutoff_date, MarkingGuide.is_active == False
            ).all()

            for guide in old_guides:
                stats.files_scanned += 1

                if guide.file_path and Path(guide.file_path).exists():
                    try:
                        file_path = Path(guide.file_path)
                        file_size = file_path.stat().st_size
                        file_path.unlink()

                        # Clear file path in database but keep metadata
                        guide.file_path = ""

                        stats.files_deleted += 1
                        stats.bytes_freed += file_size

                        logger.debug(f"Deleted old guide file: {file_path}")

                    except Exception as e:
                        stats.errors += 1
                        logger.warning(
                            f"Failed to delete guide file {guide.file_path}: {str(e)}"
                        )

            db.session.commit()

        except Exception as e:
            logger.error(f"Error during old uploads cleanup: {str(e)}")
            db.session.rollback()
            stats.errors += 1

        logger.info(
            f"Old uploads cleanup: {stats.files_deleted} files deleted, "
            f"{stats.bytes_freed / (1024*1024):.2f}MB freed"
        )
        return stats

    def cleanup_orphaned_files(self) -> CleanupStats:
        """
        Clean up files that exist on disk but not in database.

        Returns:
            Cleanup statistics
        """
        stats = CleanupStats()
        cutoff_time = datetime.now() - timedelta(hours=self.orphaned_file_max_age_hours)

        logger.info(
            f"Cleaning up orphaned files older than {self.orphaned_file_max_age_hours} hours"
        )

        try:
            # Import here to avoid circular imports
            from src.database.models import MarkingGuide, Submission

            try:
                from flask import has_app_context

                if not has_app_context():
                    logger.warning(
                        "No Flask app context available, skipping orphaned files cleanup"
                    )
                    return stats
            except ImportError:
                logger.warning("Flask not available, skipping orphaned files cleanup")
                return stats

            db_file_paths = set()

            # Submission files
            submissions = Submission.query.filter(
                Submission.file_path.isnot(None)
            ).all()
            for submission in submissions:
                if submission.file_path:
                    db_file_paths.add(Path(submission.file_path).resolve())

            # Guide files
            guides = MarkingGuide.query.filter(MarkingGuide.file_path.isnot(None)).all()
            for guide in guides:
                if guide.file_path:
                    db_file_paths.add(Path(guide.file_path).resolve())

            for directory in [self.upload_dir, self.output_dir]:
                if not directory.exists():
                    continue

                for file_path in directory.rglob("*"):
                    if file_path.is_file():
                        stats.files_scanned += 1

                        try:
                            if file_path.resolve() not in db_file_paths:
                                # Check file age
                                file_mtime = datetime.fromtimestamp(
                                    file_path.stat().st_mtime
                                )

                                if file_mtime < cutoff_time:
                                    file_size = file_path.stat().st_size
                                    file_path.unlink()

                                    stats.files_deleted += 1
                                    stats.bytes_freed += file_size

                                    logger.debug(f"Deleted orphaned file: {file_path}")

                        except Exception as e:
                            stats.errors += 1
                            logger.warning(
                                f"Failed to process file {file_path}: {str(e)}"
                            )

            # Remove empty directories
            for directory in [self.upload_dir, self.output_dir]:
                if directory.exists():
                    self._remove_empty_directories(directory)

        except Exception as e:
            logger.error(f"Error during orphaned files cleanup: {str(e)}")
            stats.errors += 1

        logger.info(
            f"Orphaned files cleanup: {stats.files_deleted} files deleted, "
            f"{stats.bytes_freed / (1024*1024):.2f}MB freed"
        )
        return stats

    def _remove_empty_directories(self, root_dir: Path):
        """Remove empty directories recursively."""
        try:
            for dir_path in sorted(root_dir.rglob("*"), reverse=True):
                if dir_path.is_dir() and dir_path != root_dir:
                    try:
                        if not any(dir_path.iterdir()):  # Directory is empty
                            dir_path.rmdir()
                            logger.debug(f"Removed empty directory: {dir_path}")
                    except OSError:
                        # Directory not empty or permission error
                        pass
        except Exception as e:
            logger.warning(f"Error removing empty directories: {str(e)}")

    def get_disk_usage(self) -> Dict[str, Dict[str, Any]]:
        """
        Get disk usage statistics for managed directories.

        Returns:
            Dictionary with usage statistics
        """
        usage_stats = {}

        for name, directory in [
            ("temp", self.temp_dir),
            ("uploads", self.upload_dir),
            ("output", self.output_dir),
        ]:
            if directory.exists():
                total_size = 0
                file_count = 0

                try:
                    for file_path in directory.rglob("*"):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
                            file_count += 1

                    usage_stats[name] = {
                        "path": str(directory),
                        "file_count": file_count,
                        "total_bytes": total_size,
                        "total_mb": round(total_size / (1024 * 1024), 2),
                        "exists": True,
                    }

                except Exception as e:
                    usage_stats[name] = {
                        "path": str(directory),
                        "error": str(e),
                        "exists": True,
                    }
            else:
                usage_stats[name] = {"path": str(directory), "exists": False}

        return usage_stats

    def force_cleanup_file(self, file_path: str) -> bool:
        """
        Force cleanup of a specific file.

        Args:
            file_path: Path to file to delete

        Returns:
            True if successful
        """
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                logger.info(f"Force deleted file: {file_path}")
                return True
            else:
                logger.warning(f"File not found or not a file: {file_path}")
                return False

        except Exception as e:
            logger.error(f"Failed to force delete file {file_path}: {str(e)}")
            return False
