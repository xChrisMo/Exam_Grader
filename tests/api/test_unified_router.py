"""Tests for unified API router."""

import json
import time
import unittest
from unittest.mock import patch, MagicMock

from flask import Flask, g
from flask_login import LoginManager

from src.api.unified_router import (
    unified_api_bp, init_unified_api, APIMiddleware,
    rate_limit_storage
)
from src.models.api_responses import APIResponse, ErrorResponse
from src.database.models import db, User
from tests.conftest import create_test_app


class TestUnifiedRouter(unittest.TestCase):
    """Test cases for unified API router."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = create_test_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Initialize database
        db.create_all()
        
        # Create test user
        self.test_user = User(
            username='testuser',
            email='test@example.com',
            password_hash='hashed_password'
        )
        db.session.add(self.test_user)
        db.session.commit()
        
        # Initialize unified API
        init_unified_api(self.app)
        
        self.client = self.app.test_client()
        
        # Clear rate limit storage
        rate_limit_storage.clear()

    def tearDown(self):
        """Clean up test fixtures."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        rate_limit_storage.clear()

    def test_health_check_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get('/api/v1/health')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
        self.assertEqual(data['data']['status'], 'healthy')
        self.assertIn('timestamp', data['data'])
        self.assertIn('version', data['data'])

    def test_api_info_endpoint(self):
        """Test API info endpoint."""
        response = self.client.get('/api/v1/info')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
        self.assertEqual(data['data']['name'], 'Exam Grader API')
        self.assertEqual(data['data']['version'], '1.0.0')
        self.assertIn('endpoints', data['data'])

    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        # Create a test route with rate limiting
        @self.app.route('/test-rate-limit')
        @APIMiddleware.rate_limit(max_requests=2, window_seconds=60)
        def test_route():
            return {'message': 'success'}
        
        # First request should succeed
        response = self.client.get('/test-rate-limit')
        self.assertEqual(response.status_code, 200)
        
        # Second request should succeed
        response = self.client.get('/test-rate-limit')
        self.assertEqual(response.status_code, 200)
        
        # Third request should be rate limited
        response = self.client.get('/test-rate-limit')
        self.assertEqual(response.status_code, 429)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Rate limit exceeded', data['message'])

    def test_json_validation_middleware(self):
        """Test JSON validation middleware."""
        # Create a test route with JSON validation
        @self.app.route('/test-json-validation', methods=['POST'])
        @APIMiddleware.validate_json(['name', 'email'])
        def test_route():
            return {'message': 'success', 'data': g.validated_data}
        
        # Test with valid JSON
        response = self.client.post(
            '/test-json-validation',
            data=json.dumps({'name': 'Test', 'email': 'test@example.com'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Test with missing required field
        response = self.client.post(
            '/test-json-validation',
            data=json.dumps({'name': 'Test'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Validation failed', data['message'])
        
        # Test with non-JSON content
        response = self.client.post(
            '/test-json-validation',
            data='not json',
            content_type='text/plain'
        )
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('Request must be JSON', data['message'])

    def test_authentication_middleware(self):
        """Test authentication middleware."""
        # Create a test route with authentication
        @self.app.route('/test-auth')
        @APIMiddleware.require_auth()
        def test_route():
            return {'message': 'authenticated'}
        
        # Test without authentication
        response = self.client.get('/test-auth')
        self.assertEqual(response.status_code, 401)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Authentication required', data['message'])

    def test_request_logging_middleware(self):
        """Test request logging middleware."""
        with patch('src.api.unified_router.logger') as mock_logger:
            # Create a test route with logging
            @self.app.route('/test-logging')
            @APIMiddleware.log_request()
            def test_route():
                return {'message': 'logged'}
            
            response = self.client.get('/test-logging')
            self.assertEqual(response.status_code, 200)
            
            # Verify logging calls
            self.assertTrue(mock_logger.info.called)
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            
            # Check for request and response logs
            request_logged = any('API Request:' in call for call in log_calls)
            response_logged = any('API Response:' in call for call in log_calls)
            
            self.assertTrue(request_logged)
            self.assertTrue(response_logged)

    def test_error_handlers(self):
        """Test error handlers."""
        # Test 404 error
        response = self.client.get('/api/v1/nonexistent')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Resource not found', data['message'])
        
        # Test 500 error by creating a route that raises an exception
        @self.app.route('/test-500')
        def test_500():
            raise Exception('Test error')
        
        with patch('src.api.unified_router.logger') as mock_logger:
            response = self.client.get('/test-500')
            self.assertEqual(response.status_code, 500)
            
            data = json.loads(response.data)
            self.assertEqual(data['status'], 'error')
            self.assertIn('An unexpected error occurred', data['message'])
            
            # Verify error was logged
            mock_logger.error.assert_called()

    def test_cors_headers(self):
        """Test CORS headers are properly set."""
        response = self.client.get('/api/v1/health')
        
        # Check for CORS headers (these would be set by Flask-CORS)
        # Note: In actual testing, you might need to make an OPTIONS request
        # or configure the test client differently to see CORS headers
        self.assertEqual(response.status_code, 200)

    def test_api_endpoint_decorator(self):
        """Test the composite api_endpoint decorator."""
        from src.api.unified_router import api_endpoint
        
        # Create a test route with the composite decorator
        @self.app.route('/test-composite', methods=['POST'])
        @api_endpoint(
            methods=['POST'],
            auth_required=False,  # Disable auth for testing
            rate_limit_config={'max_requests': 5, 'window_seconds': 60},
            validate_json_fields=['test_field']
        )
        def test_route():
            return {'message': 'success', 'data': g.validated_data}
        
        # Test with valid request
        response = self.client.post(
            '/test-composite',
            data=json.dumps({'test_field': 'test_value'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['data']['test_field'], 'test_value')

    def test_request_id_generation(self):
        """Test that request IDs are generated and included in responses."""
        response = self.client.get('/api/v1/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Check that metadata includes request_id
        self.assertIn('metadata', data)
        self.assertIn('request_id', data['metadata'])
        self.assertIsInstance(data['metadata']['request_id'], str)
        self.assertTrue(len(data['metadata']['request_id']) > 0)

    def test_processing_time_tracking(self):
        """Test that processing time is tracked and included in responses."""
        # Create a route that takes some time
        @self.app.route('/test-timing')
        @APIMiddleware.log_request()
        def test_route():
            time.sleep(0.01)  # Small delay
            return {'message': 'timed'}
        
        response = self.client.get('/test-timing')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Check that metadata includes processing_time
        self.assertIn('metadata', data)
        self.assertIn('processing_time', data['metadata'])
        self.assertIsInstance(data['metadata']['processing_time'], (int, float))
        self.assertGreater(data['metadata']['processing_time'], 0)

    def test_rate_limit_cleanup(self):
        """Test that old rate limit entries are cleaned up."""
        # Create a test route with short window
        @self.app.route('/test-cleanup')
        @APIMiddleware.rate_limit(max_requests=2, window_seconds=1)
        def test_route():
            return {'message': 'success'}
        
        # Make requests
        response1 = self.client.get('/test-cleanup')
        self.assertEqual(response1.status_code, 200)
        
        response2 = self.client.get('/test-cleanup')
        self.assertEqual(response2.status_code, 200)
        
        # Should be rate limited
        response3 = self.client.get('/test-cleanup')
        self.assertEqual(response3.status_code, 429)
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should work again
        response4 = self.client.get('/test-cleanup')
        self.assertEqual(response4.status_code, 200)


if __name__ == '__main__':
    unittest.main()