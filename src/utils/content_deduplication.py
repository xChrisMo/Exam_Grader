"""
Content deduplication utilities for preventing duplicate document processing.

This module provides functions to calculate content hashes and check for duplicates
based on document content rather than filename or metadata.
"""

import hashlib
import logging
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from src.database.models import LLMDocument, MarkingGuide, Submission

logger = logging.getLogger(__name__)


def calculate_content_hash(content: str) -> str:
    """
    Calculate SHA-256 hash of document content for deduplication.
    
    Args:
        content: Text content of the document
        
    Returns:
        SHA-256 hash as hexadecimal string
    """
    if not content:
        return ""
    
    # Normalize content for consistent hashing
    normalized_content = content.strip().replace('\r\n', '\n').replace('\r', '\n')
    
    # Calculate SHA-256 hash
    hash_obj = hashlib.sha256(normalized_content.encode('utf-8'))
    return hash_obj.hexdigest()


def check_llm_document_duplicate(
    user_id: str, 
    content: str, 
    document_type: str,
    db_session: Session,
    exclude_id: Optional[str] = None
) -> Tuple[bool, Optional[LLMDocument]]:
    """
    Check if an LLM document with the same content already exists for the user.
    
    Args:
        user_id: User ID to check within
        content: Document text content
        document_type: Type of document (training_guide, test_submission, etc.)
        db_session: Database session
        exclude_id: Document ID to exclude from check (for updates)
        
    Returns:
        Tuple of (is_duplicate, existing_document)
    """
    if not content:
        return False, None
    
    content_hash = calculate_content_hash(content)
    if not content_hash:
        return False, None
    
    # Query for existing document with same content hash
    query = db_session.query(LLMDocument).filter(
        LLMDocument.user_id == user_id,
        LLMDocument.content_hash == content_hash,
        LLMDocument.type == document_type
    )
    
    if exclude_id:
        query = query.filter(LLMDocument.id != exclude_id)
    
    existing_doc = query.first()
    
    if existing_doc:
        logger.info(f"Found duplicate LLM document: {existing_doc.name} (ID: {existing_doc.id})")
        return True, existing_doc
    
    return False, None


def check_marking_guide_duplicate(
    user_id: str,
    content: str,
    db_session: Session,
    exclude_id: Optional[str] = None
) -> Tuple[bool, Optional[MarkingGuide]]:
    """
    Check if a marking guide with the same content already exists for the user.
    
    Args:
        user_id: User ID to check within
        content: Guide text content
        db_session: Database session
        exclude_id: Guide ID to exclude from check (for updates)
        
    Returns:
        Tuple of (is_duplicate, existing_guide)
    """
    if not content:
        return False, None
    
    content_hash = calculate_content_hash(content)
    if not content_hash:
        return False, None
    
    # Query for existing guide with same content hash
    query = db_session.query(MarkingGuide).filter(
        MarkingGuide.user_id == user_id,
        MarkingGuide.content_hash == content_hash
    )
    
    if exclude_id:
        query = query.filter(MarkingGuide.id != exclude_id)
    
    existing_guide = query.first()
    
    if existing_guide:
        logger.info(f"Found duplicate marking guide: {existing_guide.title} (ID: {existing_guide.id})")
        return True, existing_guide
    
    return False, None


def check_submission_duplicate(
    user_id: str,
    content: str,
    db_session: Session,
    exclude_id: Optional[str] = None
) -> Tuple[bool, Optional[Submission]]:
    """
    Check if a submission with the same content already exists for the user.
    
    Args:
        user_id: User ID to check within
        content: Submission text content
        db_session: Database session
        exclude_id: Submission ID to exclude from check (for updates)
        
    Returns:
        Tuple of (is_duplicate, existing_submission)
    """
    if not content:
        return False, None
    
    content_hash = calculate_content_hash(content)
    if not content_hash:
        return False, None
    
    # Query for existing submission with same content hash
    query = db_session.query(Submission).filter(
        Submission.user_id == user_id,
        Submission.content_hash == content_hash
    )
    
    if exclude_id:
        query = query.filter(Submission.id != exclude_id)
    
    existing_submission = query.first()
    
    if existing_submission:
        logger.info(f"Found duplicate submission: {existing_submission.filename} (ID: {existing_submission.id})")
        return True, existing_submission
    
    return False, None


def get_deduplication_response(existing_doc: Any, doc_type: str = "document") -> Dict[str, Any]:
    """
    Generate a standardized response for duplicate document detection.
    
    Args:
        existing_doc: The existing document object
        doc_type: Type of document for the message
        
    Returns:
        Dictionary with success=False and duplicate information
    """
    return {
        'success': False,
        'error': f'A {doc_type} with identical content already exists',
        'duplicate': True,
        'existing_document': {
            'id': existing_doc.id,
            'name': getattr(existing_doc, 'name', getattr(existing_doc, 'title', getattr(existing_doc, 'filename', 'Unknown'))),
            'created_at': existing_doc.created_at.isoformat() if existing_doc.created_at else None,
            'word_count': getattr(existing_doc, 'word_count', 0),
            'file_size': getattr(existing_doc, 'file_size', 0)
        }
    }


def update_content_hash(document: Any, content: str) -> None:
    """
    Update the content hash for a document object.
    
    Args:
        document: Document object (LLMDocument, MarkingGuide, or Submission)
        content: Text content to hash
    """
    if hasattr(document, 'content_hash'):
        document.content_hash = calculate_content_hash(content)
    else:
        logger.warning(f"Document type {type(document)} does not have content_hash field")


def is_content_changed(document: Any, new_content: str) -> bool:
    """
    Check if document content has changed by comparing hashes.
    
    Args:
        document: Existing document object
        new_content: New content to compare
        
    Returns:
        True if content has changed, False otherwise
    """
    if not hasattr(document, 'content_hash'):
        return True  # Assume changed if no hash field
    
    current_hash = getattr(document, 'content_hash', '')
    new_hash = calculate_content_hash(new_content)
    
    return current_hash != new_hash