"""Enhanced Upload Service with content validation and duplicate detection.

This service integrates file upload handling with content validation,
duplicate detection, and database operations for both submissions and marking guides.
"""

import os
import uuid
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from src.database.models import db, Submission, MarkingGuide, User
from src.services.content_validation_service import ContentValidationService
from src.services.ocr_service import OCRService
from utils.logger import logger
from utils.file_processor import FileProcessor


class EnhancedUploadService:
    """Service for handling file uploads with content validation and duplicate detection."""
    
    def __init__(self, upload_folder: str, ocr_service: Optional[OCRService] = None):
        """Initialize the enhanced upload service.
        
        Args:
            upload_folder: Base directory for file uploads
            ocr_service: OCR service instance
        """
        self.upload_folder = Path(upload_folder)
        self.ocr_service = ocr_service or OCRService()
        self.content_validator = ContentValidationService(self.ocr_service)
        self.file_processor = FileProcessor()
        
        # Ensure upload directories exist
        self.submissions_folder = self.upload_folder / 'submissions'
        self.guides_folder = self.upload_folder / 'marking_guides'
        self.submissions_folder.mkdir(parents=True, exist_ok=True)
        self.guides_folder.mkdir(parents=True, exist_ok=True)
        
        # Allowed file extensions
        self.allowed_extensions = {
            'pdf', 'docx', 'doc', 'txt', 'jpg', 'jpeg', 'png', 'tiff', 'bmp'
        }
    
    def _is_allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed.
        
        Args:
            filename: Name of the file
            
        Returns:
            True if file extension is allowed
        """
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def _get_file_type(self, filename: str) -> str:
        """Extract file type from filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            File extension in lowercase
        """
        return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    def _save_file(self, file: FileStorage, target_folder: Path, 
                   prefix: str = '') -> Tuple[str, str]:
        """Save uploaded file to disk.
        
        Args:
            file: Uploaded file object
            target_folder: Directory to save the file
            prefix: Optional prefix for filename
            
        Returns:
            Tuple of (file_path, secure_filename)
        """
        # Generate secure filename
        original_filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        
        if prefix:
            filename = f"{prefix}_{file_id}_{original_filename}"
        else:
            filename = f"{file_id}_{original_filename}"
        
        file_path = target_folder / filename
        
        # Save file
        file.save(str(file_path))
        
        return str(file_path), original_filename
    
    def validate_file_upload(self, file: FileStorage) -> Dict[str, Any]:
        """Validate uploaded file before processing.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Validation result dictionary
        """
        if not file or not file.filename:
            return {
                'success': False,
                'error': 'No file provided',
                'code': 'NO_FILE'
            }
        
        if not self._is_allowed_file(file.filename):
            return {
                'success': False,
                'error': f'File type not allowed. Supported types: {", ".join(self.allowed_extensions)}',
                'code': 'INVALID_FILE_TYPE'
            }
        
        # Check file size (limit to 50MB)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        max_size = 50 * 1024 * 1024  # 50MB
        if file_size > max_size:
            return {
                'success': False,
                'error': f'File size ({file_size / 1024 / 1024:.1f}MB) exceeds maximum allowed size (50MB)',
                'code': 'FILE_TOO_LARGE'
            }
        
        return {
            'success': True,
            'file_size': file_size,
            'file_type': self._get_file_type(file.filename)
        }
    
    def upload_submission(self, file: FileStorage, user_id: str, 
                         marking_guide_id: str, student_name: str, 
                         student_id: str, check_duplicates: bool = True) -> Dict[str, Any]:
        """Upload and process a submission file.
        
        Args:
            file: Uploaded file object
            user_id: ID of the user uploading
            marking_guide_id: ID of the associated marking guide
            student_name: Name of the student
            student_id: Student ID
            check_duplicates: Whether to check for duplicate content
            
        Returns:
            Upload result dictionary
        """
        try:
            # Step 1: Validate file
            validation_result = self.validate_file_upload(file)
            if not validation_result['success']:
                return validation_result
            
            file_size = validation_result['file_size']
            file_type = validation_result['file_type']
            
            # Step 2: Save file temporarily
            temp_path, original_filename = self._save_file(
                file, self.submissions_folder, 'temp'
            )
            
            try:
                # Step 3: Extract and validate content
                if check_duplicates:
                    content_result = self.content_validator.validate_and_check_duplicates(
                        temp_path, file_type, user_id, 'submission', marking_guide_id
                    )
                    
                    if not content_result['success']:
                        os.remove(temp_path)  # Clean up temp file
                        return {
                            'success': False,
                            'error': content_result.get('error', 'Content validation failed'),
                            'code': 'CONTENT_VALIDATION_FAILED'
                        }
                    
                    # Check for duplicates
                    if content_result.get('is_duplicate', False):
                        os.remove(temp_path)  # Clean up temp file
                        return {
                            'success': False,
                            'error': content_result['message'],
                            'code': 'DUPLICATE_CONTENT',
                            'duplicate_info': content_result.get('duplicate_submission')
                        }
                    
                    content_hash = content_result['content_hash']
                    text_content = content_result['text_content']
                    confidence = content_result['confidence']
                else:
                    # Skip duplicate checking but still extract content
                    content_validation = self.content_validator.validate_file_content(
                        temp_path, file_type
                    )
                    if content_validation['success']:
                        content_hash = content_validation['content_hash']
                        text_content = content_validation['text_content']
                        confidence = content_validation['confidence']
                    else:
                        content_hash = None
                        text_content = ''
                        confidence = 0.0
                
                # Step 4: Move file to final location
                final_path, _ = self._save_file(
                    type('MockFile', (), {
                        'filename': original_filename,
                        'save': lambda path: os.rename(temp_path, path)
                    })(),
                    self.submissions_folder,
                    'submission'
                )
                
                # Step 5: Create database record
                submission = Submission(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    marking_guide_id=marking_guide_id,
                    student_name=student_name,
                    student_id=student_id,
                    filename=original_filename,
                    file_path=final_path,
                    file_size=file_size,
                    content_text=text_content,
                    content_hash=content_hash,
                    processing_status='pending'
                )
                
                db.session.add(submission)
                db.session.commit()
                
                logger.info(f"Submission uploaded successfully: {submission.id}")
                
                return {
                    'success': True,
                    'submission_id': submission.id,
                    'filename': original_filename,
                    'file_size': file_size,
                    'content_hash': content_hash,
                    'text_length': len(text_content) if text_content else 0,
                    'confidence': confidence,
                    'message': 'Submission uploaded successfully'
                }
                
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e
                
        except Exception as e:
            logger.error(f"Error uploading submission: {e}")
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}',
                'code': 'UPLOAD_ERROR'
            }
    
    def upload_marking_guide(self, file: FileStorage, user_id: str, 
                           title: str, check_duplicates: bool = True) -> Dict[str, Any]:
        """Upload and process a marking guide file.
        
        Args:
            file: Uploaded file object
            user_id: ID of the user uploading
            title: Title for the marking guide
            check_duplicates: Whether to check for duplicate content
            
        Returns:
            Upload result dictionary
        """
        try:
            # Step 1: Validate file
            validation_result = self.validate_file_upload(file)
            if not validation_result['success']:
                return validation_result
            
            file_size = validation_result['file_size']
            file_type = validation_result['file_type']
            
            # Step 2: Save file temporarily
            temp_path, original_filename = self._save_file(
                file, self.guides_folder, 'temp'
            )
            
            try:
                # Step 3: Extract and validate content
                if check_duplicates:
                    content_result = self.content_validator.validate_and_check_duplicates(
                        temp_path, file_type, user_id, 'marking_guide'
                    )
                    
                    if not content_result['success']:
                        os.remove(temp_path)  # Clean up temp file
                        return {
                            'success': False,
                            'error': content_result.get('error', 'Content validation failed'),
                            'code': 'CONTENT_VALIDATION_FAILED'
                        }
                    
                    # Check for duplicates
                    if content_result.get('is_duplicate', False):
                        os.remove(temp_path)  # Clean up temp file
                        return {
                            'success': False,
                            'error': content_result['message'],
                            'code': 'DUPLICATE_CONTENT',
                            'duplicate_info': content_result.get('duplicate_guide')
                        }
                    
                    content_hash = content_result['content_hash']
                    text_content = content_result['text_content']
                    confidence = content_result['confidence']
                else:
                    # Skip duplicate checking but still extract content
                    content_validation = self.content_validator.validate_file_content(
                        temp_path, file_type
                    )
                    if content_validation['success']:
                        content_hash = content_validation['content_hash']
                        text_content = content_validation['text_content']
                        confidence = content_validation['confidence']
                    else:
                        content_hash = None
                        text_content = ''
                        confidence = 0.0
                
                # Step 4: Move file to final location
                final_path, _ = self._save_file(
                    type('MockFile', (), {
                        'filename': original_filename,
                        'save': lambda path: os.rename(temp_path, path)
                    })(),
                    self.guides_folder,
                    'guide'
                )
                
                # Step 5: Create database record
                marking_guide = MarkingGuide(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title=title,
                    filename=original_filename,
                    file_path=final_path,
                    file_size=file_size,
                    content_text=text_content,
                    content_hash=content_hash,
                    is_active=True
                )
                
                db.session.add(marking_guide)
                db.session.commit()
                
                logger.info(f"Marking guide uploaded successfully: {marking_guide.id}")
                
                return {
                    'success': True,
                    'guide_id': marking_guide.id,
                    'title': title,
                    'filename': original_filename,
                    'file_size': file_size,
                    'content_hash': content_hash,
                    'text_length': len(text_content) if text_content else 0,
                    'confidence': confidence,
                    'message': 'Marking guide uploaded successfully'
                }
                
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e
                
        except Exception as e:
            logger.error(f"Error uploading marking guide: {e}")
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}',
                'code': 'UPLOAD_ERROR'
            }
    
    def get_duplicate_info(self, content_hash: str, check_type: str, 
                          user_id: str) -> Dict[str, Any]:
        """Get information about existing files with the same content hash.
        
        Args:
            content_hash: Content hash to search for
            check_type: 'submission' or 'marking_guide'
            user_id: User ID for scoping
            
        Returns:
            Information about duplicate files
        """
        try:
            if check_type == 'submission':
                return self.content_validator.check_submission_duplicate(
                    content_hash, user_id
                )
            elif check_type == 'marking_guide':
                return self.content_validator.check_marking_guide_duplicate(
                    content_hash, user_id
                )
            else:
                return {
                    'success': False,
                    'error': f'Invalid check_type: {check_type}'
                }
        except Exception as e:
            logger.error(f"Error getting duplicate info: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_temp_files(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """Clean up temporary files older than specified age.
        
        Args:
            max_age_hours: Maximum age of temp files in hours
            
        Returns:
            Cleanup result
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            cleaned_files = []
            
            # Check both upload folders
            for folder in [self.submissions_folder, self.guides_folder]:
                for file_path in folder.glob('temp_*'):
                    if file_path.is_file():
                        file_age = current_time - file_path.stat().st_mtime
                        if file_age > max_age_seconds:
                            try:
                                file_path.unlink()
                                cleaned_files.append(str(file_path))
                            except Exception as e:
                                logger.warning(f"Could not delete temp file {file_path}: {e}")
            
            return {
                'success': True,
                'cleaned_files': cleaned_files,
                'count': len(cleaned_files)
            }
            
        except Exception as e:
            logger.error(f"Error cleaning temp files: {e}")
            return {
                'success': False,
                'error': str(e)
            }