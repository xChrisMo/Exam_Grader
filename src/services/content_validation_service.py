"""Content Validation Service for duplicate file detection.

This service handles:
- Text extraction from various file formats (PDF, DOCX, images)
- Content normalization and hashing
- Duplicate detection logic
- Integration with existing OCR and file processing services
"""

import hashlib
import re
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from src.database.models import db, Submission, MarkingGuide
from src.services.ocr_service import OCRService
from utils.logger import logger


class ContentValidationService:
    """Service for validating file content and detecting duplicates."""
    
    def __init__(self, ocr_service: Optional[OCRService] = None):
        """Initialize the content validation service.
        
        Args:
            ocr_service: OCR service instance for text extraction from images/PDFs
        """
        self.ocr_service = ocr_service or OCRService()
        
    def normalize_text(self, text: str) -> str:
        """Normalize text content for consistent comparison.
        
        Args:
            text: Raw text content
            
        Returns:
            Normalized text string
        """
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove extra whitespace and normalize line breaks
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common punctuation that doesn't affect content meaning
        # Keep important punctuation like periods for sentence structure
        chars_to_remove = '"\'\u201c\u201d\u2018\u2019`\u00b4'
        for char in chars_to_remove:
            normalized = normalized.replace(char, '')
        
        # Normalize common variations
        normalized = normalized.replace('\u2013', '-')  # en dash
        normalized = normalized.replace('\u2014', '-')  # em dash
        normalized = normalized.replace('\u2026', '...')  # ellipsis
        
        return normalized.strip()
    
    def compute_content_hash(self, text: str) -> str:
        """Compute SHA256 hash of normalized text content.
        
        Args:
            text: Text content to hash
            
        Returns:
            SHA256 hash as hexadecimal string
        """
        normalized_text = self.normalize_text(text)
        return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
    
    def extract_text_content(self, file_path: str, file_type: str) -> Tuple[str, float]:
        """Extract text content from a file.
        
        Args:
            file_path: Path to the file
            file_type: Type of file (pdf, docx, jpg, png, etc.)
            
        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                logger.error(f"File not found: {file_path}")
                return "", 0.0
            
            # Handle different file types
            if file_type.lower() in ['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'bmp']:
                # Use OCR service for images and PDFs
                result = self.ocr_service.extract_text(file_path)
                if result and 'text' in result:
                    confidence = result.get('confidence', 0.0)
                    return result['text'], confidence
                else:
                    logger.warning(f"OCR extraction failed for {file_path}")
                    return "", 0.0
                    
            elif file_type.lower() in ['docx', 'doc']:
                # Handle Word documents
                try:
                    import docx
                    doc = docx.Document(file_path)
                    text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                    return text, 1.0  # High confidence for direct text extraction
                except ImportError:
                    logger.error("python-docx not installed, cannot process DOCX files")
                    return "", 0.0
                except Exception as e:
                    logger.error(f"Error extracting text from DOCX: {e}")
                    return "", 0.0
                    
            elif file_type.lower() == 'txt':
                # Handle plain text files
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    return text, 1.0
                except UnicodeDecodeError:
                    # Try with different encoding
                    try:
                        with open(file_path, 'r', encoding='latin-1') as f:
                            text = f.read()
                        return text, 0.9  # Slightly lower confidence due to encoding issues
                    except Exception as e:
                        logger.error(f"Error reading text file: {e}")
                        return "", 0.0
                        
            else:
                logger.warning(f"Unsupported file type for text extraction: {file_type}")
                return "", 0.0
                
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return "", 0.0
    
    def validate_file_content(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Validate file content and compute hash.
        
        Args:
            file_path: Path to the file
            file_type: Type of file
            
        Returns:
            Dictionary containing validation results
        """
        try:
            # Extract text content
            text_content, confidence = self.extract_text_content(file_path, file_type)
            
            if not text_content.strip():
                return {
                    'success': False,
                    'error': 'No text content could be extracted from the file',
                    'content_hash': None,
                    'text_content': '',
                    'confidence': 0.0
                }
            
            # Compute content hash
            content_hash = self.compute_content_hash(text_content)
            
            return {
                'success': True,
                'content_hash': content_hash,
                'text_content': text_content,
                'confidence': confidence,
                'text_length': len(text_content),
                'normalized_length': len(self.normalize_text(text_content))
            }
            
        except Exception as e:
            logger.error(f"Content validation failed for {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'content_hash': None,
                'text_content': '',
                'confidence': 0.0
            }
    
    def check_submission_duplicate(self, content_hash: str, user_id: str, 
                                 marking_guide_id: Optional[str] = None) -> Dict[str, Any]:
        """Check if a submission with the same content hash already exists.
        
        Args:
            content_hash: Content hash to check
            user_id: User ID for scoping the check
            marking_guide_id: Optional marking guide ID for more specific checking
            
        Returns:
            Dictionary with duplicate check results
        """
        try:
            query = db.session.query(Submission).filter(
                Submission.content_hash == content_hash,
                Submission.user_id == user_id
            )
            
            # If marking guide is specified, check within that scope
            if marking_guide_id:
                query = query.filter(Submission.marking_guide_id == marking_guide_id)
            
            existing_submission = query.first()
            
            if existing_submission:
                return {
                    'is_duplicate': True,
                    'duplicate_submission': {
                        'id': existing_submission.id,
                        'filename': existing_submission.filename,
                        'student_name': existing_submission.student_name,
                        'student_id': existing_submission.student_id,
                        'created_at': existing_submission.created_at.isoformat(),
                        'processing_status': existing_submission.processing_status
                    },
                    'message': f"This submission appears to be a duplicate of '{existing_submission.filename}' uploaded on {existing_submission.created_at.strftime('%Y-%m-%d %H:%M')}."
                }
            else:
                return {
                    'is_duplicate': False,
                    'message': 'No duplicate content found.'
                }
                
        except Exception as e:
            logger.error(f"Error checking submission duplicate: {e}")
            return {
                'is_duplicate': False,
                'error': str(e),
                'message': 'Error occurred while checking for duplicates.'
            }
    
    def check_marking_guide_duplicate(self, content_hash: str, user_id: str) -> Dict[str, Any]:
        """Check if a marking guide with the same content hash already exists.
        
        Args:
            content_hash: Content hash to check
            user_id: User ID for scoping the check
            
        Returns:
            Dictionary with duplicate check results
        """
        try:
            existing_guide = db.session.query(MarkingGuide).filter(
                MarkingGuide.content_hash == content_hash,
                MarkingGuide.user_id == user_id,
                MarkingGuide.is_active == True
            ).first()
            
            if existing_guide:
                return {
                    'is_duplicate': True,
                    'duplicate_guide': {
                        'id': existing_guide.id,
                        'title': existing_guide.title,
                        'filename': existing_guide.filename,
                        'created_at': existing_guide.created_at.isoformat(),
                        'total_marks': existing_guide.total_marks
                    },
                    'message': f"This marking guide appears to be a duplicate of '{existing_guide.title}' (file: {existing_guide.filename}) created on {existing_guide.created_at.strftime('%Y-%m-%d %H:%M')}."
                }
            else:
                return {
                    'is_duplicate': False,
                    'message': 'No duplicate content found.'
                }
                
        except Exception as e:
            logger.error(f"Error checking marking guide duplicate: {e}")
            return {
                'is_duplicate': False,
                'error': str(e),
                'message': 'Error occurred while checking for duplicates.'
            }
    
    def validate_and_check_duplicates(self, file_path: str, file_type: str, 
                                    user_id: str, check_type: str,
                                    marking_guide_id: Optional[str] = None) -> Dict[str, Any]:
        """Complete validation and duplicate checking workflow.
        
        Args:
            file_path: Path to the file
            file_type: Type of file
            user_id: User ID
            check_type: 'submission' or 'marking_guide'
            marking_guide_id: Optional marking guide ID for submission checks
            
        Returns:
            Complete validation and duplicate check results
        """
        # Step 1: Validate file content
        validation_result = self.validate_file_content(file_path, file_type)
        
        if not validation_result['success']:
            return validation_result
        
        content_hash = validation_result['content_hash']
        
        # Step 2: Check for duplicates
        if check_type == 'submission':
            duplicate_result = self.check_submission_duplicate(
                content_hash, user_id, marking_guide_id
            )
        elif check_type == 'marking_guide':
            duplicate_result = self.check_marking_guide_duplicate(
                content_hash, user_id
            )
        else:
            return {
                'success': False,
                'error': f"Invalid check_type: {check_type}. Must be 'submission' or 'marking_guide'."
            }
        
        # Combine results
        result = {
            **validation_result,
            **duplicate_result
        }
        
        return result
    
    def get_content_similarity(self, text1: str, text2: str) -> float:
        """Calculate content similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            # Normalize both texts
            norm1 = self.normalize_text(text1)
            norm2 = self.normalize_text(text2)
            
            if not norm1 or not norm2:
                return 0.0
            
            # Simple word-based similarity
            words1 = set(norm1.split())
            words2 = set(norm2.split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union) if union else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating content similarity: {e}")
            return 0.0