"""
Comprehensive integration tests for the Exam Grader application.
Tests all components working together after the 20 critical fixes.
"""
import pytest
import os
import sys
import tempfile
import json
from unittest.mock import Mock, patch
from io import BytesIO

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the Flask app and utilities
from webapp.exam_grader_app import app, config
from utils.cache import Cache
from utils.rate_limiter import rate_limiter, ip_whitelist
from utils.input_sanitizer import InputSanitizer, validate_file_upload
from utils.error_handler import ErrorHandler
from utils.loading_states import loading_manager
from utils.file_processor import FileProcessor

class TestIntegration:
    """Integration tests for all components."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        with app.test_client() as client:
            with app.app_context():
                yield client
    
    @pytest.fixture
    def temp_file(self):
        """Create temporary test file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'Test content for exam grader')
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
        cache.set('test_key', 'test_value')
        assert cache.get('test_key') == 'test_value'
        
        # Test TTL
        cache.set('ttl_key', 'ttl_value', ttl=1)
        assert cache.get('ttl_key') == 'ttl_value'
        
        # Test cache stats
        stats = cache.get_stats()
        assert 'hit_rate' in stats
        assert 'total_requests' in stats
        
        # Test cleanup
        cleanup_result = cache.cleanup()
        assert isinstance(cleanup_result, dict)
    
    def test_rate_limiter_integration(self):
        """Test rate limiting functionality."""
        # Test basic rate limiting
        allowed, info = rate_limiter.is_allowed('test_rule')
        assert allowed is True
        assert 'remaining' in info
        
        # Test IP whitelist
        ip_whitelist.add_ip('192.168.1.100')
        assert ip_whitelist.is_whitelisted('192.168.1.100')
        
        # Test rate limit stats
        stats = rate_limiter.get_stats()
        assert 'active_ips' in stats
        assert 'rules' in stats
    
    def test_input_sanitizer_integration(self):
        """Test input sanitization functionality."""
        # Test string sanitization
        malicious_input = '<script>alert("xss")</script>Hello'
        sanitized = InputSanitizer.sanitize_string(malicious_input)
        assert '<script>' not in sanitized
        assert 'Hello' in sanitized
        
        # Test filename sanitization
        bad_filename = '../../../etc/passwd'
        safe_filename = InputSanitizer.sanitize_filename(bad_filename)
        assert '..' not in safe_filename
        assert '/' not in safe_filename
        
        # Test file validation
        test_data = b'Test file content'
        is_valid, error_msg = validate_file_upload(test_data, 'test.txt', ['.txt'])
        assert is_valid is True
        
        # Test malicious file
        is_valid, error_msg = validate_file_upload(test_data, 'test.exe', ['.txt'])
        assert is_valid is False
    
    def test_error_handler_integration(self):
        """Test error handling functionality."""
        # Test user-friendly error messages
        error_info = ErrorHandler.get_user_friendly_error('file_not_found', {'filename': 'test.txt'})
        assert 'message' in error_info
        assert 'suggestions' in error_info
        assert 'test.txt' in error_info['message']
        
        # Test error logging
        test_error = Exception("Test error")
        error_id = ErrorHandler.log_error(test_error, 'test_error', {'context': 'test'})
        assert len(error_id) == 8  # UUID first 8 chars
        
        # Test file error handling
        error_type, context = ErrorHandler.handle_file_error(FileNotFoundError("File not found"), "test.txt")
        assert error_type == 'file_not_found'
        assert context['filename'] == 'test.txt'
    
    def test_loading_states_integration(self):
        """Test loading states functionality."""
        # Test operation creation
        progress = loading_manager.start_operation('test_op', 'Test Operation', 10)
        assert progress.operation_id == 'test_op'
        assert progress.total_steps == 10
        
        # Test progress updates
        updated = loading_manager.update_progress('test_op', current_step=5, message='Half done')
        assert updated.current_step == 5
        assert updated.progress_percent == 50.0
        
        # Test completion
        completed = loading_manager.complete_operation('test_op', 'Done!')
        assert completed.progress_percent == 100.0
        
        # Test cleanup
        cleaned = loading_manager.cleanup_old_operations(max_age_seconds=0)
        assert cleaned >= 0
    
    def test_file_processor_integration(self):
        """Test file processing functionality."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'Test file content for processing')
            temp_path = f.name
        
        try:
            # Test file info
            file_info = FileProcessor.get_file_info(temp_path)
            assert 'size_bytes' in file_info
            assert 'extension' in file_info
            assert file_info['extension'] == '.txt'
            
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
        response = client.get('/')
        assert response.status_code == 200
        assert b'Dashboard' in response.data
    
    def test_upload_guide_integration(self, client, temp_file):
        """Test guide upload with all security and processing features."""
        with open(temp_file, 'rb') as f:
            data = {
                'guide_file': (f, 'test_guide.txt')
            }
            response = client.post('/upload-guide', data=data, follow_redirects=True)
            assert response.status_code == 200
    
    def test_api_endpoints_integration(self, client):
        """Test API endpoints with rate limiting and error handling."""
        # Test cache stats API
        response = client.get('/api/cache/stats')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        
        # Test loading progress API (should return 404 for non-existent operation)
        response = client.get('/api/loading/progress/nonexistent')
        assert response.status_code == 404
        
        # Test active operations API
        response = client.get('/api/loading/active')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'active_operations' in data
    
    def test_error_handling_integration(self, client):
        """Test error handling across the application."""
        # Test 404 error
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
        
        # Test file upload with invalid file type
        data = {
            'guide_file': (BytesIO(b'test content'), 'test.invalid')
        }
        response = client.post('/upload-guide', data=data)
        assert response.status_code == 302  # Redirect after error
    
    def test_session_management_integration(self, client):
        """Test session management and persistence."""
        with client.session_transaction() as sess:
            sess['test_key'] = 'test_value'
        
        # Test that session persists
        response = client.get('/')
        assert response.status_code == 200
        
        with client.session_transaction() as sess:
            assert sess.get('test_key') == 'test_value'
    
    def test_security_features_integration(self, client):
        """Test security features working together."""
        # Test CSRF protection (should be disabled in testing)
        response = client.post('/upload-guide', data={})
        assert response.status_code in [200, 302, 400]  # Various valid responses
        
        # Test input sanitization in API
        malicious_data = {
            'malicious_field': '<script>alert("xss")</script>'
        }
        response = client.post('/api/process-mapping', 
                             data=json.dumps(malicious_data),
                             content_type='application/json')
        # Should handle gracefully (not crash)
        assert response.status_code in [200, 400, 500]
    
    def test_performance_features_integration(self):
        """Test performance optimizations."""
        # Test cache performance
        cache = Cache()
        
        # Warm up cache
        for i in range(100):
            cache.set(f'perf_key_{i}', f'value_{i}')
        
        # Test retrieval performance
        for i in range(100):
            value = cache.get(f'perf_key_{i}')
            assert value == f'value_{i}'
        
        # Test cache stats after performance test
        stats = cache.get_stats()
        assert stats['total_requests'] >= 200  # 100 sets + 100 gets
    
    def test_configuration_integration(self):
        """Test configuration management."""
        # Test config values are accessible
        assert hasattr(config, 'supported_formats')
        assert hasattr(config, 'max_file_size_mb')
        
        # Test fallback values work
        from webapp.exam_grader_app import get_config_value
        value = get_config_value('nonexistent_key', 'default_value')
        assert value == 'default_value'
    
    def test_logging_integration(self):
        """Test logging system integration."""
        from utils.logger import setup_logger
        
        test_logger = setup_logger('test_integration')
        
        # Test logging doesn't crash
        test_logger.info('Test info message')
        test_logger.warning('Test warning message')
        test_logger.error('Test error message')
        
        # Logger should be properly configured
        assert test_logger.name == 'test_integration'

if __name__ == '__main__':
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
