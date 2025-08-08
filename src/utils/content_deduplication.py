"""Content deduplication utilities for detecting duplicate marking guides and submissions."""

import hashlib
import logging
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from src.database.models import MarkingGuide, Submission

logger = logging.getLogger(__name__)


def calculate_content_hash(content: str) -> str:
    """
    Calculate SHA256 hash of content for duplicate detection.
    
    Args:
        content: Text content to hash
        
    Returns:
        SHA256 hash as hexadecimal string
    """
    if not content:
        return ""
    
    # Normalize content by stripping whitespace and converting to lowercase
    normalized_content = content.strip().lower()
    
    # Calculate SHA256 hash
    hash_object = hashlib.sha256(normalized_content.encode('utf-8'))
    return hash_object.hexdigest()


def check_marking_guide_duplicate(
    user_id: str, 
    content: str, 
    db_session: Session
) -> Tuple[bool, Optional[MarkingGuide]]:
    """
    Check if a marking guide with the same content already exists for the user.
    
    Args:
        user_id: ID of the user
        content: Content text to check for duplicates
        db_session: Database session
        
    Returns:
        Tuple of (is_duplicate, existing_guide)
    """
    if not content or not user_id:
        return False, None
    
    try:
        content_hash = calculate_content_hash(content)
        if not content_hash:
            return False, None
        
        # Check for existing marking guide with same content hash and user
        existing_guide = db_session.query(MarkingGuide).filter(
            MarkingGuide.user_id == user_id,
            MarkingGuide.content_hash == content_hash,
            MarkingGuide.is_active == True
        ).first()
        
        if existing_guide:
            logger.info(f"Duplicate marking guide found for user {user_id}: {existing_guide.title}")
            return True, existing_guide
        
        return False, None
        
    except Exception as e:
        logger.error(f"Error checking marking guide duplicate: {e}")
        return False, None


def check_submission_duplicate(
    user_id: str, 
    content: str, 
    db_session: Session
) -> Tuple[bool, Optional[Submission]]:
    """
    Check if a submission with the same content already exists for the user.
    
    Args:
        user_id: ID of the user
        content: Content text to check for duplicates
        db_session: Database session
        
    Returns:
        Tuple of (is_duplicate, existing_submission)
    """
    if not content or not user_id:
        return False, None
    
    try:
        content_hash = calculate_content_hash(content)
        if not content_hash:
            return False, None
        
        # Check for existing submission with same content hash and user
        existing_submission = db_session.query(Submission).filter(
            Submission.user_id == user_id,
            Submission.content_hash == content_hash,
            Submission.archived == False
        ).first()
        
        if existing_submission:
            logger.info(f"Duplicate submission found for user {user_id}: {existing_submission.filename}")
            return True, existing_submission
        
        return False, None
        
    except Exception as e:
        logger.error(f"Error checking submission duplicate: {e}")
        return False, None