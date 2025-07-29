"""Guide verification utilities to prevent concurrent processing."""

from datetime import datetime, timedelta
from typing import Optional
from utils.logger import logger

def is_guide_in_use(guide_id) -> bool:
    """
    Check if a marking guide is currently being used for processing.
    
    Args:
        guide_id: ID of the marking guide to check (can be string or int)
        
    Returns:
        bool: True if guide is currently in use, False otherwise
    """
    try:
        # Import here to avoid circular imports
        from src.database.models import Submission, GradingResult
        
        active_submissions = Submission.query.filter(
            Submission.marking_guide_id == guide_id,
            Submission.processing_status.in_(['processing', 'pending'])
        ).count()
        
        if active_submissions > 0:
            logger.warning(f"Guide {guide_id} is currently in use by {active_submissions} active submissions")
            return True
            
        # This indicates recent processing activity
        recent_threshold = datetime.utcnow() - timedelta(minutes=5)
        recent_results = GradingResult.query.filter(
            GradingResult.marking_guide_id == guide_id,
            GradingResult.created_at >= recent_threshold
        ).count()
        
        if recent_results > 0:
            logger.warning(f"Guide {guide_id} has recent processing activity ({recent_results} results in last 5 minutes)")
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Error checking if guide {guide_id} is in use: {str(e)}")
        return False