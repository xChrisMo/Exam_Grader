"""
OCR Service for processing image-based submissions using HandwritingOCR API.
"""

import json
import mimetypes
import os
import time
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Tuple, Union

import requests

from utils.logger import logger


class OCRServiceError(Exception):
    """Exception raised for errors in the OCR service."""

    def __init__(
        self, message: str, error_code: str = None, original_error: Exception = None
    ):
        """Initialize OCR service error.

        Args:
            message: Human-readable error message
            error_code: Optional error code for categorization
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.original_error = original_error

    def __str__(self):
        """Return string representation of the error."""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class OCRService:
    """OCR service that uses HandwritingOCR API for text extraction."""

    def __init__(self, api_key=None, base_url=None, allow_no_key=False):
        """
        Initialize with API key and base URL.

        Args:
            api_key: HandwritingOCR API key
            base_url: API base URL
            allow_no_key: If True, allows initialization without API key (for graceful degradation)
        """
        self.api_key = api_key or os.getenv("HANDWRITING_OCR_API_KEY")

        if not self.api_key and not allow_no_key:
            raise OCRServiceError("HandwritingOCR API key not configured")

        self.base_url = base_url or os.getenv(
            "HANDWRITING_OCR_API_URL", "https://www.handwritingocr.com/api/v3"
        )

        if self.api_key:
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            }
            logger.info("OCR service initialized successfully")
        else:
            self.headers = {"Accept": "application/json"}
            logger.warning("OCR service initialized without API key - service will be disabled")

    def is_available(self) -> bool:
        """Check if the OCR service is available by testing API connectivity."""
        try:
            # Basic configuration check
            if not self.api_key:
                logger.debug("OCR service unavailable: No API key configured")
                return False
            if not self.base_url:
                logger.debug("OCR service unavailable: No base URL configured")
                return False

            # Test API connectivity with a simple request
            try:
                import requests
                response = requests.get(
                    f"{self.base_url}/health",  # Try health endpoint first
                    headers=self.headers,
                    timeout=5
                )
                if response.status_code == 200:
                    logger.debug("OCR service health check passed")
                    return True
            except requests.exceptions.RequestException:
                # Health endpoint might not exist, try documents endpoint
                try:
                    response = requests.get(
                        f"{self.base_url}/documents",
                        headers=self.headers,
                        timeout=5
                    )
                    # Any response (even 401/403) means the service is reachable
                    if response.status_code in [200, 401, 403]:
                        logger.debug("OCR service connectivity confirmed")
                        return True
                except requests.exceptions.RequestException as e:
                    logger.debug(f"OCR service connectivity test failed: {str(e)}")
                    return False

            return False
        except Exception as e:
            logger.error(f"OCR service availability check failed: {str(e)}")
            return False

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
        supported_formats = [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"]
        if ext not in supported_formats:
            raise OCRServiceError(f"Unsupported file format: {ext}")

    def extract_text_from_image(self, file: Union[str, Path, BinaryIO]) -> str:
        """
        Extract text from an image using OCR with enhanced timeout handling.

        Args:
            file: Path to the image file or file object

        Returns:
            str: Extracted text

        Raises:
            OCRServiceError: If OCR processing fails
        """
        if not self.api_key:
            raise OCRServiceError("OCR service not available - API key not configured")

        logger.info("Starting OCR text extraction...")

        try:
            # Validate file if it's a path
            if isinstance(file, (str, Path)):
                self._validate_file(file)

            # Step 1: Upload document
            document_id = self._upload_document(file)
            logger.info(f"Document uploaded with ID: {document_id}")

            # Step 2: Wait for processing with improved timeout handling
            max_retries = 15
            retry_delay = 3
            max_wait_time = 60
            start_time = time.time()

            for attempt in range(max_retries):
                elapsed_time = time.time() - start_time
                if elapsed_time > max_wait_time:
                    logger.error(f"OCR processing timed out after {elapsed_time:.1f}s")
                    raise OCRServiceError(f"OCR processing timed out after {elapsed_time:.1f}s")

                try:
                    status = self._get_document_status(document_id)

                    if status == "processed":
                        logger.info(f"OCR processing completed after {elapsed_time:.1f}s")
                        break
                    elif status == "failed":
                        logger.error("OCR processing failed on server")
                        raise OCRServiceError("OCR processing failed on server")

                    logger.info(f"OCR processing in progress (attempt {attempt+1}/{max_retries}) - Elapsed: {elapsed_time:.0f}s")

                    # Exponential backoff
                    actual_delay = min(retry_delay * (1.2 ** attempt), 10)
                    time.sleep(actual_delay)

                except requests.exceptions.RequestException as e:
                    logger.warning(f"Network error checking status (attempt {attempt+1}): {str(e)}")
                    if attempt == max_retries - 1:
                        raise OCRServiceError(f"Network error during status check: {str(e)}")
                    time.sleep(retry_delay)
            else:
                elapsed_time = time.time() - start_time
                logger.error(f"OCR processing timed out after {max_retries} attempts ({elapsed_time:.1f}s)")
                raise OCRServiceError(f"OCR processing timed out after {max_retries} attempts")

            # Step 3: Get results
            text = self._get_document_result(document_id)
            logger.info(f"OCR completed successfully. Extracted {len(text)} characters.")
            return text

        except OCRServiceError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during OCR: {str(e)}")
            raise OCRServiceError(f"Network error during OCR: {str(e)}")
        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
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
                files = {"file": open(file, "rb")}
            else:
                filename = getattr(file, "name", "document.jpg")
                files = {"file": (filename, file)}

            # Include required processing action
            data = {
                "action": "transcribe",  # Per API docs: Extract all text from the document
                "delete_after": 3600,  # Auto-delete after 1 hour
            }

            # Upload the file
            response = requests.post(
                f"{self.base_url}/documents",
                headers=self.headers,
                files=files,
                data=data,
                timeout=30,
            )

            # Check for errors
            if response.status_code != 201:  # API returns 201 Created on success
                error_msg = f"Failed to upload document: {response.status_code}"
                try:
                    error_details = response.json()
                    if isinstance(error_details, dict) and "error" in error_details:
                        error_msg += f" - {error_details['error']}"
                except json.JSONDecodeError as e:
                    logger.warning(f"Could not parse error response as JSON: {str(e)}")
                    error_msg += f" - {response.text}"
                raise OCRServiceError(error_msg)

            # Get the document ID
            response_data = response.json()
            document_id = response_data.get("id")

            if not document_id:
                raise OCRServiceError("No document ID returned from API")

            logger.info(f"Document uploaded successfully, ID: {document_id}")
            return document_id

        finally:
            # Close the file if we opened it
            if isinstance(file, (str, Path)) and "files" in locals():
                files["file"].close()

    def _get_document_status(self, document_id: str) -> str:
        """
        Get document processing status.

        Args:
            document_id: Document ID

        Returns:
            str: Document status (new, processing, processed, failed)
        """
        response = requests.get(
            f"{self.base_url}/documents/{document_id}", headers=self.headers, timeout=10
        )

        if response.status_code != 200:
            raise OCRServiceError(
                f"Failed to get document status: {response.status_code} - {response.text}"
            )

        result = response.json()
        return result.get("status", "unknown")

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
            timeout=10,
        )

        if response.status_code != 200:
            raise OCRServiceError(
                f"Failed to get document result: {response.status_code} - {response.text}"
            )

        result = response.json()

        # Extract text from the response based on API format
        if "results" in result:
            # Combine text from all pages
            text = ""
            for page in result.get("results", []):
                if "transcript" in page:
                    text += page.get("transcript", "") + "\n"
            return text.strip()
        else:
            raise OCRServiceError("Unexpected response format from OCR service")
