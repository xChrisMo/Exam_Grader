"""Content Validation Service for duplicate file detection.

This service handles:
- Text extraction from various file formats (PDF, DOCX, images)
- Content normalization and hashing
- Duplicate detection logic
- Integration with existing OCR and file processing services
"""
from typing import Any, Dict, Optional, Tuple

import hashlib
# Removed regex import - using LLM-based approaches instead
from pathlib import Path

from src.database.models import db, Submission, MarkingGuide
from src.services.consolidated_ocr_service import ConsolidatedOCRService
from utils.logger import logger


class ContentValidationService:
    """Service for validating file content and detecting duplicates."""
    
    def __init__(self, ocr_service: Optional[ConsolidatedOCRService] = None):
        """Initialize the content validation service.
        
        Args:
            ocr_service: OCR service instance for text extraction from images/PDFs
        """
        self.ocr_service = ocr_service or ConsolidatedOCRService()
        
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
        
        # Remove extra whitespace and normalize line breaks using basic string operations
        normalized = ' '.join(normalized.split())
        
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
    
    def compute_content_hash(self, text_content: str) -> str:
        """Compute SHA-256 hash of normalized text content.
        
        Args:
            text_content: Text content to hash
            
        Returns:
            SHA-256 hash string
        """
        normalized_text = self.normalize_text(text_content)
        return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of file content.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA-256 hash string
        """
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error computing file hash for {file_path}: {e}")
            # Fallback to a hash based on filename and size
            import os
            file_info = f"{os.path.basename(file_path)}_{os.path.getsize(file_path)}"
            return hashlib.sha256(file_info.encode('utf-8')).hexdigest()
    
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
            if file_type.lower() in ['docx', 'doc']:
                from src.parsing.parse_submission import DocumentParser
                try:
                    text_content = DocumentParser.extract_text_from_docx(file_path)
                    if text_content and len(text_content.strip()) >= 10:
                        logger.info(f"✓ Content validation: {len(text_content)} characters extracted")
                        return text_content, 1.0  # Perfect confidence for Word documents
                    else:
                        logger.warning(f"⚠ Word document appears to be empty")
                        return "", 0.0
                except Exception as e:
                    logger.error(f"✗ Content validation failed: {str(e)}")
                    return "", 0.0
            elif file_type.lower() == 'pdf':
                # For PDFs, text extraction is handled by OCR service during upload
                # We just validate that the file exists and is readable
                try:
                    logger.info(f"✓ PDF file type accepted - text extraction handled by OCR service")
                    # Return empty string with confidence - actual text will be provided via extracted_text parameter
                    return "", 0.8  # Lower confidence since OCR was used
                except Exception as e:
                    logger.error(f"✗ PDF validation failed: {str(e)}")
                    return "", 0.0
            elif file_type.lower() == 'txt':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
                    if text_content and len(text_content.strip()) >= 10:
                        logger.info(f"✓ Text file validation: {len(text_content)} characters extracted")
                        return text_content, 1.0  # Perfect confidence for text files
                    else:
                        logger.warning(f"⚠ Text file appears to be empty")
                        return "", 0.0
                except Exception as e:
                    logger.error(f"✗ Text file validation failed: {str(e)}")
                    return "", 0.0
            elif file_type.lower() in ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'gif']:
                # For images, text extraction is handled by OCR service during upload
                try:
                    logger.info(f"✓ Image file type accepted - text extraction handled by OCR service")
                    return "", 0.7  # Lower confidence since OCR was used
                except Exception as e:
                    logger.error(f"✗ Image validation failed: {str(e)}")
                    return "", 0.0
            else:
                logger.error(f"✗ Unsupported file type: {file_type}. Supported types: docx, doc, pdf, txt, jpg, jpeg, png, bmp, tiff, gif")
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
            
            # For image files, if OCR fails, still allow the upload but use file-based hash
            if not text_content.strip():
                if file_type.lower() in ['jpg', 'jpeg', 'png', 'tiff', 'bmp']:
                    # For images, compute hash based on file content instead of text
                    logger.warning(f"No text extracted from image {file_path}, using file-based hash")
                    file_hash = self._compute_file_hash(file_path)
                    return {
                        'success': True,
                        'content_hash': file_hash,
                        'text_content': '',
                        'confidence': 0.0,
                        'text_length': 0,
                        'normalized_length': 0,
                        'validation_method': 'file_hash',
                        'file_size': Path(file_path).stat().st_size,
                        'file_type': file_type
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No text content could be extracted from the file',
                        'content_hash': None,
                        'text_content': '',
                        'confidence': 0.0,
                        'file_size': Path(file_path).stat().st_size,
                        'file_type': file_type
                    }
            
            # Compute content hash
            content_hash = self.compute_content_hash(text_content)
            
            return {
                'success': True,
                'content_hash': content_hash,
                'text_content': text_content,
                'confidence': confidence,
                'text_length': len(text_content),
                'normalized_length': len(self.normalize_text(text_content)),
                'validation_method': 'text_content',
                'file_size': Path(file_path).stat().st_size,
                'file_type': file_type
            }
            
        except Exception as e:
            logger.error(f"Content validation failed for {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'content_hash': None,
                'text_content': '',
                'confidence': 0.0,
                'file_size': 0,
                'file_type': file_type
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
                                    marking_guide_id: Optional[str] = None,
                                    extracted_text: Optional[str] = None) -> Dict[str, Any]:
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
        if extracted_text is not None:
            # Use pre-extracted text (from OCR or other processing)
            logger.info(f"Using pre-extracted text ({len(extracted_text)} characters) for validation")
            content_hash = self.compute_content_hash(extracted_text)
            validation_result = {
                'success': True,
                'content_hash': content_hash,
                'text_content': extracted_text,
                'confidence': 0.8,  # OCR confidence
                'text_length': len(extracted_text),
                'normalized_length': len(self.normalize_text(extracted_text)),
                'validation_method': 'pre_extracted_text',
                'file_size': Path(file_path).stat().st_size,
                'file_type': file_type
            }
        else:
            # Extract text from file
            validation_result = self.validate_file_content(file_path, file_type)
        
        if not validation_result['success']:
            # For marking guides, be more lenient with content extraction failures
            if check_type == 'marking_guide':
                logger.warning(f"Content extraction failed for marking guide {file_path}, using file-based validation")
                # Try to create a file-based hash as fallback
                try:
                    file_hash = self._compute_file_hash(file_path)
                    validation_result = {
                        'success': True,
                        'content_hash': file_hash,
                        'text_content': '',
                        'confidence': 0.0,
                        'text_length': 0,
                        'normalized_length': 0,
                        'validation_method': 'file_hash_fallback',
                        'file_size': Path(file_path).stat().st_size,
                        'file_type': file_type
                    }
                except Exception as e:
                    logger.error(f"File-based validation also failed for {file_path}: {e}")
                    return validation_result
            else:
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
            'duplicate_check': duplicate_result
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