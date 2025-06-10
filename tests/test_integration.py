"""
Comprehensive integration tests for the Exam Grader application.
Tests all components working together with the new database-backed system.
"""

import json
import os
import sys
import tempfile
from io import BytesIO
from unittest.mock import Mock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config.unified_config import config
from src.database import (
    DatabaseUtils,
    MarkingGuide,
    MigrationManager,
    Submission,
    User,
    db,
)
from src.security.secrets_manager import secrets_manager
from src.security.session_manager import SecureSessionManager
from src.services.file_cleanup_service import FileCleanupService
from src.services.retry_service import retry_service, retry_with_backoff
from utils.cache import Cache
from utils.error_handler import ErrorHandler
from utils.file_processor import FileProcessor
from utils.input_sanitizer import InputSanitizer, validate_file_upload
from utils.loading_states import loading_manager
from utils.rate_limiter import ip_whitelist, rate_limiter

# Import the Flask app and new components
from webapp.exam_grader_app import app


class TestIntegration:
    """Integration tests for all components."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing
        app.config["SQLALCHEMY_DATABASE_URI"] = (
            "sqlite:///:memory:"  # In-memory database for tests
        )

        with app.test_client() as client:
            with app.app_context():
                # Initialize database for testing
                db.create_all()

                # Create test user
                test_user = User(
                    username="testuser", email="test@example.com", is_active=True
                )
                test_user.set_password("testpass")
                db.session.add(test_user)
                db.session.commit()

                yield client

                # Cleanup
                db.session.remove()
                db.drop_all()

    @pytest.fixture
    def temp_file(self):
        """Create temporary test file."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"Test content for exam grader")
            temp_path = f.name
        yield temp_path
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    def test_cache_system_integration(self):
        """Test cache system functionality."""
        cache = Cache()

        # Test basic caching
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"

        # Test TTL
        cache.set("ttl_key", "ttl_value", ttl=1)
        assert cache.get("ttl_key") == "ttl_value"

        # Test cache stats
        stats = cache.get_stats()
        assert "hit_rate" in stats
        assert "total_requests" in stats

        # Test cleanup
        cleanup_result = cache.cleanup()
        assert isinstance(cleanup_result, dict)

    def test_rate_limiter_integration(self):
        """Test rate limiting functionality."""
        # Test basic rate limiting
        allowed, info = rate_limiter.is_allowed("test_rule")
        assert allowed is True
        assert "remaining" in info

        # Test IP whitelist
        ip_whitelist.add_ip("192.168.1.100")
        assert ip_whitelist.is_whitelisted("192.168.1.100")

        # Test rate limit stats
        stats = rate_limiter.get_stats()
        assert "active_ips" in stats
        assert "rules" in stats

    def test_input_sanitizer_integration(self):
        """Test input sanitization functionality."""
        # Test string sanitization
        malicious_input = '<script>alert("xss")</script>Hello'
        sanitized = InputSanitizer.sanitize_string(malicious_input)
        assert "<script>" not in sanitized
        assert "Hello" in sanitized

        # Test filename sanitization
        bad_filename = "../../../etc/passwd"
        safe_filename = InputSanitizer.sanitize_filename(bad_filename)
        assert ".." not in safe_filename
        assert "/" not in safe_filename

        # Test file validation
        test_data = b"Test file content"
        is_valid, error_msg = validate_file_upload(test_data, "test.txt", [".txt"])
        assert is_valid is True

        # Test malicious file
        is_valid, error_msg = validate_file_upload(test_data, "test.exe", [".txt"])
        assert is_valid is False

    def test_error_handler_integration(self):
        """Test error handling functionality."""
        # Test user-friendly error messages
        error_info = ErrorHandler.get_user_friendly_error(
            "file_not_found", {"filename": "test.txt"}
        )
        assert "message" in error_info
        assert "suggestions" in error_info
        assert "test.txt" in error_info["message"]

        # Test error logging
        test_error = Exception("Test error")
        error_id = ErrorHandler.log_error(test_error, "test_error", {"context": "test"})
        assert len(error_id) == 8  # UUID first 8 chars

        # Test file error handling
        error_type, context = ErrorHandler.handle_file_error(
            FileNotFoundError("File not found"), "test.txt"
        )
        assert error_type == "file_not_found"
        assert context["filename"] == "test.txt"

    def test_loading_states_integration(self):
        """Test loading states functionality."""
        # Test operation creation
        progress = loading_manager.start_operation("test_op", "Test Operation", 10)
        assert progress.operation_id == "test_op"
        assert progress.total_steps == 10

        # Test progress updates
        updated = loading_manager.update_progress(
            "test_op", current_step=5, message="Half done"
        )
        assert updated.current_step == 5
        assert updated.progress_percent == 50.0

        # Test completion
        completed = loading_manager.complete_operation("test_op", "Done!")
        assert completed.progress_percent == 100.0

        # Test cleanup
        cleaned = loading_manager.cleanup_old_operations(max_age_seconds=0)
        assert cleaned >= 0

    def test_file_processor_integration(self):
        """Test file processing functionality."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"Test file content for processing")
            temp_path = f.name

        try:
            # Test file info
            file_info = FileProcessor.get_file_info(temp_path)
            assert "size_bytes" in file_info
            assert "extension" in file_info
            assert file_info["extension"] == ".txt"

            # Test file validation
            is_valid = FileProcessor.validate_file_size(temp_path, max_size_mb=1)
            assert is_valid is True

            # Test file hash calculation
            file_hash = FileProcessor.calculate_file_hash(temp_path)
            assert len(file_hash) == 64  # SHA256 hex length

        finally:
            os.unlink(temp_path)

    def test_dashboard_route_integration(self, client):
        """Test dashboard route with all integrations."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Dashboard" in response.data

    def test_upload_guide_integration(self, client, temp_file):
        """Test guide upload with all security and processing features."""
        with open(temp_file, "rb") as f:
            data = {"guide_file": (f, "test_guide.txt")}
            response = client.post("/upload-guide", data=data, follow_redirects=True)
            assert response.status_code == 200

    def test_api_endpoints_integration(self, client):
        """Test API endpoints with rate limiting and error handling."""
        # Test cache stats API
        response = client.get("/api/cache/stats")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"

        # Test loading progress API (should return 404 for non-existent operation)
        response = client.get("/api/loading/progress/nonexistent")
        assert response.status_code == 404

        # Test active operations API
        response = client.get("/api/loading/active")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "active_operations" in data

    def test_error_handling_integration(self, client):
        """Test error handling across the application."""
        # Test 404 error
        response = client.get("/nonexistent-page")
        assert response.status_code == 404

        # Test file upload with invalid file type
        data = {"guide_file": (BytesIO(b"test content"), "test.invalid")}
        response = client.post("/upload-guide", data=data)
        assert response.status_code == 302  # Redirect after error

    def test_session_management_integration(self, client):
        """Test session management and persistence."""
        with client.session_transaction() as sess:
            sess["test_key"] = "test_value"

        # Test that session persists
        response = client.get("/")
        assert response.status_code == 200

        with client.session_transaction() as sess:
            assert sess.get("test_key") == "test_value"

    def test_security_features_integration(self, client):
        """Test security features working together."""
        # Test CSRF protection (should be disabled in testing)
        response = client.post("/upload-guide", data={})
        assert response.status_code in [200, 302, 400]  # Various valid responses

        # Test input sanitization in API
        malicious_data = {"malicious_field": '<script>alert("xss")</script>'}
        response = client.post(
            "/api/process-mapping",
            data=json.dumps(malicious_data),
            content_type="application/json",
        )
        # Should handle gracefully (not crash)
        assert response.status_code in [200, 400, 500]

    def test_performance_features_integration(self):
        """Test performance optimizations."""
        # Test cache performance
        cache = Cache()

        # Warm up cache
        for i in range(100):
            cache.set(f"perf_key_{i}", f"value_{i}")

        # Test retrieval performance
        for i in range(100):
            value = cache.get(f"perf_key_{i}")
            assert value == f"value_{i}"

        # Test cache stats after performance test
        stats = cache.get_stats()
        assert stats["total_requests"] >= 200  # 100 sets + 100 gets

    def test_configuration_integration(self):
        """Test configuration management."""
        # Test config values are accessible
        assert hasattr(config, "supported_formats")
        assert hasattr(config, "max_file_size_mb")

        # Test fallback values work
        from webapp.exam_grader_app import get_config_value

        value = get_config_value("nonexistent_key", "default_value")
        assert value == "default_value"

    def test_logging_integration(self):
        """Test logging system integration."""
        from utils.logger import setup_logger

        test_logger = setup_logger("test_integration")

        # Test logging doesn't crash
        test_logger.info("Test info message")
        test_logger.warning("Test warning message")
        test_logger.error("Test error message")

        # Logger should be properly configured
        assert test_logger.name == "test_integration"

    def test_database_integration(self, client):
        """Test database operations and models."""
        with app.app_context():
            # Test user creation and authentication
            user = User(username="dbtest", email="dbtest@example.com")
            user.set_password("testpass")
            db.session.add(user)
            db.session.commit()

            # Test password verification
            assert user.check_password("testpass")
            assert not user.check_password("wrongpass")

            # Test marking guide creation
            guide = MarkingGuide(
                user_id=user.id,
                title="Test Guide",
                filename="test.pdf",
                file_path="/tmp/test.pdf",
                file_size=1024,
                file_type="pdf",
                total_marks=100.0,
            )
            db.session.add(guide)
            db.session.commit()

            # Test submission creation
            submission = Submission(
                user_id=user.id,
                marking_guide_id=guide.id,
                filename="submission.pdf",
                file_path="/tmp/submission.pdf",
                file_size=2048,
                file_type="pdf",
                processing_status="completed",
            )
            db.session.add(submission)
            db.session.commit()

            # Test relationships
            assert len(user.marking_guides) == 1
            assert len(user.submissions) == 1
            assert submission.marking_guide == guide

    def test_secure_session_management(self):
        """Test secure session management."""
        session_manager = SecureSessionManager("test-secret-key", 3600)

        # Create test user
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()
            if user:
                # Test session creation
                session_id = session_manager.create_session(
                    user.id, {"test_data": "test_value"}
                )
                assert session_id is not None

                # Test session retrieval
                session_data = session_manager.get_session(session_id)
                assert session_data is not None
                assert session_data["test_data"] == "test_value"

                # Test session update
                updated_data = {"test_data": "updated_value", "new_key": "new_value"}
                success = session_manager.update_session(session_id, updated_data)
                assert success

                # Test session invalidation
                success = session_manager.invalidate_session(session_id)
                assert success

                # Test invalidated session retrieval
                session_data = session_manager.get_session(session_id)
                assert session_data is None

    def test_secrets_manager_integration(self):
        """Test secrets manager functionality."""
        # Test setting and getting secrets
        success = secrets_manager.set_secret(
            "test_secret", "secret_value", "Test secret"
        )
        assert success

        value = secrets_manager.get_secret("test_secret")
        assert value == "secret_value"

        # Test listing secrets
        secrets_list = secrets_manager.list_secrets()
        assert "test_secret" in secrets_list

        # Test deleting secrets
        success = secrets_manager.delete_secret("test_secret")
        assert success

        value = secrets_manager.get_secret("test_secret")
        assert value is None

    def test_file_cleanup_service(self):
        """Test file cleanup service functionality."""
        cleanup_service = FileCleanupService(config)

        # Test disk usage stats
        usage_stats = cleanup_service.get_disk_usage()
        assert "temp" in usage_stats
        assert "uploads" in usage_stats
        assert "output" in usage_stats

        # Test cleanup operations (should not fail)
        temp_stats = cleanup_service.cleanup_temp_files()
        assert hasattr(temp_stats, "files_scanned")
        assert hasattr(temp_stats, "files_deleted")
        assert hasattr(temp_stats, "bytes_freed")

    def test_retry_service_integration(self):
        """Test retry service with circuit breaker."""

        # Test successful operation
        @retry_with_backoff("test_service", max_attempts=3)
        def successful_operation():
            return "success"

        result = successful_operation()
        assert result == "success"

        # Test failing operation
        attempt_count = 0

        @retry_with_backoff("failing_service", max_attempts=3)
        def failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary failure")
            return "success_after_retries"

        result = failing_operation()
        assert result == "success_after_retries"
        assert attempt_count == 3

        # Test service stats
        stats = retry_service.get_service_stats("test_service")
        assert "service_name" in stats
        assert "total_attempts" in stats


