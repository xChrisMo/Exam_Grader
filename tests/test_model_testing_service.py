"""
Unit tests for ModelTestingService

Tests the model testing functionality including test creation,
submission processing, and result analysis.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.services.model_testing_service import ModelTestingService
from src.database.models import LLMModelTest, LLMTestSubmission, LLMTrainingJob, User

class TestModelTestingService:
    """Test cases for ModelTestingService"""
    
    @pytest.fixture
    def service(self):
        """Create ModelTestingService instance for testing"""
        return ModelTestingService()
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing"""
        user = Mock(spec=User)
        user.id = 'test-user-id'
        return user
    
    @pytest.fixture
    def mock_training_job(self):
        """Create mock training job for testing"""
        job = Mock(spec=LLMTrainingJob)
        job.id = 'test-job-id'
        job.name = 'Test Training Job'
        job.model_id = 'test-model'
        job.status = 'completed'
        job.user_id = 'test-user-id'
        return job
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration"""
        return {
            'name': 'Test Model Test',
            'description': 'Test description',
            'confidence_threshold': 0.8,
            'comparison_mode': 'strict',
            'feedback_level': 'detailed',
            'grading_criteria': {
                'accuracy_weight': 0.6,
                'completeness_weight': 0.4
            }
        }
    
    @patch('src.services.model_testing_service.db')
    @patch('src.services.model_testing_service.LLMTrainingJob')
    def test_create_test_session_success(self, mock_job_class, mock_db, service, mock_training_job, test_config):
        """Test successful test session creation"""
        # Setup mocks
        mock_job_class.query.filter_by.return_value.first.return_value = mock_training_job
        mock_db.session.add = Mock()
        mock_db.session.commit = Mock()
        
        # Create mock test session
        mock_test = Mock(spec=LLMModelTest)
        mock_test.id = 'test-session-id'
        
        with patch('src.services.model_testing_service.LLMModelTest', return_value=mock_test):
            # Execute
            result = service.create_test_session('test-user-id', 'test-job-id', test_config)
            
            # Verify
            assert result == 'test-session-id'
            mock_db.session.add.assert_called_once()
            mock_db.session.commit.assert_called_once()
    
    @patch('src.services.model_testing_service.db')
    @patch('src.services.model_testing_service.LLMTrainingJob')
    def test_create_test_session_job_not_found(self, mock_job_class, mock_db, service, test_config):
        """Test test session creation with non-existent job"""
        # Setup mocks
        mock_job_class.query.filter_by.return_value.first.return_value = None
        
        # Execute and verify
        with pytest.raises(ValueError, match="Training job not found"):
            service.create_test_session('test-user-id', 'invalid-job-id', test_config)
    
    @patch('src.services.model_testing_service.db')
    @patch('src.services.model_testing_service.LLMTrainingJob')
    def test_create_test_session_job_not_completed(self, mock_job_class, mock_db, service, mock_training_job, test_config):
        """Test test session creation with incomplete job"""
        # Setup mocks
        mock_training_job.status = 'training'
        mock_job_class.query.filter_by.return_value.first.return_value = mock_training_job
        
        # Execute and verify
        with pytest.raises(ValueError, match="Training job must be completed"):
            service.create_test_session('test-user-id', 'test-job-id', test_config)
    
    @patch('src.services.model_testing_service.current_app')
    @patch('src.services.model_testing_service.db')
    @patch('src.services.model_testing_service.os')
    def test_upload_test_submissions_success(self, mock_os, mock_db, mock_app, service):
        """Test successful test submission upload"""
        # Setup mocks
        mock_test = Mock(spec=LLMModelTest)
        mock_test.id = 'test-id'
        mock_db.session.get.return_value = mock_test
        
        mock_app.root_path = '/test/path'
        mock_os.path.join.return_value = '/test/path/uploads/test_submissions'
        mock_os.makedirs = Mock()
        mock_os.path.getsize.return_value = 1024
        
        # Mock file processor
        service.file_processor = Mock()
        service.file_processor.process_file_with_fallback.return_value = {
            'success': True,
            'text_content': 'Test content',
            'word_count': 10,
            'validation_errors': [],
            'processing_duration_ms': 100
        }
        
        # Test files
        files = [
            {
                'original_name': 'test1.txt',
                'content': b'Test content 1',
                'expected_grade': 0.8
            },
            {
                'original_name': 'test2.txt',
                'content': b'Test content 2',
                'expected_grade': 0.9
            }
        ]
        
        with patch('builtins.open', create=True) as mock_open:
            with patch('src.services.model_testing_service.LLMTestSubmission') as mock_submission_class:
                mock_submission = Mock()
                mock_submission.to_dict.return_value = {'id': 'sub-id', 'name': 'test1.txt'}
                mock_submission_class.return_value = mock_submission
                
                # Execute
                result = service.upload_test_submissions('test-id', files)
                
                # Verify
                assert len(result) == 2
                assert mock_db.session.add.call_count == 2
                mock_db.session.commit.assert_called_once()
    
    @patch('src.services.model_testing_service.db')
    def test_upload_test_submissions_test_not_found(self, mock_db, service):
        """Test upload with non-existent test session"""
        # Setup mocks
        mock_db.session.get.return_value = None
        
        # Execute and verify
        with pytest.raises(ValueError, match="Test session not found"):
            service.upload_test_submissions('invalid-test-id', [])
    
    @patch('src.services.model_testing_service.db')
    @patch('src.services.model_testing_service.threading')
    def test_run_model_test_success(self, mock_threading, mock_db, service):
        """Test successful model test execution"""
        # Setup mocks
        mock_test = Mock(spec=LLMModelTest)
        mock_test.status = 'ready'
        mock_db.session.get.return_value = mock_test
        
        mock_thread = Mock()
        mock_threading.Thread.return_value = mock_thread
        
        # Execute
        result = service.run_model_test('test-id')
        
        # Verify
        assert result['status'] == 'started'
        assert result['test_id'] == 'test-id'
        mock_thread.start.assert_called_once()
        mock_db.session.commit.assert_called_once()
    
    @patch('src.services.model_testing_service.db')
    def test_run_model_test_invalid_status(self, mock_db, service):
        """Test model test execution with invalid status"""
        # Setup mocks
        mock_test = Mock(spec=LLMModelTest)
        mock_test.status = 'completed'
        mock_db.session.get.return_value = mock_test
        
        # Execute and verify
        with pytest.raises(ValueError, match="Test cannot be started"):
            service.run_model_test('test-id')
    
    @patch('src.services.model_testing_service.db')
    def test_run_model_test_already_running(self, mock_db, service):
        """Test model test execution when already running"""
        # Setup mocks
        mock_test = Mock(spec=LLMModelTest)
        mock_test.status = 'ready'
        mock_db.session.get.return_value = mock_test
        
        # Add test to running tests
        service._running_tests['test-id'] = Mock()
        
        # Execute
        result = service.run_model_test('test-id')
        
        # Verify
        assert result['status'] == 'already_running'
    
    def test_process_submission_with_model(self, service):
        """Test submission processing with model"""
        # Create mock submission and test session
        mock_submission = Mock(spec=LLMTestSubmission)
        mock_submission.original_name = 'test.txt'
        mock_submission.expected_grade = 0.8
        
        mock_test_session = Mock(spec=LLMModelTest)
        mock_test_session.training_job.model_id = 'test-model'
        
        # Execute
        result = service._process_submission_with_model(mock_submission, mock_test_session)
        
        # Verify
        assert 'grade' in result
        assert 'feedback' in result
        assert 'confidence' in result
        assert 'detailed_results' in result
        assert 0 <= result['grade'] <= 1
        assert 0 <= result['confidence'] <= 1
    
    @patch('src.services.model_testing_service.db')
    def test_get_test_results_success(self, mock_db, service):
        """Test successful test results retrieval"""
        # Setup mocks
        mock_test = Mock(spec=LLMModelTest)
        mock_test.to_dict.return_value = {'id': 'test-id', 'name': 'Test'}
        mock_test.results = {'accuracy': 0.85}
        mock_test.performance_metrics = {'avg_confidence': 0.9}
        
        with patch('src.services.model_testing_service.LLMModelTest') as mock_test_class:
            mock_test_class.query.filter_by.return_value.first.return_value = mock_test
            
            with patch('src.services.model_testing_service.LLMTestSubmission') as mock_sub_class:
                mock_submissions = [Mock(), Mock()]
                for sub in mock_submissions:
                    sub.to_dict.return_value = {'id': 'sub-id'}
                mock_sub_class.query.filter_by.return_value.all.return_value = mock_submissions
                
                # Execute
                result = service.get_test_results('test-id', 'user-id')
                
                # Verify
                assert 'test_info' in result
                assert 'submissions' in result
                assert 'summary' in result
                assert 'performance_metrics' in result
                assert len(result['submissions']) == 2
    
    @patch('src.services.model_testing_service.db')
    def test_get_test_results_not_found(self, mock_db, service):
        """Test test results retrieval with non-existent test"""
        with patch('src.services.model_testing_service.LLMModelTest') as mock_test_class:
            mock_test_class.query.filter_by.return_value.first.return_value = None
            
            # Execute and verify
            with pytest.raises(ValueError, match="Test session not found"):
                service.get_test_results('invalid-test-id', 'user-id')
    
    @patch('src.services.model_testing_service.db')
    def test_cancel_test_success(self, mock_db, service):
        """Test successful test cancellation"""
        # Setup mocks
        mock_test = Mock(spec=LLMModelTest)
        mock_test.status = 'running'
        
        with patch('src.services.model_testing_service.LLMModelTest') as mock_test_class:
            mock_test_class.query.filter_by.return_value.first.return_value = mock_test
            
            # Execute
            result = service.cancel_test('test-id', 'user-id')
            
            # Verify
            assert result is True
            assert mock_test.status == 'cancelled'
            mock_db.session.commit.assert_called_once()
    
    @patch('src.services.model_testing_service.db')
    def test_cancel_test_invalid_status(self, mock_db, service):
        """Test test cancellation with invalid status"""
        # Setup mocks
        mock_test = Mock(spec=LLMModelTest)
        mock_test.status = 'completed'
        
        with patch('src.services.model_testing_service.LLMModelTest') as mock_test_class:
            mock_test_class.query.filter_by.return_value.first.return_value = mock_test
            
            # Execute and verify
            with pytest.raises(ValueError, match="Test cannot be cancelled"):
                service.cancel_test('test-id', 'user-id')
    
    def test_cleanup(self, service):
        """Test service cleanup"""
        # Add some mock running tests
        service._running_tests['test1'] = Mock()
        service._running_tests['test2'] = Mock()
        service._cancelled_tests.add('test3')
        
        # Execute
        service.cleanup()
        
        # Verify
        assert len(service._running_tests) == 0
        assert len(service._cancelled_tests) == 0

class TestModelTestingServiceIntegration:
    """Integration tests for ModelTestingService"""
    
    @pytest.fixture
    def service(self):
        """Create ModelTestingService instance for integration testing"""
        return ModelTestingService()
    
    def test_full_workflow_simulation(self, service):
        """Test complete model testing workflow simulation"""
        # This would be a more comprehensive integration test
        
        # For now, just verify service initialization
        assert service is not None
        assert hasattr(service, 'file_processor')
        assert hasattr(service, '_running_tests')
        assert hasattr(service, '_cancelled_tests')
    
    def test_concurrent_test_execution(self, service):
        """Test handling of concurrent test executions"""
        # This would test the threading and concurrency aspects
        # of the service when multiple tests run simultaneously
        
        # For now, just verify the tracking structures
        assert isinstance(service._running_tests, dict)
        assert isinstance(service._cancelled_tests, set)

if __name__ == '__main__':
    pytest.main([__file__])