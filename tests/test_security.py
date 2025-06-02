"""
Security tests for the Exam Grader application.
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from webapp.security import SecurityValidator, RateLimiter


class TestSecurityValidator:
    """Test security validation functions."""
    
    def test_validate_filename_valid(self):
        """Test valid filenames."""
        valid_filenames = [
            "test.pdf",
            "document.docx",
            "image.jpg",
            "file_with_underscores.png",
            "file-with-hyphens.txt"
        ]
        
        for filename in valid_filenames:
            is_valid, error = SecurityValidator.validate_filename(filename)
            assert is_valid, f"Filename '{filename}' should be valid, but got error: {error}"
    
    def test_validate_filename_invalid(self):
        """Test invalid filenames."""
        invalid_filenames = [
            "",  # Empty filename
            "../test.pdf",  # Path traversal
            "test/file.pdf",  # Forward slash
            "test\\file.pdf",  # Backslash
            "test\x00.pdf",  # Null byte
            "test.exe",  # Invalid extension
            "a" * 300 + ".pdf"  # Too long
        ]
        
        for filename in invalid_filenames:
            is_valid, error = SecurityValidator.validate_filename(filename)
            assert not is_valid, f"Filename '{filename}' should be invalid"
            assert error is not None, f"Error message should be provided for '{filename}'"
    
    def test_validate_file_path_valid(self):
        """Test valid file paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.pdf")
            
            is_valid, error = SecurityValidator.validate_file_path(test_file, temp_dir)
            assert is_valid, f"File path should be valid, but got error: {error}"
    
    def test_validate_file_path_invalid(self):
        """Test invalid file paths (path traversal)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to access file outside allowed directory
            invalid_path = os.path.join(temp_dir, "..", "test.pdf")
            
            is_valid, error = SecurityValidator.validate_file_path(invalid_path, temp_dir)
            assert not is_valid, "Path traversal should be detected"
            assert error is not None, "Error message should be provided"
    
    def test_validate_file_size_valid(self):
        """Test valid file sizes."""
        valid_sizes = [
            (1024, 'default'),  # 1KB
            (1024 * 1024, 'default'),  # 1MB
            (5 * 1024 * 1024, 'image'),  # 5MB image
            (10 * 1024 * 1024, 'document')  # 10MB document
        ]
        
        for size, file_type in valid_sizes:
            is_valid, error = SecurityValidator.validate_file_size(size, file_type)
            assert is_valid, f"File size {size} bytes should be valid for type {file_type}"
    
    def test_validate_file_size_invalid(self):
        """Test invalid file sizes."""
        invalid_sizes = [
            (20 * 1024 * 1024, 'default'),  # 20MB (exceeds 16MB limit)
            (15 * 1024 * 1024, 'image'),  # 15MB image (exceeds 10MB limit)
        ]
        
        for size, file_type in invalid_sizes:
            is_valid, error = SecurityValidator.validate_file_size(size, file_type)
            assert not is_valid, f"File size {size} bytes should be invalid for type {file_type}"
            assert error is not None, "Error message should be provided"
    
    def test_sanitize_input(self):
        """Test input sanitization."""
        test_cases = [
            ("Hello World", "Hello World"),
            ("<script>alert('xss')</script>", "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"),
            ("Test & Company", "Test &amp; Company"),
            ('Test "quotes"', "Test &quot;quotes&quot;"),
            ("Test\x00null", "Testnull"),
            ("A" * 2000, "A" * 1000)  # Truncation test
        ]
        
        for input_str, expected in test_cases:
            result = SecurityValidator.sanitize_input(input_str)
            assert result == expected, f"Input '{input_str}' not sanitized correctly"
    
    def test_generate_secure_token(self):
        """Test secure token generation."""
        token1 = SecurityValidator.generate_secure_token()
        token2 = SecurityValidator.generate_secure_token()
        
        assert len(token1) == 64, "Token should be 64 characters long"
        assert len(token2) == 64, "Token should be 64 characters long"
        assert token1 != token2, "Tokens should be unique"
        assert all(c in '0123456789abcdef' for c in token1), "Token should be hexadecimal"


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_allows_requests(self):
        """Test that rate limiter allows requests within limits."""
        limiter = RateLimiter()
        
        # Should allow requests within limit
        for i in range(5):
            assert limiter.is_allowed("test_user", max_requests=10, window_seconds=60)
    
    def test_rate_limiter_blocks_excess_requests(self):
        """Test that rate limiter blocks requests exceeding limits."""
        limiter = RateLimiter()
        
        # Fill up the limit
        for i in range(5):
            assert limiter.is_allowed("test_user", max_requests=5, window_seconds=60)
        
        # Next request should be blocked
        assert not limiter.is_allowed("test_user", max_requests=5, window_seconds=60)
    
    def test_rate_limiter_different_users(self):
        """Test that rate limiter tracks different users separately."""
        limiter = RateLimiter()
        
        # Fill up limit for user1
        for i in range(5):
            assert limiter.is_allowed("user1", max_requests=5, window_seconds=60)
        
        # user1 should be blocked
        assert not limiter.is_allowed("user1", max_requests=5, window_seconds=60)
        
        # user2 should still be allowed
        assert limiter.is_allowed("user2", max_requests=5, window_seconds=60)


if __name__ == "__main__":
    pytest.main([__file__])