if __name__ == "__main__":
    # Run basic integration tests
    test_instance = TestIntegration()

    print("Running integration tests...")

    try:
        test_instance.test_cache_system_integration()
        print("✅ Cache system integration: PASSED")
    except Exception as e:
        print(f"❌ Cache system integration: FAILED - {e}")

    try:
        test_instance.test_rate_limiter_integration()
        print("✅ Rate limiter integration: PASSED")
    except Exception as e:
        print(f"❌ Rate limiter integration: FAILED - {e}")

    try:
        test_instance.test_input_sanitizer_integration()
        print("✅ Input sanitizer integration: PASSED")
    except Exception as e:
        print(f"❌ Input sanitizer integration: FAILED - {e}")

    try:
        test_instance.test_error_handler_integration()
        print("✅ Error handler integration: PASSED")
    except Exception as e:
        print(f"❌ Error handler integration: FAILED - {e}")

    try:
        test_instance.test_loading_states_integration()
        print("✅ Loading states integration: PASSED")
    except Exception as e:
        print(f"❌ Loading states integration: FAILED - {e}")

    try:
        test_instance.test_file_processor_integration()
        print("✅ File processor integration: PASSED")
    except Exception as e:
        print(f"❌ File processor integration: FAILED - {e}")

    print("\nIntegration tests completed!")
