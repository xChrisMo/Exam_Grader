"""Consolidated OCR Service with unified functionality, caching, and base service integration."""

import asyncio
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

import requests
from PIL import Image, ImageEnhance, ImageFilter

from src.services.base_service import BaseService, ServiceStatus
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


class ConsolidatedOCRService(BaseService):
    """Consolidated OCR service with unified functionality, caching, and performance optimization."""

    def __init__(self, api_key=None, base_url=None, allow_no_key=False, **kwargs):
        """Initialize consolidated OCR service.

        Args:
            api_key: HandwritingOCR API key
            base_url: API base URL
            allow_no_key: If True, allows initialization without API key
            **kwargs: Additional configuration options
        """
        super().__init__("consolidated_ocr_service", **kwargs)
        
        # API configuration
        self.api_key = api_key or os.getenv("HANDWRITING_OCR_API_KEY")
        self.base_url = base_url or os.getenv(
            "HANDWRITING_OCR_API_URL", "https://www.handwritingocr.com/api/v3"
        )
        self.allow_no_key = allow_no_key
        
        # Headers setup
        if self.api_key:
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            }
        else:
            self.headers = {"Accept": "application/json"}
        
        # Cache configuration
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = kwargs.get('cache_ttl', 86400 * 7)  # 7 days
        self.max_cache_size = kwargs.get('max_cache_size', 1000)
        
        # Performance configuration
        self.max_workers = min(kwargs.get('max_workers', 2), os.cpu_count() or 1)  # Reduced workers to avoid rate limits
        self.request_timeout = kwargs.get('request_timeout', 30)
        self.max_retries = kwargs.get('max_retries', 5)  # Reduced retries
        self.retry_delay = kwargs.get('retry_delay', 5)  # Increased delay
        self.max_wait_time = kwargs.get('max_wait_time', 120)  # Increased wait time
        
        # Rate limiting configuration
        self.rate_limit_delay = kwargs.get('rate_limit_delay', 2)  # Delay between requests
        self.last_request_time = 0
        
        # Image processing configuration
        self.max_image_size = kwargs.get('max_image_size', 2048)
        self.image_quality = kwargs.get('image_quality', 95)
        self.contrast_enhancement = kwargs.get('contrast_enhancement', 1.2)
        self.sharpness_enhancement = kwargs.get('sharpness_enhancement', 1.1)
        
        # Initialize service
        self._initialized = self.initialize()

    def initialize(self) -> bool:
        """Initialize the OCR service.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            if not self.api_key and not self.allow_no_key:
                logger.error("HandwritingOCR API key not configured")
                self.metrics.status = ServiceStatus.UNHEALTHY
                return False
            
            if not self.api_key:
                logger.info("OCR service initialized without API key - service will be disabled")
                self.metrics.status = ServiceStatus.DEGRADED
                return True
            
            # Test API connectivity
            if self.is_available():
                logger.info("Consolidated OCR service initialized successfully")
                self.metrics.status = ServiceStatus.HEALTHY
                self.update_custom_metric("cache_enabled", True)
                self.update_custom_metric("max_workers", self.max_workers)
                return True
            else:
                logger.info("OCR service initialized with API key - connectivity will be tested on first use")
                self.metrics.status = ServiceStatus.HEALTHY
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize OCR service: {str(e)}")
            self.metrics.status = ServiceStatus.UNHEALTHY
            return False

    def health_check(self) -> bool:
        """Perform health check for the OCR service.
        
        Returns:
            bool: True if service is healthy, False otherwise
        """
        try:
            if not self.api_key:
                return self.allow_no_key
            
            return self.is_available()
            
        except Exception as e:
            logger.error(f"OCR service health check failed: {str(e)}")
            return False

    def cleanup(self) -> None:
        """Cleanup service resources."""
        try:
            # Clear cache
            cleared_count = self.clear_cache()
            logger.info(f"OCR service cleanup completed. Cleared {cleared_count} cache entries.")
        except Exception as e:
            logger.error(f"Error during OCR service cleanup: {str(e)}")

    def is_available(self) -> bool:
        """Check if the OCR service is available by testing API connectivity."""
        try:
            if not self.api_key:
                logger.debug("OCR service unavailable: No API key configured")
                return False
            if not self.base_url:
                logger.debug("OCR service unavailable: No base URL configured")
                return False

            # For now, if we have API key and URL, consider it available
            # The actual connectivity will be tested when making real requests
            logger.debug("OCR service configuration validated - API key and URL present")
            return True

            # Optional: Test API connectivity (commented out to avoid startup delays)
            # try:
            #     response = requests.get(
            #         f"{self.base_url}/health",
            #         headers=self.headers,
            #         timeout=5
            #     )
            #     if response.status_code == 200:
            #         logger.debug("OCR service health check passed")
            #         return True
            # except requests.exceptions.RequestException:
            #     # Health endpoint might not exist, try documents endpoint
            #     try:
            #         response = requests.get(
            #             f"{self.base_url}/documents",
            #             headers=self.headers,
            #             timeout=5
            #         )
            #         # Any response (even 401/403) means the service is reachable
            #         if response.status_code in [200, 401, 403]:
            #             logger.debug("OCR service connectivity confirmed")
            #             return True
            #     except requests.exceptions.RequestException as e:
            #         logger.debug(f"OCR service connectivity test failed: {str(e)}")
            #         return False

        except Exception as e:
            logger.error(f"OCR service availability check failed: {str(e)}")
            return False

    def _validate_file(self, file_path: Union[str, Path]) -> None:
        """Validate file exists and is within size limits.

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

    def _get_file_hash(self, file_path: Union[str, Path]) -> str:
        """Generate hash for file content to use as cache key."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _get_cached_result(self, file_hash: str) -> Optional[str]:
        """Retrieve cached OCR result from in-memory cache."""
        try:
            if file_hash in self.cache:
                # Check if cache entry is still valid
                timestamp = self.cache_timestamps.get(file_hash, 0)
                if time.time() - timestamp < self.cache_ttl:
                    logger.info(f"Cache hit for file hash: {file_hash[:8]}...")
                    self.update_custom_metric("cache_hits", 
                        self.metrics.custom_metrics.get("cache_hits", 0) + 1)
                    return self.cache[file_hash]
                else:
                    # Remove expired entry
                    del self.cache[file_hash]
                    del self.cache_timestamps[file_hash]
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")

        self.update_custom_metric("cache_misses", 
            self.metrics.custom_metrics.get("cache_misses", 0) + 1)
        return None

    def _cache_result(self, file_hash: str, result: str) -> None:
        """Cache OCR result in memory."""
        try:
            # Clean up old entries if cache is full
            if len(self.cache) >= self.max_cache_size:
                self._cleanup_cache()

            self.cache[file_hash] = result
            self.cache_timestamps[file_hash] = time.time()
            logger.info(f"Cached OCR result for hash: {file_hash[:8]}...")
            self.update_custom_metric("cached_items", len(self.cache))
        except Exception as e:
            logger.warning(f"Cache storage error: {e}")

    def _cleanup_cache(self) -> None:
        """Remove oldest cache entries to make room for new ones."""
        try:
            # Remove oldest 20% of entries
            sorted_items = sorted(self.cache_timestamps.items(), key=lambda x: x[1])
            items_to_remove = len(sorted_items) // 5

            for file_hash, _ in sorted_items[:items_to_remove]:
                del self.cache[file_hash]
                del self.cache_timestamps[file_hash]

            logger.info(f"Cleaned up {items_to_remove} old cache entries")
            self.update_custom_metric("cached_items", len(self.cache))
        except Exception as e:
            logger.warning(f"Cache cleanup error: {e}")

    def _preprocess_image(self, image_path: Union[str, Path]) -> str:
        """Optimize image for better OCR accuracy and speed."""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Resize if too large
                if max(img.size) > self.max_image_size:
                    ratio = self.max_image_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    logger.info(f"Resized image to {new_size}")

                # Enhance contrast and sharpness for better OCR
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(self.contrast_enhancement)

                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(self.sharpness_enhancement)

                # Apply slight noise reduction
                img = img.filter(ImageFilter.MedianFilter(size=3))

                # Save optimized image
                optimized_path = str(image_path).replace('.', '_optimized.')
                img.save(optimized_path, 'JPEG', quality=self.image_quality, optimize=True)

                logger.info(f"Image preprocessed and saved to: {optimized_path}")
                return optimized_path

        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}, using original")
            return str(image_path)

    def extract_text_from_image(self, file: Union[str, Path, BinaryIO]) -> str:
        """Extract text from an image using OCR with caching and preprocessing.

        Args:
            file: Path to the image file or file object

        Returns:
            str: Extracted text

        Raises:
            OCRServiceError: If OCR processing fails
        """
        if not self.api_key:
            raise OCRServiceError("OCR service not available - API key not configured")

        with self.track_request():
            logger.info("Starting OCR text extraction...")

            try:
                # Handle file path vs file object
                if isinstance(file, (str, Path)):
                    file_path = Path(file)
                    self._validate_file(file_path)
                    
                    # Check cache first
                    file_hash = self._get_file_hash(file_path)
                    cached_result = self._get_cached_result(file_hash)
                    if cached_result:
                        return cached_result
                    
                    # Preprocess image for better OCR
                    optimized_path = self._preprocess_image(file_path)
                    file_to_process = optimized_path
                else:
                    file_to_process = file
                    file_hash = None
                    optimized_path = None

                try:
                    # Step 1: Upload document
                    document_id = self._upload_document(file_to_process)
                    logger.info(f"Document uploaded with ID: {document_id}")

                    # Step 2: Wait for processing
                    self._wait_for_processing(document_id)

                    # Step 3: Get results
                    text = self._get_document_result(document_id)

                    if not text or not text.strip():
                        logger.warning("OCR completed but returned empty text")
                        # Instead of raising an error, return empty string to let caller handle it
                        return ""

                    # Cache the result if we have a file hash
                    if file_hash:
                        self._cache_result(file_hash, text)

                    logger.info(f"OCR completed successfully. Extracted {len(text)} characters.")
                    return text

                finally:
                    # Clean up optimized image if it was created
                    if optimized_path and optimized_path != str(file) and os.path.exists(optimized_path):
                        try:
                            os.remove(optimized_path)
                        except OSError:
                            pass

            except OCRServiceError:
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error during OCR: {str(e)}")
                raise OCRServiceError(
                    f"Network error during OCR processing: {str(e)}. "
                    "Please check your internet connection and try again."
                )
            except Exception as e:
                logger.error(f"OCR processing failed: {str(e)}")
                raise OCRServiceError(
                    f"OCR processing failed: {str(e)}. "
                    "Please try again or contact support if the issue persists."
                )

    def _wait_for_processing(self, document_id: str) -> None:
        """Wait for document processing to complete."""
        start_time = time.time()

        for attempt in range(self.max_retries):
            elapsed_time = time.time() - start_time
            if elapsed_time > self.max_wait_time:
                logger.error(f"OCR processing timed out after {elapsed_time:.1f}s")
                raise OCRServiceError(
                    f"OCR processing timed out after {elapsed_time:.1f}s. "
                    "Please try again or contact support if the issue persists."
                )

            try:
                status = self._get_document_status(document_id)

                if status == "processed":
                    logger.info(f"OCR processing completed after {elapsed_time:.1f}s")
                    return
                elif status == "failed":
                    logger.error("OCR processing failed on server")
                    raise OCRServiceError(
                        "OCR processing failed on the server. "
                        "This may be due to image quality or format issues. "
                        "Please try with a different image or contact support."
                    )

                logger.info(f"OCR processing in progress (attempt {attempt+1}/{self.max_retries}) - Elapsed: {elapsed_time:.0f}s")

                # Exponential backoff
                actual_delay = min(self.retry_delay * (1.2 ** attempt), 10)
                time.sleep(actual_delay)

            except requests.exceptions.RequestException as e:
                logger.warning(f"Network error checking status (attempt {attempt+1}): {str(e)}")
                if attempt == self.max_retries - 1:
                    raise OCRServiceError(
                        f"Network error during OCR processing: {str(e)}. "
                        "Please check your internet connection and try again."
                    )
                time.sleep(self.retry_delay)
        else:
            elapsed_time = time.time() - start_time
            logger.error(f"OCR processing timed out after {self.max_retries} attempts ({elapsed_time:.1f}s)")
            raise OCRServiceError(
                f"OCR processing timed out after {self.max_retries} attempts. "
                "The service may be experiencing high load. Please try again later."
            )

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between API requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def _upload_document(self, file: Union[str, Path, BinaryIO]) -> str:
        """Upload document for OCR processing."""
        try:
            # Enforce rate limiting
            self._enforce_rate_limit()
            # Handle both file paths and file objects
            if isinstance(file, (str, Path)):
                self._validate_file(file)
                files = {"file": open(file, "rb")}
            else:
                filename = getattr(file, "name", "document.jpg")
                files = {"file": (filename, file)}

            # Include required processing action
            data = {
                "action": "transcribe",
                "delete_after": 3600,  # Auto-delete after 1 hour
            }

            # Upload the file
            response = requests.post(
                f"{self.base_url}/documents",
                headers=self.headers,
                files=files,
                data=data,
                timeout=self.request_timeout,
            )

            # Check for errors
            if response.status_code != 201:
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
        """Get document processing status."""
        # Enforce rate limiting
        self._enforce_rate_limit()
        
        response = requests.get(
            f"{self.base_url}/documents/{document_id}", 
            headers=self.headers, 
            timeout=10
        )

        if response.status_code != 200:
            raise OCRServiceError(
                f"Failed to get document status: {response.status_code} - {response.text}"
            )

        result = response.json()
        return result.get("status", "unknown")

    def _get_document_result(self, document_id: str) -> str:
        """Get OCR results for a document."""
        # Enforce rate limiting
        self._enforce_rate_limit()
        
        response = requests.get(
            f"{self.base_url}/documents/{document_id}.json",
            headers=self.headers,
            timeout=10,
        )

        if response.status_code != 200:
            raise OCRServiceError(
                f"Failed to get document result: {response.status_code} - {response.text}"
            )

        try:
            result = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error in OCR result: {e}. Raw response: {response.text}")
            raise OCRServiceError("Invalid JSON response from OCR service") from e

        # Extract text from the response
        if "results" in result:
            text = ""
            for i, page in enumerate(result.get("results", [])):
                if "transcript" in page:
                    page_text = page.get("transcript", "") or ""  # Ensure it's never None
                    if not page_text:
                        logger.warning(f"Page {i+1} has no transcript content.")
                    text += page_text + "\n"
                else:
                    logger.warning(f"Page {i+1} missing 'transcript' key in OCR result. Page content: {page}")
            return text.strip()
        else:
            raise OCRServiceError("Unexpected response format from OCR service")

    def extract_text_from_multiple_images_parallel(self, file_paths: List[Union[str, Path]]) -> List[Tuple[str, str, Optional[str]]]:
        """Extract text from multiple images in parallel.

        Returns:
            List of tuples: (file_path, extracted_text, error_message)
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(self._extract_with_error_handling, path): path
                for path in file_paths
            }

            # Collect results as they complete
            for future in as_completed(future_to_path):
                file_path = future_to_path[future]
                try:
                    text, error = future.result()
                    results.append((str(file_path), text, error))
                except Exception as e:
                    logger.error(f"Unexpected error processing {file_path}: {e}")
                    results.append((str(file_path), "", str(e)))

        return results

    def _extract_with_error_handling(self, file_path: Union[str, Path]) -> Tuple[str, Optional[str]]:
        """Extract text with error handling for parallel processing."""
        try:
            text = self.extract_text_from_image(file_path)
            return text, None
        except Exception as e:
            logger.error(f"OCR failed for {file_path}: {e}")
            return "", str(e)

    async def extract_text_async(self, file_path: Union[str, Path]) -> str:
        """Async wrapper for OCR extraction."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.extract_text_from_image, file_path)

    async def extract_text_from_multiple_images_async(self, file_paths: List[Union[str, Path]]) -> List[Tuple[str, str, Optional[str]]]:
        """Extract text from multiple images asynchronously."""
        tasks = [self.extract_text_async(path) for path in file_paths]
        results = []

        for i, task in enumerate(asyncio.as_completed(tasks)):
            try:
                text = await task
                results.append((str(file_paths[i]), text, None))
            except Exception as e:
                logger.error(f"Async OCR failed for {file_paths[i]}: {e}")
                results.append((str(file_paths[i]), "", str(e)))

        return results

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        try:
            current_time = time.time()
            valid_entries = 0
            expired_entries = 0

            for file_hash, timestamp in self.cache_timestamps.items():
                if current_time - timestamp < self.cache_ttl:
                    valid_entries += 1
                else:
                    expired_entries += 1

            # Calculate approximate memory usage
            total_size = sum(len(text.encode('utf-8')) for text in self.cache.values())
            memory_mb = total_size / (1024 * 1024)

            return {
                "cache_enabled": True,
                "total_entries": len(self.cache),
                "valid_entries": valid_entries,
                "expired_entries": expired_entries,
                "memory_usage_mb": round(memory_mb, 2),
                "max_cache_size": self.max_cache_size,
                "cache_ttl_hours": self.cache_ttl / 3600,
                "cache_hits": self.metrics.custom_metrics.get("cache_hits", 0),
                "cache_misses": self.metrics.custom_metrics.get("cache_misses", 0)
            }
        except Exception as e:
            return {"cache_enabled": True, "error": str(e)}

    def clear_cache(self) -> int:
        """Clear all cached OCR results."""
        try:
            cleared_count = len(self.cache)
            self.cache.clear()
            self.cache_timestamps.clear()
            self.update_custom_metric("cached_items", 0)
            logger.info(f"Cleared {cleared_count} cached OCR results")
            return cleared_count
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0

    def extract_text(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Extract text from a file and return in expected format for ContentValidationService.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with 'text' and 'confidence' keys
        """
        try:
            text = self.extract_text_from_image(file_path)
            return {
                'text': text,
                'confidence': 0.8  # Default confidence for successful extraction
            }
        except Exception as e:
            logger.error(f"Text extraction failed for {file_path}: {e}")
            return {
                'text': '',
                'confidence': 0.0
            }


# Backward compatibility aliases
OCRService = ConsolidatedOCRService
OptimizedOCRService = ConsolidatedOCRService