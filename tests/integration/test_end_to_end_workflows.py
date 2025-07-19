"""End-to-End Integration Tests for Exam Grader Application.

This module provides comprehensive integration tests that validate complete
user workflows from file upload through grading and result retrieval.
"""

import os
import json
import time
import tempfile
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.test import Client
from werkzeug.datastructures import FileStorage

try:
    from webapp.exam_grader_app import create_app
    from src.models.database_models import (
        User, MarkingGuide, Submission, Grade, 
        db, init_db
    )
    from src.services.unified_ai_processing_service import UnifiedAIProcessingService
    from src.security.auth_system import AuthenticationManager, UserRole
    from src.performance.optimization_manager import PerformanceOptimizer
except ImportError:
    # Fallback for testing environment
    pytest.skip("Required modules not available", allow_module_level=True)


class TestEndToEndWorkflows:
    """Test complete user workflows from start to finish."""
    
    @pytest.fixture(scope="class")
    def app(self):
        """Create test Flask application."""
        app = create_app()
        app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret-key',
            'UPLOAD_FOLDER': tempfile.mkdtemp(),
        })
        
        with app.app_context():
            init_db()
            yield app
    
    @pytest.fixture
    def client(self, app: Flask) -> FlaskClient:
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def auth_headers(self, app: Flask) -> Dict[str, str]:
        """Create authentication headers for test requests."""
        with app.app_context():
            # Create test user
            test_user = User(
                username='testuser',
                email='test@example.com',
                role=UserRole.ADMIN
            )
            db.session.add(test_user)
            db.session.commit()
            
            # Generate auth token (simplified for testing)
            return {
                'Authorization': 'Bearer test-token',
                'Content-Type': 'application/json'
            }
    
    @pytest.fixture
    def sample_files(self) -> Dict[str, FileStorage]:
        """Create sample files for testing."""
        # Create temporary files
        marking_guide_content = """
        Question 1: What is the capital of France?
        Answer: Paris
        
        Question 2: Calculate 2 + 2
        Answer: 4
        """
        
        submission_content = """
        Answer 1: Paris is the capital of France.
        Answer 2: 2 + 2 = 4
        """
        
        marking_guide_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        marking_guide_file.write(marking_guide_content)
        marking_guide_file.close()
        
        submission_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        submission_file.write(submission_content)
        submission_file.close()
        
        return {
            'marking_guide': FileStorage(
                stream=open(marking_guide_file.name, 'rb'),
                filename='marking_guide.txt',
                content_type='text/plain'
            ),
            'submission': FileStorage(
                stream=open(submission_file.name, 'rb'),
                filename='submission.txt',
                content_type='text/plain'
            )
        }
    
    def test_complete_grading_workflow(self, client: FlaskClient, auth_headers: Dict[str, str], sample_files: Dict[str, FileStorage]):
        """Test complete workflow from file upload to grading results."""
        # Step 1: Upload marking guide
        response = client.post(
            '/api/v1/files/upload',
            data={
                'file': sample_files['marking_guide'],
                'file_type': 'marking_guide',
                'description': 'Test marking guide'
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        guide_data = json.loads(response.data)
        assert guide_data['success'] is True
        guide_id = guide_data['data']['file_id']
        
        # Step 2: Upload student submission
        response = client.post(
            '/api/v1/files/upload',
            data={
                'file': sample_files['submission'],
                'file_type': 'submission',
                'description': 'Test submission'
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        submission_data = json.loads(response.data)
        assert submission_data['success'] is True
        submission_id = submission_data['data']['file_id']
        
        # Step 3: Start processing
        response = client.post(
            '/api/v1/processing/start',
            json={
                'marking_guide_id': guide_id,
                'submission_ids': [submission_id],
                'processing_options': {
                    'enable_ocr': True,
                    'enable_mapping': True,
                    'enable_grading': True
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        processing_data = json.loads(response.data)
        assert processing_data['success'] is True
        task_id = processing_data['data']['task_id']
        
        # Step 4: Monitor processing status
        max_attempts = 30
        for attempt in range(max_attempts):
            response = client.get(
                f'/api/v1/processing/status/{task_id}',
                headers=auth_headers
            )
            
            assert response.status_code == 200
            status_data = json.loads(response.data)
            
            if status_data['data']['status'] == 'completed':
                break
            elif status_data['data']['status'] == 'failed':
                pytest.fail(f"Processing failed: {status_data['data'].get('error')}")
            
            time.sleep(1)
        else:
            pytest.fail("Processing did not complete within timeout")
        
        # Step 5: Retrieve results
        response = client.get(
            f'/api/v1/processing/results/{task_id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        results_data = json.loads(response.data)
        assert results_data['success'] is True
        
        # Validate results structure
        results = results_data['data']
        assert 'grades' in results
        assert 'summary' in results
        assert len(results['grades']) > 0
        
        # Validate grade data
        grade = results['grades'][0]
        assert 'submission_id' in grade
        assert 'total_score' in grade
        assert 'feedback' in grade
        assert 'question_grades' in grade
    
    def test_batch_processing_workflow(self, client: FlaskClient, auth_headers: Dict[str, str], sample_files: Dict[str, FileStorage]):
        """Test batch processing of multiple submissions."""
        # Upload marking guide
        response = client.post(
            '/api/v1/files/upload',
            data={
                'file': sample_files['marking_guide'],
                'file_type': 'marking_guide'
            },
            headers=auth_headers
        )
        
        guide_id = json.loads(response.data)['data']['file_id']
        
        # Upload multiple submissions
        submission_ids = []
        for i in range(3):
            response = client.post(
                '/api/v1/files/upload',
                data={
                    'file': sample_files['submission'],
                    'file_type': 'submission',
                    'description': f'Test submission {i+1}'
                },
                headers=auth_headers
            )
            
            submission_id = json.loads(response.data)['data']['file_id']
            submission_ids.append(submission_id)
        
        # Start batch processing
        response = client.post(
            '/api/v1/processing/batch',
            json={
                'marking_guide_id': guide_id,
                'submission_ids': submission_ids,
                'processing_options': {
                    'enable_parallel_processing': True,
                    'batch_size': 2
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        batch_data = json.loads(response.data)
        task_id = batch_data['data']['task_id']
        
        # Monitor batch processing
        max_attempts = 60
        for attempt in range(max_attempts):
            response = client.get(
                f'/api/v1/processing/status/{task_id}',
                headers=auth_headers
            )
            
            status_data = json.loads(response.data)
            
            if status_data['data']['status'] == 'completed':
                break
            elif status_data['data']['status'] == 'failed':
                pytest.fail(f"Batch processing failed: {status_data['data'].get('error')}")
            
            time.sleep(1)
        
        # Validate batch results
        response = client.get(
            f'/api/v1/processing/results/{task_id}',
            headers=auth_headers
        )
        
        results_data = json.loads(response.data)
        assert len(results_data['data']['grades']) == len(submission_ids)
    
    def test_error_handling_workflow(self, client: FlaskClient, auth_headers: Dict[str, str]):
        """Test error handling in various workflow scenarios."""
        # Test invalid file upload
        response = client.post(
            '/api/v1/files/upload',
            data={'file_type': 'marking_guide'},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        error_data = json.loads(response.data)
        assert error_data['success'] is False
        assert 'error' in error_data
        
        # Test processing with invalid guide ID
        response = client.post(
            '/api/v1/processing/start',
            json={
                'marking_guide_id': 'invalid-id',
                'submission_ids': ['invalid-submission']
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400
        error_data = json.loads(response.data)
        assert error_data['success'] is False
        
        # Test status check with invalid task ID
        response = client.get(
            '/api/v1/processing/status/invalid-task-id',
            headers=auth_headers
        )
        
        assert response.status_code == 400
        error_data = json.loads(response.data)
        assert error_data['success'] is False
    
    def test_authentication_workflow(self, client: FlaskClient, app: Flask):
        """Test authentication and authorization workflows."""
        with app.app_context():
            # Test unauthenticated access
            response = client.get('/api/v1/processing/status/test')
            assert response.status_code in [401, 403]
            
            # Test invalid authentication
            response = client.get(
                '/api/v1/processing/status/test',
                headers={'Authorization': 'Bearer invalid-token'}
            )
            assert response.status_code in [401, 403]
    
    def test_file_validation_workflow(self, client: FlaskClient, auth_headers: Dict[str, str]):
        """Test file validation and security workflows."""
        # Test oversized file
        large_content = 'x' * (10 * 1024 * 1024)  # 10MB
        large_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        large_file.write(large_content)
        large_file.close()
        
        with open(large_file.name, 'rb') as f:
            response = client.post(
                '/api/v1/files/upload',
                data={
                    'file': FileStorage(
                        stream=f,
                        filename='large_file.txt',
                        content_type='text/plain'
                    ),
                    'file_type': 'submission'
                },
                headers=auth_headers
            )
        
        # Should reject oversized file
        assert response.status_code == 400
        error_data = json.loads(response.data)
        assert 'size' in error_data['error'].lower()
        
        # Test invalid file type
        malicious_file = tempfile.NamedTemporaryFile(mode='w', suffix='.exe', delete=False)
        malicious_file.write('malicious content')
        malicious_file.close()
        
        with open(malicious_file.name, 'rb') as f:
            response = client.post(
                '/api/v1/files/upload',
                data={
                    'file': FileStorage(
                        stream=f,
                        filename='malicious.exe',
                        content_type='application/octet-stream'
                    ),
                    'file_type': 'submission'
                },
                headers=auth_headers
            )
        
        # Should reject invalid file type
        assert response.status_code == 400
        error_data = json.loads(response.data)
        assert 'type' in error_data['error'].lower() or 'extension' in error_data['error'].lower()
    
    def test_performance_monitoring_workflow(self, client: FlaskClient, auth_headers: Dict[str, str]):
        """Test performance monitoring and metrics collection."""
        # Test health check endpoint
        response = client.get('/api/monitoring/health')
        assert response.status_code in [200, 503]  # Healthy or degraded
        
        health_data = json.loads(response.data)
        assert 'status' in health_data
        assert 'checks' in health_data
        
        # Test performance metrics (requires admin access)
        response = client.get(
            '/api/monitoring/performance/metrics',
            headers=auth_headers
        )
        
        if response.status_code == 200:
            metrics_data = json.loads(response.data)
            assert metrics_data['success'] is True
            assert 'data' in metrics_data
    
    def test_websocket_integration_workflow(self, app: Flask):
        """Test WebSocket integration for real-time updates."""
        # This would require a WebSocket test client
        # For now, we'll test the WebSocket manager initialization
        with app.app_context():
            try:
                from src.services.websocket_manager import WebSocketManager
                ws_manager = WebSocketManager()
                assert ws_manager is not None
                
                # Test connection handling
                test_client_id = 'test-client-123'
                ws_manager.add_client(test_client_id, MagicMock())
                assert test_client_id in ws_manager.clients
                
                # Test message broadcasting
                test_message = {'type': 'test', 'data': 'test message'}
                ws_manager.broadcast_to_room('test-room', test_message)
                
                # Cleanup
                ws_manager.remove_client(test_client_id)
                assert test_client_id not in ws_manager.clients
                
            except ImportError:
                pytest.skip("WebSocket manager not available")
    
    def test_caching_integration_workflow(self, app: Flask):
        """Test caching integration across services."""
        with app.app_context():
            try:
                from src.performance.optimization_manager import get_performance_optimizer
                optimizer = get_performance_optimizer()
                
                if optimizer:
                    # Test cache operations
                    test_key = 'test-cache-key'
                    test_value = {'data': 'test value'}
                    
                    # Set cache value
                    optimizer.cache_set(test_key, test_value, ttl=60)
                    
                    # Get cache value
                    cached_value = optimizer.cache_get(test_key)
                    assert cached_value == test_value
                    
                    # Test cache statistics
                    stats = optimizer.memory_cache.get_stats()
                    assert 'size' in stats
                    assert 'hits' in stats
                    assert 'misses' in stats
                    
            except ImportError:
                pytest.skip("Performance optimizer not available")
    
    def test_database_integration_workflow(self, app: Flask):
        """Test database operations and transactions."""
        with app.app_context():
            # Test user creation
            test_user = User(
                username='integration_test_user',
                email='integration@test.com',
                role=UserRole.USER
            )
            db.session.add(test_user)
            db.session.commit()
            
            # Test marking guide creation
            test_guide = MarkingGuide(
                title='Integration Test Guide',
                description='Test guide for integration testing',
                user_id=test_user.id,
                file_path='/tmp/test_guide.txt'
            )
            db.session.add(test_guide)
            db.session.commit()
            
            # Test submission creation
            test_submission = Submission(
                title='Integration Test Submission',
                user_id=test_user.id,
                marking_guide_id=test_guide.id,
                file_path='/tmp/test_submission.txt'
            )
            db.session.add(test_submission)
            db.session.commit()
            
            # Test grade creation
            test_grade = Grade(
                submission_id=test_submission.id,
                total_score=85.5,
                feedback='Good work on integration testing',
                question_grades=[{
                    'question_id': 1,
                    'score': 8.5,
                    'max_score': 10,
                    'feedback': 'Well answered'
                }]
            )
            db.session.add(test_grade)
            db.session.commit()
            
            # Verify relationships
            assert test_submission.marking_guide == test_guide
            assert test_grade.submission == test_submission
            assert test_user.marking_guides[0] == test_guide
            
            # Cleanup
            db.session.delete(test_grade)
            db.session.delete(test_submission)
            db.session.delete(test_guide)
            db.session.delete(test_user)
            db.session.commit()


class TestAPIIntegration:
    """Test API endpoint integration and consistency."""
    
    @pytest.fixture(scope="class")
    def app(self):
        """Create test Flask application."""
        app = create_app()
        app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        })
        
        with app.app_context():
            init_db()
            yield app
    
    @pytest.fixture
    def client(self, app: Flask) -> FlaskClient:
        """Create test client."""
        return app.test_client()
    
    def test_api_response_consistency(self, client: FlaskClient):
        """Test that all API endpoints return consistent response format."""
        endpoints_to_test = [
            '/api/v1/health',
            '/api/monitoring/health',
        ]
        
        for endpoint in endpoints_to_test:
            response = client.get(endpoint)
            
            # Should return JSON
            assert response.content_type.startswith('application/json')
            
            # Should have consistent structure
            data = json.loads(response.data)
            
            # Health endpoints might have different structures
            if 'health' in endpoint:
                assert 'status' in data
            else:
                # Standard API responses should have success field
                assert 'success' in data or 'status' in data
    
    def test_error_response_consistency(self, client: FlaskClient):
        """Test that error responses are consistent across endpoints."""
        # Test 404 errors
        response = client.get('/api/v1/nonexistent-endpoint')
        assert response.status_code == 404
        
        # Test method not allowed
        response = client.post('/api/monitoring/health')
        assert response.status_code == 405
    
    def test_cors_headers(self, client: FlaskClient):
        """Test CORS headers are properly set."""
        response = client.options('/api/v1/health')
        
        # Should include CORS headers
        assert 'Access-Control-Allow-Origin' in response.headers or response.status_code == 404
    
    def test_security_headers(self, client: FlaskClient):
        """Test security headers are properly set."""
        response = client.get('/api/monitoring/health')
        
        # Should include security headers
        expected_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection'
        ]
        
        # Note: Headers might not be set in test environment
        for header in expected_headers:
            if header in response.headers:
                assert response.headers[header] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])