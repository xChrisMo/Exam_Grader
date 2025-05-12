"""
OCR Service for processing image-based submissions using HandwritingOCR API.
"""
import os
import json
import time
import requests
from typing import Dict, List, Optional, Tuple, Union, BinaryIO
from pathlib import Path
import mimetypes
from datetime import datetime
from utils.logger import logger
from src.services.progress_tracker import progress_tracker

class OCRServiceError(Exception):
    """Exception raised for errors in the OCR service."""
    pass

class OCRService:
    """OCR service that uses HandwritingOCR API for text extraction."""

    def __init__(self, api_key=None, base_url=None):
        """Initialize with API key and base URL."""
        self.api_key = api_key or os.getenv('HANDWRITING_OCR_API_KEY')
        if not self.api_key:
            raise OCRServiceError("HandwritingOCR API key not configured")

        self.base_url = base_url or os.getenv('HANDWRITING_OCR_API_URL', 'https://www.handwritingocr.com/api/v3')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }
        logger.info("OCR service initialized successfully")

    def _validate_file(self, file_path: Union[str, Path]) -> None:
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

    def extract_text_from_image(self, file: Union[str, Path, BinaryIO], tracker_id: Optional[str] = None) -> Tuple[str, str]:
        """
        Extract text from an image using OCR.

        Args:
            file: Path to the image file or file object
            tracker_id: Optional progress tracker ID for monitoring progress

        Returns:
            Tuple[str, str]: (Extracted text, Tracker ID)

        Raises:
            OCRServiceError: If OCR processing fails
        """
        # Create a progress tracker if not provided
        if not tracker_id:
            tracker_id = progress_tracker.create_tracker(
                operation_type="ocr",
                task_name="Image Text Extraction",
                total_steps=4
            )

        try:
            # Step 1: Upload the document to process
            document_id = self._upload_document(file)

            # Log progress instead of updating tracker
            logger.info("Uploading document for OCR processing...")

            # Step 2: Wait for processing to complete
            max_retries = 10
            retry_delay = 2  # seconds

            for attempt in range(max_retries):
                status = self._get_document_status(document_id)

                if status == "processed":
                    break
                elif status == "failed":
                    # Log error instead of updating tracker
                    logger.error("OCR processing failed on the server")
                    raise OCRServiceError("OCR processing failed")

                # Log progress instead of updating tracker
                logger.info(f"OCR processing in progress (attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)
            else:
                # Log error instead of updating tracker
                logger.error("OCR processing timed out after multiple attempts")
                raise OCRServiceError("OCR processing timed out")

            # Log progress instead of updating tracker
            logger.info("Retrieving OCR results...")

            # Step 3: Get the results
            text = self._get_document_result(document_id)

            # Log completion instead of updating tracker
            logger.info(f"OCR processing completed successfully. Extracted {len(text)} characters.")

            return text, tracker_id

        except requests.exceptions.RequestException as e:
            # Update progress - Network error
            progress_tracker.update_progress(
                tracker_id=tracker_id,
                status="failed",
                message=f"Network error during OCR request: {str(e)}",
                completed=True,
                success=False,
                error=f"Network error: {str(e)}"
            )
            raise OCRServiceError(f"Network error during OCR request: {str(e)}")
        except Exception as e:
            # Update progress - General error
            progress_tracker.update_progress(
                tracker_id=tracker_id,
                status="failed",
                message=f"OCR processing failed: {str(e)}",
                completed=True,
                success=False,
                error=str(e)
            )
            raise OCRServiceError(f"OCR processing failed: {str(e)}")

    def _upload_document(self, file: Union[str, Path, BinaryIO]) -> str:
        """
        Upload document for OCR processing.

        Args:
            file: Path to the document file or file object

        Returns:
            str: Document ID
        """
        try:
            # Handle both file paths and file objects
            if isinstance(file, (str, Path)):
                self._validate_file(file)
                files = {'file': open(file, 'rb')}
            else:
                filename = getattr(file, 'name', 'document.jpg')
                files = {'file': (filename, file)}

            # Include required processing action
            data = {
                'action': 'transcribe',  # Per API docs: Extract all text from the document
                'delete_after': 3600  # Auto-delete after 1 hour
            }

            # Upload the file
            response = requests.post(
                f"{self.base_url}/documents",
                headers=self.headers,
                files=files,
                data=data,
                timeout=30
            )

            # Check for errors
            if response.status_code != 201:  # API returns 201 Created on success
                error_msg = f"Failed to upload document: {response.status_code}"
                try:
                    error_details = response.json()
                    if isinstance(error_details, dict) and 'error' in error_details:
                        error_msg += f" - {error_details['error']}"
                except:
                    error_msg += f" - {response.text}"
                raise OCRServiceError(error_msg)

            # Get the document ID
            response_data = response.json()
            document_id = response_data.get('id')

            if not document_id:
                raise OCRServiceError("No document ID returned from API")

            logger.info(f"Document uploaded successfully, ID: {document_id}")
            return document_id

        finally:
            # Close the file if we opened it
            if isinstance(file, (str, Path)) and 'files' in locals():
                files['file'].close()

    def _get_document_status(self, document_id: str) -> str:
        """
        Get document processing status.

        Args:
            document_id: Document ID

        Returns:
            str: Document status (new, processing, processed, failed)
        """
        response = requests.get(
            f"{self.base_url}/documents/{document_id}",
            headers=self.headers,
            timeout=10
        )

        if response.status_code != 200:
            raise OCRServiceError(f"Failed to get document status: {response.status_code} - {response.text}")

        result = response.json()
        return result.get('status', 'unknown')

    def _get_document_result(self, document_id: str) -> str:
        """
        Get OCR results for a document.

        Args:
            document_id: Document ID

        Returns:
            str: Extracted text
        """
        # Request the JSON format
        response = requests.get(
            f"{self.base_url}/documents/{document_id}.json",
            headers=self.headers,
            timeout=10
        )

        if response.status_code != 200:
            raise OCRServiceError(f"Failed to get document result: {response.status_code} - {response.text}")

        result = response.json()

        # Extract text from the response based on API format
        if 'results' in result:
            # Combine text from all pages
            text = ""
            for page in result.get('results', []):
                if 'transcript' in page:
                    text += page.get('transcript', '') + "\n"
            return text.strip()
        else:
            raise OCRServiceError("Unexpected response format from OCR service")
