"""Unit tests for the Consolidated OCR Service."""

import asyncio
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock
from io import BytesIO

import pytest
from PIL import Image

from src.services.consolidated_ocr_service import ConsolidatedOCRService, OCRServiceError
from src.services.base_service import ServiceStatus


class TestConsolidatedOCRService(unittest.TestCase):
    """Test cases for ConsolidatedOCRService."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_key = "test_api_key"
        self.base_url = "https://test.api.com/v3"
        
        # Create service with test configuration
        self.service = ConsolidatedOCRService(
            api_key=self.api_key,
            base_url=self.base_url,
            cache_ttl=3600,  # 1 hour for testing
            max_cache_size=10,
            max_workers=2,
            request_timeout=10,
            max_retries=3,
            retry_delay=1,
            max_wait_time=10
        )

    def test_initialization_with_api_key(self):
        """Test service initialization with API key."""
        service = ConsolidatedOCRService(
            api_key="test_key",
            base_url="https://test.com"
        )
        
        self.assertEqual(service.service_name, "consolidated_ocr_service")
        self.assertEqual(service.api_key, "test_key")
        self.assertEqual(service.base_url, "https://test.com")
        self.assertIn("Authorization", service.headers)
        self.assertEqual(service.headers["Authorization"], "Bearer test_key")

    def test_initialization_without_api_key_allowed(self):
        """Test service initialization without API key when allowed."""
        service = ConsolidatedOCRService(allow_no_key=True)
        
        self.assertIsNone(service.api_key)
        self.assertNotIn("Authorization", service.headers)
        self.assertTrue(service.allow_no_key)

    def test_initialization_without_api_key_not_allowed(self):
        """Test service initialization fails without API key when not allowed."""
        with patch.dict(os.environ, {}, clear=True):
            service = ConsolidatedOCRService(allow_no_key=False)
            self.assertEqual(service.metrics.status, ServiceStatus.UNHEALTHY)

    @patch('src.services.consolidated_ocr_service.requests.get')
    def test_is_available_success(self, mock_get):
        """Test is_available returns True when API is reachable."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.service.is_available()
        
        self.assertTrue(result)
        mock_get.assert_called_once()

    @patch('src.services.consolidated_ocr_service.requests.get')
    def test_is_available_fallback(self, mock_get):
        """Test is_available fallback to documents endpoint."""
        # First call (health) fails, second call (documents) succeeds
        mock_get.side_effect = [
            Exception("Health endpoint not found"),
            Mock(status_code=401)  # 401 means service is reachable
        ]
        
        result = self.service.is_available()
        
        self.assertTrue(result)
        self.assertEqual(mock_get.call_count, 2)

    def test_is_available_no_api_key(self):
        """Test is_available returns False when no API key."""
        service = ConsolidatedOCRService(allow_no_key=True)
        
        result = service.is_available()
        
        self.assertFalse(result)

    def test_health_check_with_api_key(self):
        """Test health check with API key."""
        with patch.object(self.service, 'is_available', return_value=True):
            result = self.service.health_check()
            self.assertTrue(result)

    def test_health_check_without_api_key(self):
        """Test health check without API key."""
        service = ConsolidatedOCRService(allow_no_key=True)
        
        result = service.health_check()
        
        self.assertTrue(result)  # Should return True when allow_no_key is True

    def test_cleanup(self):
        """Test service cleanup."""
        # Add some cache entries
        self.service.cache = {"hash1": "text1", "hash2": "text2"}
        self.service.cache_timestamps = {"hash1": time.time(), "hash2": time.time()}
        
        self.service.cleanup()
        
        self.assertEqual(len(self.service.cache), 0)
        self.assertEqual(len(self.service.cache_timestamps), 0)

    def test_validate_file_success(self):
        """Test file validation with valid file."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_file.write(b"test image data")
            tmp_file_path = tmp_file.name
        
        try:
            # Should not raise an exception
            self.service._validate_file(tmp_file_path)
        finally:
            os.unlink(tmp_file_path)

    def test_validate_file_not_found(self):
        """Test file validation with non-existent file."""
        with self.assertRaises(OCRServiceError) as context:
            self.service._validate_file("/non/existent/file.jpg")
        
        self.assertIn("File not found", str(context.exception))

    def test_validate_file_unsupported_format(self):
        """Test file validation with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(b"test data")
            tmp_file_path = tmp_file.name
        
        try:
            with self.assertRaises(OCRServiceError) as context:
                self.service._validate_file(tmp_file_path)
            
            self.assertIn("Unsupported file format", str(context.exception))
        finally:
            os.unlink(tmp_file_path)

    def test_get_file_hash(self):
        """Test file hash generation."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_file_path = tmp_file.name
        
        try:
            hash1 = self.service._get_file_hash(tmp_file_path)
            hash2 = self.service._get_file_hash(tmp_file_path)
            
            self.assertEqual(hash1, hash2)
            self.assertIsInstance(hash1, str)
            self.assertEqual(len(hash1), 64)  # SHA256 hex length
        finally:
            os.unlink(tmp_file_path)

    def test_cache_operations(self):
        """Test cache storage and retrieval."""
        file_hash = "test_hash"
        result_text = "extracted text"
        
        # Test cache miss
        cached_result = self.service._get_cached_result(file_hash)
        self.assertIsNone(cached_result)
        
        # Test cache storage
        self.service._cache_result(file_hash, result_text)
        
        # Test cache hit
        cached_result = self.service._get_cached_result(file_hash)
        self.assertEqual(cached_result, result_text)

    def test_cache_expiration(self):
        """Test cache entry expiration."""
        file_hash = "test_hash"
        result_text = "extracted text"
        
        # Cache with expired timestamp
        self.service.cache[file_hash] = result_text
        self.service.cache_timestamps[file_hash] = time.time() - self.service.cache_ttl - 1
        
        # Should return None and clean up expired entry
        cached_result = self.service._get_cached_result(file_hash)
        self.assertIsNone(cached_result)
        self.assertNotIn(file_hash, self.service.cache)

    def test_cache_cleanup(self):
        """Test cache cleanup when full."""
        # Fill cache beyond max size
        for i in range(self.service.max_cache_size + 5):
            self.service.cache[f"hash_{i}"] = f"text_{i}"
            self.service.cache_timestamps[f"hash_{i}"] = time.time() - i  # Different timestamps
        
        # Trigger cleanup
        self.service._cleanup_cache()
        
        # Should have removed oldest entries
        self.assertLess(len(self.service.cache), self.service.max_cache_size + 5)

    @patch('src.services.consolidated_ocr_service.Image.open')
    def test_preprocess_image(self, mock_image_open):
        """Test image preprocessing."""
        # Mock PIL Image
        mock_img = Mock()
        mock_img.mode = 'RGBA'
        mock_img.size = (1000, 800)
        mock_img.convert.return_value = mock_img
        mock_img.resize.return_value = mock_img
        mock_img.filter.return_value = mock_img
        
        mock_enhancer = Mock()
        mock_enhancer.enhance.return_value = mock_img
        
        mock_image_open.return_value.__enter__.return_value = mock_img
        
        with patch('src.services.consolidated_ocr_service.ImageEnhance.Contrast', return_value=mock_enhancer), \
             patch('src.services.consolidated_ocr_service.ImageEnhance.Sharpness', return_value=mock_enhancer):
            
            result_path = self.service._preprocess_image("/test/image.jpg")
            
            # Should convert to RGB
            mock_img.convert.assert_called_with('RGB')
            
            # Should enhance image
            self.assertEqual(mock_enhancer.enhance.call_count, 2)
            
            # Should save optimized image
            mock_img.save.assert_called_once()

    @patch('src.services.consolidated_ocr_service.requests.post')
    def test_upload_document_success(self, mock_post):
        """Test successful document upload."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "test_doc_id"}
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_file.write(b"test image data")
            tmp_file_path = tmp_file.name
        
        try:
            document_id = self.service._upload_document(tmp_file_path)
            
            self.assertEqual(document_id, "test_doc_id")
            mock_post.assert_called_once()
        finally:
            os.unlink(tmp_file_path)

    @patch('src.services.consolidated_ocr_service.requests.post')
    def test_upload_document_failure(self, mock_post):
        """Test document upload failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.json.side_effect = Exception("Not JSON")
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_file.write(b"test image data")
            tmp_file_path = tmp_file.name
        
        try:
            with self.assertRaises(OCRServiceError) as context:
                self.service._upload_document(tmp_file_path)
            
            self.assertIn("Failed to upload document", str(context.exception))
        finally:
            os.unlink(tmp_file_path)

    @patch('src.services.consolidated_ocr_service.requests.get')
    def test_get_document_status(self, mock_get):
        """Test getting document status."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "processed"}
        mock_get.return_value = mock_response
        
        status = self.service._get_document_status("test_doc_id")
        
        self.assertEqual(status, "processed")
        mock_get.assert_called_once()

    @patch('src.services.consolidated_ocr_service.requests.get')
    def test_get_document_result(self, mock_get):
        """Test getting document result."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"transcript": "Page 1 text"},
                {"transcript": "Page 2 text"}
            ]
        }
        mock_get.return_value = mock_response
        
        result = self.service._get_document_result("test_doc_id")
        
        self.assertEqual(result, "Page 1 text\nPage 2 text")
        mock_get.assert_called_once()

    @patch.object(ConsolidatedOCRService, '_get_document_result')
    @patch.object(ConsolidatedOCRService, '_wait_for_processing')
    @patch.object(ConsolidatedOCRService, '_upload_document')
    @patch.object(ConsolidatedOCRService, '_preprocess_image')
    @patch.object(ConsolidatedOCRService, '_get_cached_result')
    @patch.object(ConsolidatedOCRService, '_get_file_hash')
    @patch.object(ConsolidatedOCRService, '_validate_file')
    def test_extract_text_from_image_success(self, mock_validate, mock_hash, mock_cache_get,
                                           mock_preprocess, mock_upload, mock_wait, mock_result):
        """Test successful text extraction from image."""
        # Setup mocks
        mock_hash.return_value = "test_hash"
        mock_cache_get.return_value = None  # Cache miss
        mock_preprocess.return_value = "/optimized/path.jpg"
        mock_upload.return_value = "doc_id"
        mock_result.return_value = "Extracted text content"
        
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_file.write(b"test image data")
            tmp_file_path = tmp_file.name
        
        try:
            result = self.service.extract_text_from_image(tmp_file_path)
            
            self.assertEqual(result, "Extracted text content")
            mock_validate.assert_called_once()
            mock_upload.assert_called_once()
            mock_wait.assert_called_once_with("doc_id")
            mock_result.assert_called_once_with("doc_id")
        finally:
            os.unlink(tmp_file_path)

    def test_extract_text_no_api_key(self):
        """Test text extraction fails without API key."""
        service = ConsolidatedOCRService(allow_no_key=True)
        
        with self.assertRaises(OCRServiceError) as context:
            service.extract_text_from_image("/test/path.jpg")
        
        self.assertIn("OCR service not available", str(context.exception))

    def test_extract_text_from_multiple_images_parallel(self):
        """Test parallel processing of multiple images."""
        file_paths = ["/test/image1.jpg", "/test/image2.jpg"]
        
        with patch.object(self.service, '_extract_with_error_handling') as mock_extract:
            mock_extract.side_effect = [
                ("Text from image 1", None),
                ("Text from image 2", None)
            ]
            
            results = self.service.extract_text_from_multiple_images_parallel(file_paths)
            
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0], ("/test/image1.jpg", "Text from image 1", None))
            self.assertEqual(results[1], ("/test/image2.jpg", "Text from image 2", None))

    def test_extract_with_error_handling_success(self):
        """Test error handling wrapper for successful extraction."""
        with patch.object(self.service, 'extract_text_from_image', return_value="Success text"):
            text, error = self.service._extract_with_error_handling("/test/path.jpg")
            
            self.assertEqual(text, "Success text")
            self.assertIsNone(error)

    def test_extract_with_error_handling_failure(self):
        """Test error handling wrapper for failed extraction."""
        with patch.object(self.service, 'extract_text_from_image', side_effect=Exception("Test error")):
            text, error = self.service._extract_with_error_handling("/test/path.jpg")
            
            self.assertEqual(text, "")
            self.assertEqual(error, "Test error")

    @pytest.mark.asyncio
    async def test_extract_text_async(self):
        """Test async text extraction."""
        with patch.object(self.service, 'extract_text_from_image', return_value="Async text"):
            result = await self.service.extract_text_async("/test/path.jpg")
            
            self.assertEqual(result, "Async text")

    def test_get_cache_stats(self):
        """Test cache statistics."""
        # Add some cache entries
        current_time = time.time()
        self.service.cache = {
            "hash1": "text1",
            "hash2": "text2",
            "hash3": "text3"
        }
        self.service.cache_timestamps = {
            "hash1": current_time,  # Valid
            "hash2": current_time - 100,  # Valid
            "hash3": current_time - self.service.cache_ttl - 1  # Expired
        }
        
        stats = self.service.get_cache_stats()
        
        self.assertTrue(stats["cache_enabled"])
        self.assertEqual(stats["total_entries"], 3)
        self.assertEqual(stats["valid_entries"], 2)
        self.assertEqual(stats["expired_entries"], 1)
        self.assertIn("memory_usage_mb", stats)

    def test_clear_cache(self):
        """Test cache clearing."""
        # Add cache entries
        self.service.cache = {"hash1": "text1", "hash2": "text2"}
        self.service.cache_timestamps = {"hash1": time.time(), "hash2": time.time()}
        
        cleared_count = self.service.clear_cache()
        
        self.assertEqual(cleared_count, 2)
        self.assertEqual(len(self.service.cache), 0)
        self.assertEqual(len(self.service.cache_timestamps), 0)

    def test_service_metrics_tracking(self):
        """Test that service metrics are properly tracked."""
        # Test successful request tracking
        with patch.object(self.service, 'extract_text_from_image', return_value="test") as mock_extract:
            with self.service.track_request():
                pass
            
            metrics = self.service.get_metrics()
            self.assertEqual(metrics.total_requests, 1)
            self.assertEqual(metrics.successful_requests, 1)
            self.assertEqual(metrics.failed_requests, 0)

    def test_service_metrics_failure_tracking(self):
        """Test that service metrics track failures."""
        # Test failed request tracking
        with self.assertRaises(Exception):
            with self.service.track_request():
                raise Exception("Test error")
        
        metrics = self.service.get_metrics()
        self.assertEqual(metrics.total_requests, 1)
        self.assertEqual(metrics.successful_requests, 0)
        self.assertEqual(metrics.failed_requests, 1)

    def test_backward_compatibility_aliases(self):
        """Test that backward compatibility aliases work."""
        from src.services.consolidated_ocr_service import OCRService, OptimizedOCRService
        
        # Both aliases should point to ConsolidatedOCRService
        self.assertEqual(OCRService, ConsolidatedOCRService)
        self.assertEqual(OptimizedOCRService, ConsolidatedOCRService)


if __name__ == '__main__':
    unittest.main()