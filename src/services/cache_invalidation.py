"""Cache invalidation utilities for maintaining data consistency."""

from src.services.cache_service import app_cache
from utils.cache import get_cache
from utils.logger import logger

def invalidate_user_cache(user_id: int, cache_types: list = None) -> None:
    """
    Invalidate all cache entries for a specific user.

    Args:
        user_id: The user ID whose cache should be invalidated
        cache_types: List of cache types to invalidate. If None, invalidates all types.
                    Options: ['guides', 'submissions', 'stats', 'dashboard']
    """
    if cache_types is None:
        cache_types = ['guides', 'submissions', 'stats', 'dashboard']

    cache_keys_to_clear = []

    try:
        # Clear guides cache
        if 'guides' in cache_types:
            for page in range(1, 21):  # Clear first 20 pages
                cache_keys_to_clear.append(f"guides_{user_id}_{page}")

        # Clear submissions cache
        if 'submissions' in cache_types:
            for page in range(1, 21):  # Clear first 20 pages
                cache_keys_to_clear.append(f"submissions_{user_id}_true_{page}")
                cache_keys_to_clear.append(f"submissions_{user_id}_false_{page}")

        # Clear user stats cache
        if 'stats' in cache_types:
            cache_keys_to_clear.append(f"user_stats_{user_id}")

        # Clear dashboard cache (if we add it later)
        if 'dashboard' in cache_types:
            cache_keys_to_clear.append(f"dashboard_{user_id}")

        # Clear all specified cache keys
        cleared_count = 0
        for key in cache_keys_to_clear:
            app_cache.delete(key)
            cleared_count += 1

        logger.info(f"Invalidated {cleared_count} cache entries for user {user_id}")

    except Exception as e:
        logger.error(f"Error invalidating cache for user {user_id}: {e}")

def invalidate_guide_cache(user_id: int) -> None:
    """Invalidate cache entries related to guides."""
    invalidate_user_cache(user_id, ['guides', 'submissions', 'stats'])

def invalidate_submission_cache(user_id: int, submission_id: str = None) -> None:
    """Invalidate cache entries related to submissions."""
    invalidate_user_cache(user_id, ['submissions', 'stats'])
    
    # If specific submission_id is provided, also clear individual submission caches
    if submission_id:
        try:
            # Clear app cache entries that might contain this submission
            app_cache_keys = [
                f"submission_{submission_id}",
                f"submission_details_{submission_id}",
                f"submission_content_{submission_id}",
            ]
            
            # Clear global cache entries
            global_cache = get_cache()
            global_cache_keys = [
                f"submission_{submission_id}",
                f"submission_details_{submission_id}",
                f"submission_content_{submission_id}",
            ]
            
            cleared_count = 0
            
            # Clear app cache
            for key in app_cache_keys:
                app_cache.delete(key)
                cleared_count += 1
            
            # Clear global cache
            for key in global_cache_keys:
                global_cache.delete(key)
                cleared_count += 1
            
            logger.debug(f"Cleared {cleared_count} individual cache entries for submission {submission_id}")
            
        except Exception as e:
            logger.error(f"Error clearing individual submission cache for {submission_id}: {e}")

def invalidate_all_cache() -> None:
    """Clear all cache entries (use with caution)."""
    try:
        app_cache.clear()
        logger.info("All cache entries cleared")
    except Exception as e:
        logger.error(f"Error clearing all cache: {e}")