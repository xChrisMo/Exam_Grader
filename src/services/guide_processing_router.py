"""
Guide Processing Router

This module routes marking guides to appropriate processing pipelines based on
file type, user preferences, and system configuration.
"""

import os
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional

from src.config.unified_config import config
from utils.logger import logger


class ProcessingMethod(Enum):
    """Available processing methods for marking guides."""
    DIRECT_LLM = "direct_llm"
    TRADITIONAL_OCR = "traditional_ocr"
    AUTO_SELECT = "auto_select"


@dataclass
class ProcessingResult:
    """Result of guide processing operation."""
    success: bool
    processing_method: str
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    fallback_used: bool = False
    metadata: Optional[Dict[str, Any]] = None


class GuideProcessingRouter:
    """Routes marking guides to appropriate processing pipeline."""
    
    def __init__(self):
        """Initialize the guide processing router."""
        self.direct_llm_enabled = os.getenv("ENABLE_DIRECT_LLM_GUIDE_PROCESSING", "true").lower() == "true"
        self.default_method = ProcessingMethod(os.getenv("DEFAULT_GUIDE_PROCESSING_METHOD", "direct_llm"))
        self.allow_method_selection = os.getenv("ALLOW_GUIDE_PROCESSING_METHOD_SELECTION", "true").lower() == "true"
        
        # Supported formats for direct LLM processing
        self.llm_supported_formats = {
            '.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'
        }
        
        # File size limits (in MB)
        self.max_file_size_mb = int(os.getenv("LLM_VISION_MAX_FILE_SIZE", "20").replace("MB", ""))
        
        logger.info(f"GuideProcessingRouter initialized - Direct LLM: {self.direct_llm_enabled}, Default: {self.default_method.value}")
    
    def determine_processing_method(self, file_info: Dict[str, Any], user_preference: Optional[str] = None) -> ProcessingMethod:
        """
        Determine the best processing method for a guide file.
        
        Args:
            file_info: Dictionary containing file metadata (path, size, type, etc.)
            user_preference: Optional user-specified processing method
            
        Returns:
            ProcessingMethod enum indicating the chosen method
        """
        try:
            # Check if direct LLM processing is enabled
            if not self.direct_llm_enabled:
                logger.info("Direct LLM processing disabled, using traditional OCR")
                return ProcessingMethod.TRADITIONAL_OCR
            
            # Honor user preference if allowed and valid
            if user_preference and self.allow_method_selection:
                try:
                    preferred_method = ProcessingMethod(user_preference)
                    if self._is_method_viable(preferred_method, file_info):
                        logger.info(f"Using user-preferred method: {preferred_method.value}")
                        return preferred_method
                    else:
                        logger.warning(f"User preference {user_preference} not viable for file, using auto-selection")
                except ValueError:
                    logger.warning(f"Invalid user preference: {user_preference}, using auto-selection")
            
            # Auto-select based on file characteristics
            return self._auto_select_method(file_info)
            
        except Exception as e:
            logger.error(f"Error determining processing method: {e}")
            return ProcessingMethod.TRADITIONAL_OCR  # Safe fallback
    
    def _auto_select_method(self, file_info: Dict[str, Any]) -> ProcessingMethod:
        """
        Automatically select the best processing method based on file characteristics.
        
        Args:
            file_info: Dictionary containing file metadata
            
        Returns:
            ProcessingMethod enum
        """
        file_path = file_info.get('path', '')
        file_size = file_info.get('size', 0)
        
        # Get file extension
        file_ext = Path(file_path).suffix.lower()
        
        # Check file size limits
        file_size_mb = file_size / (1024 * 1024) if file_size else 0
        if file_size_mb > self.max_file_size_mb:
            logger.info(f"File size {file_size_mb:.1f}MB exceeds limit {self.max_file_size_mb}MB, using traditional OCR")
            return ProcessingMethod.TRADITIONAL_OCR
        
        # Check if format is supported by LLM vision
        if file_ext not in self.llm_supported_formats:
            logger.info(f"File format {file_ext} not supported by LLM vision, using traditional OCR")
            return ProcessingMethod.TRADITIONAL_OCR
        
        # Prefer direct LLM for image files and complex documents
        if file_ext in {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif'}:
            logger.info("Image file detected, using direct LLM processing")
            return ProcessingMethod.DIRECT_LLM
        
        if file_ext in {'.pdf', '.docx', '.doc'}:
            # For document files, use direct LLM if it's the default
            if self.default_method == ProcessingMethod.DIRECT_LLM:
                logger.info("Document file with direct LLM as default, using direct LLM processing")
                return ProcessingMethod.DIRECT_LLM
        
        # Default to configured default method
        logger.info(f"Using default processing method: {self.default_method.value}")
        return self.default_method
    
    def _is_method_viable(self, method: ProcessingMethod, file_info: Dict[str, Any]) -> bool:
        """
        Check if a processing method is viable for the given file.
        
        Args:
            method: Processing method to check
            file_info: File metadata
            
        Returns:
            True if method is viable, False otherwise
        """
        if method == ProcessingMethod.TRADITIONAL_OCR:
            return True  # Traditional OCR can handle any file
        
        if method == ProcessingMethod.DIRECT_LLM:
            if not self.direct_llm_enabled:
                return False
            
            file_path = file_info.get('path', '')
            file_size = file_info.get('size', 0)
            
            # Check file format
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.llm_supported_formats:
                return False
            
            # Check file size
            file_size_mb = file_size / (1024 * 1024) if file_size else 0
            if file_size_mb > self.max_file_size_mb:
                return False
            
            return True
        
        return False
    
    def route_guide_processing(self, guide_id: str, file_path: str, options: Dict[str, Any]) -> ProcessingResult:
        """
        Route guide processing to the appropriate pipeline.
        
        Args:
            guide_id: Unique identifier for the guide
            file_path: Path to the guide file
            options: Processing options including user preferences
            
        Returns:
            ProcessingResult with processing outcome
        """
        import time
        start_time = time.time()
        
        try:
            # Gather file information
            file_info = self._gather_file_info(file_path)
            file_info['guide_id'] = guide_id
            
            # Determine processing method
            user_preference = options.get('processing_method')
            processing_method = self.determine_processing_method(file_info, user_preference)
            
            logger.info(f"Routing guide {guide_id} to {processing_method.value} processing")
            
            # Route to appropriate processor
            if processing_method == ProcessingMethod.DIRECT_LLM:
                result = self._process_with_direct_llm(file_path, file_info, options)
            else:
                result = self._process_with_traditional_ocr(file_path, file_info, options)
            
            # Update result with routing metadata
            result.processing_method = processing_method.value
            result.processing_time = time.time() - start_time
            
            if not result.metadata:
                result.metadata = {}
            result.metadata.update({
                'routing_method': processing_method.value,
                'file_info': file_info,
                'processing_options': options
            })
            
            logger.info(f"Guide {guide_id} processing completed in {result.processing_time:.2f}s using {processing_method.value}")
            return result
            
        except Exception as e:
            logger.error(f"Error routing guide processing for {guide_id}: {e}")
            return ProcessingResult(
                success=False,
                processing_method="error",
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    def _gather_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Gather information about the file for processing decisions.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file metadata
        """
        try:
            path_obj = Path(file_path)
            
            file_info = {
                'path': file_path,
                'name': path_obj.name,
                'extension': path_obj.suffix.lower(),
                'exists': path_obj.exists()
            }
            
            if path_obj.exists():
                stat = path_obj.stat()
                file_info.update({
                    'size': stat.st_size,
                    'size_mb': stat.st_size / (1024 * 1024),
                    'modified_time': stat.st_mtime
                })
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error gathering file info for {file_path}: {e}")
            return {
                'path': file_path,
                'name': Path(file_path).name,
                'extension': Path(file_path).suffix.lower(),
                'exists': False,
                'error': str(e)
            }
    
    def _process_with_direct_llm(self, file_path: str, file_info: Dict[str, Any], options: Dict[str, Any]) -> ProcessingResult:
        """
        Process guide using direct LLM method.
        
        Args:
            file_path: Path to the guide file
            file_info: File metadata
            options: Processing options
            
        Returns:
            ProcessingResult
        """
        try:
            # Import here to avoid circular dependencies
            from src.services.direct_llm_guide_processor import DirectLLMGuideProcessor
            
            processor = DirectLLMGuideProcessor()
            return processor.process_guide_directly(file_path, file_info, options)
            
        except ImportError:
            logger.warning("DirectLLMGuideProcessor not available, falling back to traditional OCR")
            return self._process_with_traditional_ocr(file_path, file_info, options)
        except Exception as e:
            logger.error(f"Direct LLM processing failed: {e}")
            # Try fallback if enabled
            if options.get('enable_fallback', True):
                logger.info("Attempting fallback to traditional OCR")
                fallback_result = self._process_with_traditional_ocr(file_path, file_info, options)
                fallback_result.fallback_used = True
                return fallback_result
            else:
                return ProcessingResult(
                    success=False,
                    processing_method="direct_llm",
                    error_message=f"Direct LLM processing failed: {str(e)}"
                )
    
    def _process_with_traditional_ocr(self, file_path: str, file_info: Dict[str, Any], options: Dict[str, Any]) -> ProcessingResult:
        """
        Process guide using traditional OCR method.
        
        Args:
            file_path: Path to the guide file
            file_info: File metadata
            options: Processing options
            
        Returns:
            ProcessingResult
        """
        try:
            # Import here to avoid circular dependencies
            from src.services.file_processing_service import FileProcessingService
            
            processor = FileProcessingService()
            
            # Prepare file info for traditional processing
            traditional_file_info = {
                'path': file_path,
                'name': file_info.get('name', ''),
                'size': file_info.get('size', 0),
                'type': file_info.get('extension', ''),
                'user_id': options.get('user_id'),
                'request_id': options.get('request_id', f"guide_proc_{int(time.time())}")
            }
            
            # Process using traditional method
            result = processor.process_file_with_fallback(file_path, traditional_file_info)
            
            # Convert to ProcessingResult format
            return ProcessingResult(
                success=result.get('success', False),
                processing_method="traditional_ocr",
                data=result,
                error_message=result.get('error_message') if not result.get('success') else None
            )
            
        except Exception as e:
            logger.error(f"Traditional OCR processing failed: {e}")
            return ProcessingResult(
                success=False,
                processing_method="traditional_ocr",
                error_message=f"Traditional OCR processing failed: {str(e)}"
            )
    
    def get_supported_formats(self, method: ProcessingMethod) -> set:
        """
        Get supported file formats for a processing method.
        
        Args:
            method: Processing method
            
        Returns:
            Set of supported file extensions
        """
        if method == ProcessingMethod.DIRECT_LLM:
            return self.llm_supported_formats.copy()
        elif method == ProcessingMethod.TRADITIONAL_OCR:
            # Traditional OCR supports more formats
            return {'.pdf', '.docx', '.doc', '.txt', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif', '.rtf', '.html'}
        else:
            return set()
    
    def get_processing_capabilities(self) -> Dict[str, Any]:
        """
        Get current processing capabilities and configuration.
        
        Returns:
            Dictionary with capability information
        """
        return {
            'direct_llm_enabled': self.direct_llm_enabled,
            'default_method': self.default_method.value,
            'allow_method_selection': self.allow_method_selection,
            'max_file_size_mb': self.max_file_size_mb,
            'llm_supported_formats': list(self.llm_supported_formats),
            'available_methods': [method.value for method in ProcessingMethod]
        }


# Global instance for easy access
guide_processing_router = GuideProcessingRouter()