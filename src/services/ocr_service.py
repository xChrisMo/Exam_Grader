"""
OCR Service for processing image-based submissions.
This is a patched version that works without requiring an API key.
"""
import os
import json
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import mimetypes
from datetime import datetime

class OCRServiceError(Exception):
    """Exception raised for errors in the OCR service."""
    pass

class OCRService:
    """Patched OCR service that doesn't require an API key."""
    
    def __init__(self, api_key=None, base_url=None):
        """Initialize with or without API key."""
        # We don't need an API key for this patch
        pass
        
    def _validate_file(self, file_path: str) -> None:
        """
        Validate file exists and is within size limits.
        
        Args:
            file_path: Path to the file to validate
            
        Raises:
            OCRServiceError: If file validation fails
        """
        if not os.path.exists(file_path):
            raise OCRServiceError(f"File not found: {file_path}")
            
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB
        if file_size > 20:
            raise OCRServiceError(f"File size ({file_size:.1f}MB) exceeds 20MB limit")
            
        ext = Path(file_path).suffix.lower()
        supported_formats = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']
        if ext not in supported_formats:
            raise OCRServiceError(f"Unsupported file format: {ext}")
    
    def upload_document(self, file_path: str, delete_after: int = 3600) -> Dict:
        """
        Simulate document upload for OCR processing.
        
        Args:
            file_path: Path to the document file
            delete_after: Seconds until auto-deletion (not used in this patch)
            
        Returns:
            Dict containing document ID and status
        """
        self._validate_file(file_path)
        
        # Generate a simulated document ID
        doc_id = f"simulated_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return {
            "id": doc_id,
            "status": "processed",
            "file_name": Path(file_path).name,
            "page_count": 1,
            "action": "transcribe"
        }
        
    def get_document_status(self, document_id: str) -> Dict:
        """
        Get document status from patched OCR service.
        
        Args:
            document_id: Document ID
            
        Returns:
            Dict containing document status
        """
        return {
            "id": document_id,
            "status": "processed"
        }
        
    def get_document_result(self, document_id: str) -> Dict:
        """
        Get OCR results for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Dict containing OCR results
        """
        return {
            "id": document_id,
            "status": "processed",
            "text": "This is simulated OCR text extracted from the document.",
            "pages": [
                {
                    "page_num": 1,
                    "text": "This is simulated OCR text extracted from the document.",
                    "confidence": 0.95
                }
            ]
        }
