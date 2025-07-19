"""
Fallback OCR service for when the main OCR API is unavailable.
This service provides basic text extraction without external dependencies.
"""

import logging
from typing import Union, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FallbackOCRService:
    """Fallback OCR service that provides basic functionality when API is unavailable."""
    
    def __init__(self):
        """Initialize fallback OCR service."""
        self.available = True
        logger.info("Fallback OCR service initialized")
    
    def is_available(self) -> bool:
        """Check if fallback service is available."""
        return self.available
    
    def extract_text_from_image(self, file_path: Union[str, Path]) -> str:
        """
        Attempt basic text extraction without external OCR API.
        
        Args:
            file_path: Path to the image or PDF file
            
        Returns:
            str: Empty string (fallback doesn't actually extract text)
            
        Raises:
            Exception: Always raises exception explaining limitation
        """
        logger.warning(f"Fallback OCR service cannot extract text from {file_path}")
        raise Exception(
            "OCR service is not available. This document appears to contain "
            "image-based content that requires OCR processing. Please check "
            "your OCR service configuration or try with a text-based document."
        )
