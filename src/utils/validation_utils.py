"""Validation utilities for content validation and duplicate detection.

Provides centralized validation functions that can be used across the application
for consistent content validation, file validation, and duplicate detection.
"""

import os
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from werkzeug.datastructures import FileStorage

from src.services.content_validation_service import ContentValidationService
from src.database.models import db, Submission, MarkingGuide
from utils.logger import logger


class ValidationUtils:
    """Utility class for content validation and duplicate detection."""
    
    # Allowed file extensions for uploads
    ALLOWED_EXTENSIONS = {
        'pdf', 'docx', 'doc', 'txt', 'jpg', 'jpeg', 'png', 'tiff', 'bmp'
    }
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_TEXT_LENGTH = 1000000  # 1M characters
    
    # Minimum content requirements
    MIN_TEXT_LENGTH = 10  # Minimum 10 characters
    MIN_CONFIDENCE = 0.3  # Minimum OCR confidence
    
    @classmethod
    def validate_file_upload(cls, file: FileStorage) -> Dict[str, Any]:
        """Validate a file upload before processing.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Dictionary with validation results
        """
        try:
            # Check if file exists
            if not file:
                return {
                    'success': False,
                    'error': 'No file provided',
                    'error_code': 'NO_FILE'
                }
                
            # Check filename
            if not file.filename or file.filename.strip() == '':
                return {
                    'success': False,
                    'error': 'No file selected or filename is empty',
                    'error_code': 'EMPTY_FILENAME'
                }
                
            # Check file extension
            if not cls._is_allowed_file(file.filename):
                return {
                    'success': False,
                    'error': f'File type not allowed. Supported formats: {", ".join(sorted(cls.ALLOWED_EXTENSIONS))}',
                    'error_code': 'INVALID_EXTENSION',
                    'allowed_extensions': list(cls.ALLOWED_EXTENSIONS)
                }
                
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size == 0:
                return {
                    'success': False,
                    'error': 'File is empty',
                    'error_code': 'EMPTY_FILE'
                }
                
            if file_size > cls.MAX_FILE_SIZE:
                return {
                    'success': False,
                    'error': f'File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size ({cls.MAX_FILE_SIZE / 1024 / 1024:.0f}MB)',
                    'error_code': 'FILE_TOO_LARGE',
                    'file_size': file_size,
                    'max_size': cls.MAX_FILE_SIZE
                }
                
            return {
                'success': True,
                'filename': file.filename,
                'file_type': cls._get_file_type(file.filename),
                'file_size': file_size
            }
            
        except Exception as e:
            logger.error(f"Error validating file upload: {e}")
            return {
                'success': False,
                'error': f'Error validating file: {str(e)}',
                'error_code': 'VALIDATION_ERROR'
            }
            
    @classmethod
    def validate_content_quality(cls, text_content: str, confidence: float) -> Dict[str, Any]:
        """Validate the quality of extracted content.
        
        Args:
            text_content: Extracted text content
            confidence: OCR confidence score
            
        Returns:
            Dictionary with content quality validation results
        """
        issues = []
        warnings = []
        
        # Check text length
        if len(text_content.strip()) < cls.MIN_TEXT_LENGTH:
            issues.append({
                'type': 'insufficient_content',
                'message': f'Content too short (minimum {cls.MIN_TEXT_LENGTH} characters required)',
                'severity': 'error'
            })
            
        # Check text length upper bound
        if len(text_content) > cls.MAX_TEXT_LENGTH:
            warnings.append({
                'type': 'excessive_content',
                'message': f'Content very long ({len(text_content)} characters), processing may be slow',
                'severity': 'warning'
            })
            
        # Check OCR confidence
        if confidence < cls.MIN_CONFIDENCE:
            warnings.append({
                'type': 'low_confidence',
                'message': f'Low OCR confidence ({confidence:.2f}), results may be inaccurate',
                'severity': 'warning'
            })
            
        # Check for suspicious patterns
        suspicious_patterns = cls._detect_suspicious_patterns(text_content)
        if suspicious_patterns:
            warnings.extend(suspicious_patterns)
            
        return {
            'success': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'text_length': len(text_content),
            'confidence': confidence,
            'quality_score': cls._calculate_quality_score(text_content, confidence)
        }
        
    @classmethod
    def validate_duplicate_policy(cls, duplicate_result: Dict[str, Any], 
                                policy: str = 'warn') -> Dict[str, Any]:
        """Validate duplicate detection results against policy.
        
        Args:
            duplicate_result: Result from duplicate detection
            policy: Duplicate handling policy ('allow', 'warn', 'reject')
            
        Returns:
            Dictionary with policy validation results
        """
        if not duplicate_result.get('is_duplicate', False):
            return {
                'success': True,
                'action': 'proceed',
                'message': 'No duplicates found'
            }
            
        if policy == 'allow':
            return {
                'success': True,
                'action': 'proceed',
                'message': 'Duplicate detected but allowed by policy',
                'duplicate_info': duplicate_result
            }
        elif policy == 'warn':
            return {
                'success': True,
                'action': 'proceed_with_warning',
                'message': 'Duplicate detected - proceeding with warning',
                'duplicate_info': duplicate_result,
                'warning': True
            }
        elif policy == 'reject':
            return {
                'success': False,
                'action': 'reject',
                'message': 'Duplicate detected and rejected by policy',
                'duplicate_info': duplicate_result,
                'error_code': 'DUPLICATE_REJECTED'
            }
        else:
            return {
                'success': False,
                'action': 'error',
                'message': f'Invalid duplicate policy: {policy}',
                'error_code': 'INVALID_POLICY'
            }
            
    @classmethod
    def validate_submission_metadata(cls, student_name: str, student_id: str, 
                                   marking_guide_id: str) -> Dict[str, Any]:
        """Validate submission metadata.
        
        Args:
            student_name: Student's name
            student_id: Student's ID
            marking_guide_id: Associated marking guide ID
            
        Returns:
            Dictionary with metadata validation results
        """
        issues = []
        
        # Validate student name
        if not student_name or not student_name.strip():
            issues.append({
                'field': 'student_name',
                'message': 'Student name is required',
                'severity': 'error'
            })
        elif len(student_name.strip()) < 2:
            issues.append({
                'field': 'student_name',
                'message': 'Student name must be at least 2 characters',
                'severity': 'error'
            })
        elif len(student_name) > 200:
            issues.append({
                'field': 'student_name',
                'message': 'Student name too long (maximum 200 characters)',
                'severity': 'error'
            })
            
        # Validate student ID
        if not student_id or not student_id.strip():
            issues.append({
                'field': 'student_id',
                'message': 'Student ID is required',
                'severity': 'error'
            })
        elif len(student_id.strip()) < 1:
            issues.append({
                'field': 'student_id',
                'message': 'Student ID cannot be empty',
                'severity': 'error'
            })
        elif len(student_id) > 100:
            issues.append({
                'field': 'student_id',
                'message': 'Student ID too long (maximum 100 characters)',
                'severity': 'error'
            })
            
        # Validate marking guide ID
        if not marking_guide_id or not marking_guide_id.strip():
            issues.append({
                'field': 'marking_guide_id',
                'message': 'Marking guide ID is required',
                'severity': 'error'
            })
        else:
            # Check if marking guide exists
            guide = MarkingGuide.query.filter_by(
                id=marking_guide_id, is_active=True
            ).first()
            if not guide:
                issues.append({
                    'field': 'marking_guide_id',
                    'message': 'Invalid or inactive marking guide',
                    'severity': 'error'
                })
                
        return {
            'success': len(issues) == 0,
            'issues': issues,
            'sanitized_data': {
                'student_name': student_name.strip() if student_name else '',
                'student_id': student_id.strip() if student_id else '',
                'marking_guide_id': marking_guide_id.strip() if marking_guide_id else ''
            }
        }
        
    @classmethod
    def validate_marking_guide_metadata(cls, title: str, description: str = None) -> Dict[str, Any]:
        """Validate marking guide metadata.
        
        Args:
            title: Guide title
            description: Optional guide description
            
        Returns:
            Dictionary with metadata validation results
        """
        issues = []
        
        # Validate title
        if not title or not title.strip():
            issues.append({
                'field': 'title',
                'message': 'Title is required',
                'severity': 'error'
            })
        elif len(title.strip()) < 3:
            issues.append({
                'field': 'title',
                'message': 'Title must be at least 3 characters',
                'severity': 'error'
            })
        elif len(title) > 200:
            issues.append({
                'field': 'title',
                'message': 'Title too long (maximum 200 characters)',
                'severity': 'error'
            })
            
        # Validate description (optional)
        if description and len(description) > 1000:
            issues.append({
                'field': 'description',
                'message': 'Description too long (maximum 1000 characters)',
                'severity': 'error'
            })
            
        return {
            'success': len(issues) == 0,
            'issues': issues,
            'sanitized_data': {
                'title': title.strip() if title else '',
                'description': description.strip() if description else None
            }
        }
        
    @classmethod
    def get_validation_summary(cls, *validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Combine multiple validation results into a summary.
        
        Args:
            *validation_results: Variable number of validation result dictionaries
            
        Returns:
            Combined validation summary
        """
        all_issues = []
        all_warnings = []
        overall_success = True
        
        for result in validation_results:
            if not result.get('success', True):
                overall_success = False
                
            # Collect issues
            if 'issues' in result:
                all_issues.extend(result['issues'])
            elif not result.get('success', True) and 'error' in result:
                all_issues.append({
                    'type': 'general_error',
                    'message': result['error'],
                    'severity': 'error'
                })
                
            # Collect warnings
            if 'warnings' in result:
                all_warnings.extend(result['warnings'])
            elif result.get('warning', False):
                all_warnings.append({
                    'type': 'general_warning',
                    'message': result.get('message', 'Warning detected'),
                    'severity': 'warning'
                })
                
        return {
            'success': overall_success,
            'total_issues': len(all_issues),
            'total_warnings': len(all_warnings),
            'issues': all_issues,
            'warnings': all_warnings,
            'has_errors': len([i for i in all_issues if i.get('severity') == 'error']) > 0,
            'has_warnings': len(all_warnings) > 0
        }
        
    @classmethod
    def _is_allowed_file(cls, filename: str) -> bool:
        """Check if file extension is allowed."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in cls.ALLOWED_EXTENSIONS
               
    @classmethod
    def _get_file_type(cls, filename: str) -> str:
        """Extract file type from filename."""
        return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
    @classmethod
    def _detect_suspicious_patterns(cls, text: str) -> List[Dict[str, Any]]:
        """Detect suspicious patterns in text content."""
        warnings = []
        
        # Check for excessive repetition
        words = text.split()
        if len(words) > 10:
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
                
            max_freq = max(word_freq.values())
            if max_freq > len(words) * 0.3:  # More than 30% repetition
                warnings.append({
                    'type': 'excessive_repetition',
                    'message': 'Content contains excessive word repetition',
                    'severity': 'warning'
                })
                
        # Check for very short lines (possible OCR artifacts)
        lines = text.split('\n')
        short_lines = [line for line in lines if 0 < len(line.strip()) < 3]
        if len(short_lines) > len(lines) * 0.5:
            warnings.append({
                'type': 'fragmented_text',
                'message': 'Content appears fragmented (possible OCR issues)',
                'severity': 'warning'
            })
            
        return warnings
        
    @classmethod
    def _calculate_quality_score(cls, text: str, confidence: float) -> float:
        """Calculate overall content quality score."""
        # Base score from confidence
        score = confidence
        
        # Adjust for text length
        text_length = len(text.strip())
        if text_length < cls.MIN_TEXT_LENGTH:
            score *= 0.5
        elif text_length > 1000:
            score = min(score + 0.1, 1.0)
            
        # Adjust for suspicious patterns
        suspicious_patterns = cls._detect_suspicious_patterns(text)
        score -= len(suspicious_patterns) * 0.1
        
        return max(0.0, min(1.0, score))


class ContentHashUtils:
    """Utilities for content hashing and comparison."""
    
    @staticmethod
    def compute_file_hash(file_path: Union[str, Path]) -> str:
        """Compute SHA256 hash of file content.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA256 hash as hexadecimal string
        """
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error computing file hash for {file_path}: {e}")
            return ""
            
    @staticmethod
    def compute_text_hash(text: str, normalize: bool = True) -> str:
        """Compute SHA256 hash of text content.
        
        Args:
            text: Text content
            normalize: Whether to normalize text before hashing
            
        Returns:
            SHA256 hash as hexadecimal string
        """
        if normalize:
            # Use ContentValidationService for consistent normalization
            service = ContentValidationService()
            text = service.normalize_text(text)
            
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
        
    @staticmethod
    def compare_hashes(hash1: str, hash2: str) -> bool:
        """Compare two content hashes.
        
        Args:
            hash1: First hash
            hash2: Second hash
            
        Returns:
            True if hashes match
        """
        return hash1.lower() == hash2.lower() if hash1 and hash2 else False