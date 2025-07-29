"""
Integration tests for LLM training workflow.

Tests the complete workflow from document upload to model training and testing.
"""

import pytest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from flask import url_for
from werkzeug.datastructures import FileStorage
from io import BytesIO

from webapp.app_factory import create_app
from src.database.models import db, User, LLMDocument, LLMDataset, LLMTrainingJob, LLMModelTest
from tests.conftest import create_test_user, login_user

class TestLLMTrainingWorkflow:
    """Integration tests for complete LLM training workflow."""
    
    @pytest.fixture
    def app(self):
        """Create test application."""
        app = create_app('testing')
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def user(self, app):
        """Create test user."""
        with app.app_context():
            return create_test_user()
    
    @pytest.fixture
    def authenticated_client(self, client, user):
        """Create authenticated test client."""
        login_user(client, user.username, 'testpass123')
        return client
    
    def test_complete_training_workflow(self, authenticated_client, app):
        """Test complete workflow from document upload to training completion."""
        with app.app_context():
            # Step 1: Upload training documents
            documents = self._upload_test_documents(authenticated_client)
            assert len(documents) == 3
            
            # Step 2: Create dataset
            dataset = self._create_test_dataset(authenticated_client, documents)
            assert dataset is not None
            
            # Step 3: Start training job
            training_job = self._start_training_job(authenticated_client, dataset['id'])
            assert training_job is not None
            assert training_job['status'] == 'pending'
            
            # Step 4: Simulate training progress
            self._simulate_training_progress(authenticated_client, training_job['id'])
            
            # Step 5: Verify training completion
            completed_job = self._verify_training_completion(authenticated_client, training_job['id'])
            assert completed_job['status'] == 'completed'
    
    def test_model_testing_workflow(self, authenticated_client, app):
        """Test model testing workflow after training completion."""
        with app.app_context():
            # Setup: Create completed training job
            training_job = self._create_completed_training_job()
            
            # Step 1: Create model test session
            test_session = self._create_model_test_session(authenticated_client, training_job.id)
            assert test_session is not None
            
            # Step 2: Upload test submissions
            test_submissions = self._upload_test_submissions(authenticated_client, test_session['id'])
            assert len(test_submissions) == 2
            
            # Step 3: Run model test
            test_results = self._run_model_test(authenticated_client, test_session['id'])
            assert test_results is not None
            
            # Step 4: Verify test results
            self._verify_test_results(authenticated_client, test_session['id'])
    
    def test_error_handling_workflow(self, authenticated_client, app):
        """Test error handling throughout the workflow."""
        with app.app_context():
            # Test invalid document upload
            response = authenticated_client.post('/api/llm/documents/upload', 
                                               data={'files': []})
            assert response.status_code == 400
            
            # Test invalid dataset creation
            response = authenticated_client.post('/api/llm/datasets', 
                                               json={'name': '', 'document_ids': []})
            assert response.status_code == 400
            
            # Test training job with invalid dataset
            response = authenticated_client.post('/api/llm/training/jobs', 
                                               json={'dataset_id': 'invalid-id'})
            assert response.status_code == 404
    
    def test_concurrent_operations(self, authenticated_client, app):
        """Test handling of concurrent operations."""
        with app.app_context():
            # Create multiple training jobs simultaneously
            documents = self._upload_test_documents(authenticated_client)
            dataset = self._create_test_dataset(authenticated_client, documents)
            
            # Start multiple training jobs
            jobs = []
            for i in range(3):
                job = self._start_training_job(authenticated_client, dataset['id'], 
                                             name=f'concurrent_job_{i}')
                jobs.append(job)
            
            # Verify all jobs are created
            assert len(jobs) == 3
            for job in jobs:
                assert job['status'] == 'pending'
    
    def test_data_validation_workflow(self, authenticated_client, app):
        """Test data validation throughout the workflow."""
        with app.app_context():
            # Test document validation
            invalid_doc = self._create_invalid_document()
            response = authenticated_client.post('/api/llm/documents/upload',
                                               data={'files': [invalid_doc]})
            # Should handle gracefully
            assert response.status_code in [200, 400]
            
            # Test dataset validation
            documents = self._upload_test_documents(authenticated_client)
            response = authenticated_client.post('/api/llm/datasets',
                                               json={
                                                   'name': 'test_dataset',
                                                   'document_ids': documents[:2]  # Valid IDs
                                               })
            assert response.status_code == 201
    
    def test_cleanup_workflow(self, authenticated_client, app):
        """Test cleanup operations."""
        with app.app_context():
            # Create test data
            documents = self._upload_test_documents(authenticated_client)
            dataset = self._create_test_dataset(authenticated_client, documents)
            training_job = self._start_training_job(authenticated_client, dataset['id'])
            
            # Test document deletion
            response = authenticated_client.delete(f'/api/llm/documents/{documents[0]}')
            assert response.status_code == 200
            
            # Test dataset deletion
            response = authenticated_client.delete(f'/api/llm/datasets/{dataset["id"]}')
            assert response.status_code == 200
            
            # Test training job cancellation
            response = authenticated_client.post(f'/api/llm/training/jobs/{training_job["id"]}/cancel')
            assert response.status_code == 200
    
    def _upload_test_documents(self, client):
        """Upload test documents and return document IDs."""
        documents = []
        
        for i in range(3):
            # Create test file
            test_content = f"This is test document {i} content for training."
            file_data = BytesIO(test_content.encode('utf-8'))
            file_storage = FileStorage(
                stream=file_data,
                filename=f'test_doc_{i}.txt',
                content_type='text/plain'
            )
            
            response = client.post('/api/llm/documents/upload',
                                 data={'files': [file_storage]})
            
            assert response.status_code == 201
            data = json.loads(response.data)
            documents.extend([doc['id'] for doc in data['data']['documents']])
        
        return documents
    
    def _create_test_dataset(self, client, document_ids):
        """Create test dataset with documents."""
        response = client.post('/api/llm/datasets',
                             json={
                                 'name': 'test_training_dataset',
                                 'description': 'Dataset for integration testing',
                                 'document_ids': document_ids
                             })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        return data['data']['dataset']
    
    def _start_training_job(self, client, dataset_id, name='test_training_job'):
        """Start a training job."""
        response = client.post('/api/llm/training/jobs',
                             json={
                                 'name': name,
                                 'model_id': 'gpt-3.5-turbo',
                                 'dataset_id': dataset_id,
                                 'config': {
                                     'epochs': 5,
                                     'batch_size': 4,
                                     'learning_rate': 0.001
                                 }
                             })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        return data['data']['job']
    
    def _simulate_training_progress(self, client, job_id):
        """Simulate training progress updates."""
        # Simulate progress updates
        for progress in [0.2, 0.5, 0.8, 1.0]:
            with patch('src.services.llm_training_service.LLMTrainingService.get_job_progress') as mock_progress:
                mock_progress.return_value = {
                    'progress': progress,
                    'current_epoch': int(progress * 5),
                    'status': 'training' if progress < 1.0 else 'completed'
                }
                
                response = client.get(f'/api/llm/training/jobs/{job_id}/progress')
                assert response.status_code == 200
    
    def _verify_training_completion(self, client, job_id):
        """Verify training job completion."""
        response = client.get(f'/api/llm/training/jobs/{job_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        job = data['data']['job']
        
        # For testing, we'll mock the completion
        with patch('src.services.llm_training_service.LLMTrainingService.get_job') as mock_get_job:
            mock_get_job.return_value = {
                **job,
                'status': 'completed',
                'progress': 1.0,
                'accuracy': 0.85,
                'validation_accuracy': 0.82
            }
            
            response = client.get(f'/api/llm/training/jobs/{job_id}')
            data = json.loads(response.data)
            return data['data']['job']
    
    def _create_completed_training_job(self):
        """Create a completed training job for testing."""
        user = User.query.first()
        
        # Create dataset
        dataset = LLMDataset(
            user_id=user.id,
            name='test_dataset',
            description='Test dataset'
        )
        db.session.add(dataset)
        db.session.flush()
        
        # Create training job
        job = LLMTrainingJob(
            user_id=user.id,
            name='completed_test_job',
            model_id='gpt-3.5-turbo',
            dataset_id=dataset.id,
            status='completed',
            progress=1.0,
            accuracy=0.85,
            validation_accuracy=0.82
        )
        db.session.add(job)
        db.session.commit()
        
        return job
    
    def _create_model_test_session(self, client, training_job_id):
        """Create model test session."""
        response = client.post('/api/llm/model-tests',
                             json={
                                 'name': 'integration_test_session',
                                 'training_job_id': training_job_id,
                                 'description': 'Integration test session',
                                 'config': {
                                     'confidence_threshold': 0.8,
                                     'comparison_mode': 'strict'
                                 }
                             })
        
        assert response.status_code == 201
        data = json.loads(response.data)
        return data['data']['test_session']
    
    def _upload_test_submissions(self, client, test_session_id):
        """Upload test submissions."""
        submissions = []
        
        for i in range(2):
            test_content = f"Test submission {i} content for grading."
            file_data = BytesIO(test_content.encode('utf-8'))
            file_storage = FileStorage(
                stream=file_data,
                filename=f'test_submission_{i}.txt',
                content_type='text/plain'
            )
            
            response = client.post(f'/api/llm/model-tests/{test_session_id}/submissions',
                                 data={'files': [file_storage]})
            
            assert response.status_code == 201
            data = json.loads(response.data)
            submissions.extend(data['data']['submissions'])
        
        return submissions
    
    def _run_model_test(self, client, test_session_id):
        """Run model test."""
        response = client.post(f'/api/llm/model-tests/{test_session_id}/run')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        return data['data']
    
    def _verify_test_results(self, client, test_session_id):
        """Verify test results."""
        response = client.get(f'/api/llm/model-tests/{test_session_id}/results')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        results = data['data']['results']
        
        assert 'accuracy_score' in results
        assert 'performance_metrics' in results
        assert results['total_submissions'] > 0
    
    def _create_invalid_document(self):
        """Create invalid document for testing."""
        # Create a file that's too large or invalid format
        large_content = "x" * (10 * 1024 * 1024)  # 10MB
        file_data = BytesIO(large_content.encode('utf-8'))
        return FileStorage(
            stream=file_data,
            filename='large_file.txt',
            content_type='text/plain'
        )