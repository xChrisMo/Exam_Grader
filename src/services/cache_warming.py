"""Cache warming service to pre-populate frequently accessed data."""

from src.services.cache_service import app_cache
from src.database.models import User, MarkingGuide, Submission, db
from utils.logger import logger

def warm_user_cache(user_id: int) -> None:
    """Pre-populate cache for a specific user."""
    try:
        # Pre-load user's guides and submissions data
        guides_count = MarkingGuide.query.filter_by(user_id=user_id).count()
        submissions_count = Submission.query.filter_by(user_id=user_id).count()

        # Cache basic stats
        stats_key = f"user_stats_{user_id}"
        stats = {
            "total_guides": guides_count,
            "total_submissions": submissions_count,
        }
        app_cache.set(stats_key, stats, ttl=600)  # 10 minutes

        logger.info(f"Warmed cache for user {user_id}")

    except Exception as e:
        logger.error(f"Error warming cache for user {user_id}: {e}")

def warm_global_cache() -> None:
    """Pre-populate global cache data."""
    try:
        # Cache system stats
        total_users = User.query.count()
        total_guides = MarkingGuide.query.count()
        total_submissions = Submission.query.count()

        system_stats = {
            "total_users": total_users,
            "total_guides": total_guides,
            "total_submissions": total_submissions,
        }

        app_cache.set("system_stats", system_stats, ttl=1800)  # 30 minutes
        logger.info("Warmed global cache")

    except Exception as e:
        logger.error(f"Error warming global cache: {e}")

def cleanup_cache() -> None:
    """Clean up expired cache entries."""
    try:
        app_cache.cleanup_expired()
        logger.info("Cache cleanup completed")
    except Exception as e:
        logger.error(f"Error during cache cleanup: {e}")