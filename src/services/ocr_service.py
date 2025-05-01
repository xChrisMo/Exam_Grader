"""
Handwriting OCR Service using handwritingocr.com API
"""
import os
import time
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path

import requests
from requests.exceptions import RequestException

from utils.logger import logger
from utils.retry import retry
from src.config.config_manager import ConfigManager

class OCRServiceError(Exception):
    """Custom exception for OCR service errors"""
    pass

class OCRService:
    """Service for handling OCR operations using handwritingocr.com API"""
    
    def __init__(self, api_key: str, base_url: str = "https://www.handwritingocr.com/api/v3"):
        """
        Initialize the OCR service.
        
        Args:
            api_key: HandwritingOCR.com API key
            base_url: Base URL for the API
        """
        logger.log_info(f"Initializing OCR service with base URL: {base_url}")
        if not api_key:
            logger.log_error("OCR Error", "API key is empty")
            raise ValueError("API key cannot be empty")
            
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip('/')
        
        # Set headers according to API documentation
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",  # Add Bearer prefix back
            "Accept": "application/json"
        }
        
        # Verify API key by making a test request
        try:
            logger.log_debug("Testing API connection...")
            # Try the documents endpoint directly to verify authentication
            response = requests.get(
                f"{self.base_url}/documents",  # Test documents endpoint instead of status
                headers=self.headers,
                timeout=30
            )
            
            # Log the response for debugging
            logger.log_debug(f"API Response Status: {response.status_code}")
            logger.log_debug(f"API Response Headers: {response.headers}")
            logger.log_debug(f"API Response Content: {response.text[:200]}")
            
            if response.status_code == 401:
                raise ValueError("Invalid API key - authentication failed")
            elif response.status_code == 403:
                raise ValueError("API key forbidden - check your subscription")
                
            response.raise_for_status()
            
            # Don't try to parse response as JSON if it's not JSON
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    user_info = response.json()
                    logger.log_info(f"Successfully connected to OCR service. Response: {user_info}")
                except ValueError as e:
                    logger.log_error("OCR Error", f"Invalid JSON response: {response.text}")
                    raise ValueError(f"Invalid API response format: {str(e)}")
            else:
                logger.log_info("Successfully connected to OCR service")
                
        except requests.exceptions.RequestException as e:
            logger.log_error("OCR Error", f"Failed to connect to API: {str(e)}")
            raise ValueError(f"API connection failed: {str(e)}")
        except Exception as e:
            logger.log_error("OCR Error", f"Failed to verify API key: {str(e)}")
            raise ValueError(f"Failed to initialize OCR service: {str(e)}")
            
        logger.log_info("OCR service initialized successfully")

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
        Upload a document for OCR processing.
        
        Args:
            file_path: Path to the document file
            delete_after: Seconds until auto-deletion (min 300, max 1209600)
            
        Returns:
            Dict containing document ID and status
            
        Raises:
            OCRServiceError: If upload fails
        """
        try:
            self._validate_file(file_path)
            
            # Use the same headers as initialized in __init__
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'action': 'transcribe',
                    'delete_after': str(max(300, min(delete_after, 1209600)))
                }
                
                logger.log_debug(f"Uploading document: {file_path}")
                logger.log_debug(f"Using headers: {headers}")  # Log headers being used
                
                response = requests.post(
                    f"{self.base_url}/documents",
                    headers=headers,
                    files=files,
                    data=data
                )
                
                # Log response details for debugging
                logger.log_debug(f"Upload Response Status: {response.status_code}")
                logger.log_debug(f"Upload Response Headers: {response.headers}")
                logger.log_debug(f"Upload Response Content: {response.text[:200]}")
                
                response.raise_for_status()
                result = response.json()
                logger.log_info(f"Document uploaded successfully: {result['id']}")
                return result
                
        except (IOError, RequestException) as e:
            logger.log_error("Upload Error", f"Failed to upload document: {str(e)}")
            raise OCRServiceError(f"Failed to upload document: {str(e)}")

    def get_document_status(self, document_id: str) -> Dict:
        """
        Get the processing status and results of a document.
        
        Args:
            document_id: The document's unique identifier
            
        Returns:
            Dict containing document status and results if processed
            
        Raises:
            OCRServiceError: If status check fails
        """
        try:
            logger.log_debug(f"Checking status for document: {document_id}")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            logger.log_debug(f"Using headers: {headers}")  # Log headers being used
            
            response = requests.get(
                f"{self.base_url}/documents/{document_id}",
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            logger.log_debug(f"Document status: {result['status']}")
            return result
            
        except RequestException as e:
            logger.log_error("Status Error", f"Failed to get document status: {str(e)}")
            raise OCRServiceError(f"Failed to get document status: {str(e)}")

    def get_document_text(self, document_id: str) -> str:
        """
        Get the processed text content of a document.
        
        Args:
            document_id: The document's unique identifier
            
        Returns:
            Extracted text content
            
        Raises:
            OCRServiceError: If text retrieval fails
        """
        try:
            logger.log_debug(f"Retrieving text for document: {document_id}")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            logger.log_debug(f"Using headers: {headers}")  # Log headers being used
            
            response = requests.get(
                f"{self.base_url}/documents/{document_id}.txt",
                headers=headers
            )
            response.raise_for_status()
            text = response.text
            logger.log_info(f"Retrieved text content ({len(text)} characters)")
            return text
            
        except RequestException as e:
            logger.log_error("Text Retrieval Error", f"Failed to get document text: {str(e)}")
            raise OCRServiceError(f"Failed to get document text: {str(e)}")

    def extract_text_from_image(self, file_path: str, timeout: int = 300) -> str:
        """
        Extract text from an image file using OCR.
        
        This is a convenience method that handles the complete OCR process:
        1. Validates the input file
        2. Uploads it for processing
        3. Waits for processing to complete
        4. Returns the extracted text
        
        Args:
            file_path: Path to the image file
            timeout: Maximum time to wait for processing in seconds
            
        Returns:
            str: Extracted text content
            
        Raises:
            OCRServiceError: If processing fails or times out
        """
        logger.log_info(f"Starting OCR processing for: {file_path}")
        return self.process_document(file_path, max_wait=timeout)

    def process_document(self, file_path: str, max_wait: int = 300) -> str:
        """
        Process a document and wait for results.
        
        Args:
            file_path: Path to the document file
            max_wait: Maximum time to wait for processing in seconds
            
        Returns:
            Extracted text content
            
        Raises:
            OCRServiceError: If processing fails or times out
        """
        logger.log_info(f"Processing document: {file_path}")
        
        # Upload document
        upload_result = self.upload_document(file_path)
        document_id = upload_result['id']
        
        # Wait for processing to complete
        start_time = time.time()
        while True:
            if time.time() - start_time > max_wait:
                error_msg = f"Document processing timed out after {max_wait} seconds"
                logger.log_error("Timeout Error", error_msg)
                raise OCRServiceError(error_msg)
                
            status = self.get_document_status(document_id)
            if status['status'] == 'processed':
                logger.log_info("Document processing completed successfully")
                return self.get_document_text(document_id)
            elif status['status'] == 'failed':
                error_msg = "Document processing failed"
                logger.log_error("Processing Error", error_msg)
                raise OCRServiceError(error_msg)
                
            time.sleep(5)  # Wait before checking again

    @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(requests.RequestException, OCRServiceError))
    def extract_text(self, file_path: str) -> Tuple[str, Optional[float]]:
        """
        Extract text from an image or PDF using OCR.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Tuple containing:
            - Extracted text
            - Confidence score (0-1) if available, None if not
            
        Raises:
            OCRServiceError: If OCR processing fails
        """
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                headers = {'Authorization': f'Bearer {self.api_key}'}
                
                response = requests.post(
                    self.base_url,
                    files=files,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code != 200:
                    raise OCRServiceError(f"OCR API error: {response.status_code} - {response.text}")
                    
                data = response.json()
                
                if 'error' in data:
                    raise OCRServiceError(f"OCR processing error: {data['error']}")
                    
                text = data.get('text', '').strip()
                confidence = data.get('confidence')
                
                if confidence is not None:
                    confidence = float(confidence)
                    
                logger.log_ocr_operation(file_path, True, confidence)
                return text, confidence
                
        except requests.RequestException as e:
            logger.log_ocr_operation(file_path, False)
            raise OCRServiceError(f"OCR request failed: {str(e)}")
        except Exception as e:
            logger.log_ocr_operation(file_path, False)
            raise OCRServiceError(f"OCR processing failed: {str(e)}") 