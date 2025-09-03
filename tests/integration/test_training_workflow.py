"""
Integration tests for the complete training workflow

Tests the end-to-end training process including file upload,
processing, training, and report generation.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from flask import url_for

from webapp.app import create_app
from src.database.models import db, User, TrainingSession, TrainingGuide, TrainingQuestion
from src.services.training_service import training_service
from src.services.confidence_monitor import confidence_monitor
from src.services.error_monitor import error_monitor
from src.services.performance_optimizer import performance_optimizer


@pytest.fixture
def app():
    """Create test Flask application"""
    app = create_app(testing=True)
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def auth_user(app):
    """Create authenticated test user"""
    with app.app_context():
        user = User(
            id=1,
            username='testuser',
            email='test@example.com',
            password_hash='hashed_password'
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def sample_files():
    """Create sample training files"""
    files = {}
    
    # Create sample PDF content
    files['sample.pdf'] = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
    
    # Create sample image content (minimal PNG)
    files['sample.png'] = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13'
        b'\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8'
        b'\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    
    return files


class TestTrainingWorkflow:
    """Test complete training workflow"""
    
    def test_file_upload_workflow(self, client, auth_user, sample_files):
        """Test file upload process"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        # Test file upload
        data = {
            'files': [
                (tempfile.NamedTemporaryFile(suffix='.pdf', delete=False), 'test.pdf'),
                (tempfile.NamedTemporaryFile(suffix='.png', delete=False), 'test.png')
            ]
        }
        
        response = client.post('/training/upload', 
                             data=data,
                             content_type='multipart/form-data')
        
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert len(result['files']) == 2
    
    def test_session_creation_workflow(self, client, auth_user):
        """Test training session creation"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        session_data = {
            'sessionName': 'Test Training Session',
            'confidenceThreshold': 0.7,
            'maxQuestions': 10,
            'useInMainApp': True,
            'files': [
                {
                    'filename': 'test_file.pdf',
                    'original_name': 'test.pdf',
                    'size': 1024,
                    'category': 'qa',
                    'extension': '.pdf'
                }
            ]
        }
        
        response = client.post('/training/create-session',
                             data=json.dumps(session_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert 'session_id' in result
    
    @patch('src.services.training_service.training_service.start_training')
    def test_training_execution_workflow(self, mock_start_training, client, auth_user):
        """Test training execution process"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        # Mock successful training start
        mock_start_training.return_value = True
        
        training_data = {
            'session_id': f'session_{auth_user.id}_123456789',
            'priority': 'normal'
        }
        
        response = client.post('/training/start-training',
                             data=json.dumps(training_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert 'session_id' in result
    
    def test_confidence_monitoring_workflow(self, client, auth_user, app):
        """Test confidence monitoring functionality"""
        with app.app_context():
            # Create test training session
            session = TrainingSession(
                id='test_session_123',
                user_id=auth_user.id,
                name='Test Session',
                status='completed'
            )
            db.session.add(session)
            
            # Create test guide
            guide = TrainingGuide(
                id='test_guide_123',
                session_id=session.id,
                filename='test.pdf',
                file_path='/test/path',
                file_size=1024,
                file_type='pdf',
                guide_type='questions_answers'
            )
            db.session.add(guide)
            
            # Create test questions
            questions = [
                TrainingQuestion(
                    id=f'test_q_{i}',
                    guide_id=guide.id,
                    question_number=str(i),
                    question_text=f'Test question {i}',
                    expected_answer=f'Test answer {i}',
                    point_value=10.0,
                    extraction_confidence=0.8 - (i * 0.1)
                )
                for i in range(5)
            ]
            
            for question in questions:
                db.session.add(question)
            
            db.session.commit()
        
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        # Test confidence analysis
        response = client.get(f'/training/session/{session.id}/confidence')
        
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert 'confidence_metrics' in result
    
    def test_error_monitoring_workflow(self, client, auth_user):
        """Test error monitoring functionality"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        # Test error statistics
        response = client.get('/training/system/errors?hours=24')
        
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert 'statistics' in result
    
    def test_performance_monitoring_workflow(self, client, auth_user):
        """Test performance monitoring functionality"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        # Test performance metrics
        response = client.get('/training/system/performance')
        
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert 'performance_metrics' in result
    
    def test_cache_management_workflow(self, client, auth_user):
        """Test cache management functionality"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        # Test cache clearing
        response = client.post('/training/system/cache/clear',
                             data=json.dumps({'cache_level': 'memory'}),
                             content_type='application/json')
        
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
    
    def test_system_health_workflow(self, client, auth_user):
        """Test system health monitoring"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        # Test system health
        response = client.get('/training/system/health')
        
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert 'health' in result


class TestTrainingServiceIntegration:
    """Test training service integration"""
    
    @patch('src.services.guide_processing_router.guide_processing_router.route_guide_processing')
    def test_guide_processing_integration(self, mock_router, app):
        """Test guide processing integration"""
        with app.app_context():
            # Mock guide processing router
            from src.services.guide_processing_router import ProcessingResult
            mock_router.return_value = ProcessingResult(
                success=True,
                processing_method="traditional_ocr_with_llm",
                data={
                    'extracted_criteria': [
                        {
                            'question_text': 'Test question',
                            'expected_answer': 'Test answer',
                            'point_value': 10,
                            'marks_allocated': 10,
                            'rubric_details': 'Test rubric'
                        }
                    ]
                },
                metadata={
                    'total_questions': 1,
                    'total_marks': 10.0,
                    'format_confidence': 0.9
                }
            )
            
            # Test guide processing
            result = training_service.process_uploaded_guides(
                session_id='test_session',
                guide_files=[{
                    'filename': 'test.pdf',
                    'file_path': '/test/path',
                    'file_type': 'pdf'
                }]
            )
            
            assert result['success'] is True
            assert len(result['processed_guides']) == 1
    
    def test_confidence_analysis_integration(self, app):
        """Test confidence analysis integration"""
        with app.app_context():
            # Create test data
            session = TrainingSession(
                id='test_session_456',
                user_id=1,
                name='Test Session',
                status='completed'
            )
            db.session.add(session)
            db.session.commit()
            
            # Test confidence analysis
            metrics = confidence_monitor.analyze_session_confidence(session.id)
            
            assert metrics.total_questions == 0  # No questions in test session
            assert metrics.avg_confidence == 0.0
    
    def test_error_logging_integration(self, app):
        """Test error logging integration"""
        with app.app_context():
            # Test error logging
            test_error = ValueError("Test error for integration testing")
            
            error_id = error_monitor.log_error(
                error=test_error,
                user_id=1,
                session_id='test_session',
                component='integration_test'
            )
            
            assert error_id is not None
            assert error_id != "error_monitor_failed"
            
            # Test error retrieval
            error_details = error_monitor.get_error_details(error_id)
            assert error_details is not None
            assert error_details['message'] == str(test_error)
    
    def test_performance_optimization_integration(self, app):
        """Test performance optimization integration"""
        with app.app_context():
            # Test caching functionality
            @performance_optimizer.cached(ttl=300)
            def test_cached_function(param):
                return f"result_for_{param}"
            
            # First call should execute function
            result1 = test_cached_function("test")
            assert result1 == "result_for_test"
            
            # Second call should use cache
            result2 = test_cached_function("test")
            assert result2 == "result_for_test"
            
            # Test metrics
            metrics = performance_optimizer.get_performance_metrics()
            assert 'cache_metrics' in metrics
            assert metrics['cache_metrics']['hits'] > 0


class TestSecurityAndValidation:
    """Test security and validation aspects"""
    
    def test_file_upload_security(self, client, auth_user):
        """Test file upload security validation"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        # Test malicious file upload
        malicious_data = {
            'files': [(tempfile.NamedTemporaryFile(suffix='.exe', delete=False), 'malicious.exe')]
        }
        
        response = client.post('/training/upload',
                             data=malicious_data,
                             content_type='multipart/form-data')
        
        # Should reject malicious file
        assert response.status_code == 400
        result = json.loads(response.data)
        assert 'error' in result
    
    def test_session_access_control(self, client, auth_user):
        """Test session access control"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        # Try to access another user's session
        other_user_session = 'session_999_123456789'
        
        response = client.get(f'/training/session/{other_user_session}/confidence')
        
        # Should deny access
        assert response.status_code == 403
        result = json.loads(response.data)
        assert 'error' in result
        assert 'Access denied' in result['error']
    
    def test_input_validation(self, client, auth_user):
        """Test input validation"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        # Test invalid session creation data
        invalid_data = {
            'sessionName': '',  # Empty name
            'confidenceThreshold': 2.0,  # Invalid threshold
            'maxQuestions': -1,  # Invalid max questions
            'files': []  # No files
        }
        
        response = client.post('/training/create-session',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        result = json.loads(response.data)
        assert 'error' in result


class TestPerformanceAndScalability:
    """Test performance and scalability aspects"""
    
    def test_large_file_handling(self, client, auth_user):
        """Test handling of large files"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        # Create large file content (simulated)
        large_content = b'x' * (60 * 1024 * 1024)  # 60MB file
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(large_content)
            f.flush()
            
            data = {
                'files': [(f, 'large_file.pdf')]
            }
            
            response = client.post('/training/upload',
                                 data=data,
                                 content_type='multipart/form-data')
            
            # Should reject file that's too large
            assert response.status_code == 400
            result = json.loads(response.data)
            assert 'error' in result
    
    def test_concurrent_sessions(self, client, auth_user):
        """Test handling of concurrent training sessions"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(auth_user.id)
        
        # Create multiple sessions concurrently
        session_data = {
            'sessionName': 'Concurrent Test Session',
            'confidenceThreshold': 0.6,
            'files': [{
                'filename': 'test.pdf',
                'original_name': 'test.pdf',
                'size': 1024,
                'category': 'qa',
                'extension': '.pdf'
            }]
        }
        
        responses = []
        for i in range(3):
            session_data['sessionName'] = f'Concurrent Test Session {i}'
            response = client.post('/training/create-session',
                                 data=json.dumps(session_data),
                                 content_type='application/json')
            responses.append(response)
        
        # All sessions should be created successfully
        for response in responses:
            assert response.status_code == 200
            result = json.loads(response.data)
            assert result['success'] is True
    
    def test_memory_usage_monitoring(self, app):
        """Test memory usage monitoring"""
        with app.app_context():
            # Test memory metrics
            metrics = performance_optimizer.get_performance_metrics()
            
            assert 'system_metrics' in metrics
            assert 'memory_usage' in metrics['system_metrics']
            assert isinstance(metrics['system_metrics']['memory_usage'], (int, float))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])