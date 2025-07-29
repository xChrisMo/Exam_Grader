"""
Performance tests for LLM training system.

Tests system performance under various load conditions.
"""

import pytest
import time
import threading
import concurrent.futures
import tempfile
import os
from unittest.mock import patch
import statistics
from io import BytesIO
from werkzeug.datastructures import FileStorage

from webapp.app_factory import create_app
from src.database.models import db, User, LLMDocument, LLMDataset, LLMTrainingJob
from tests.conftest import create_test_user, login_user

class TestLLMPerformance:
    """Performance tests for LLM training system."""
    
    @pytest.fixture
    def app(self):
        """Create test application."""
        app = create_app('testing')
        app.config['TESTING'] = True
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
    
    def test_concurrent_document_uploads(self, authenticated_client, app):
        """Test performance with concurrent document uploads."""
        with app.app_context():
            num_concurrent_uploads = 10
            file_size_kb = 100  # 100KB files
            
            def upload_document(client, file_index):
                """Upload a single document."""
                start_time = time.time()
                
                # Create test file
                content = "x" * (file_size_kb * 1024)
                file_data = BytesIO(content.encode('utf-8'))
                file_storage = FileStorage(
                    stream=file_data,
                    filename=f'perf_test_{file_index}.txt',
                    content_type='text/plain'
                )
                
                response = client.post('/api/llm/documents/upload',
                                     data={'files': [file_storage]})
                
                end_time = time.time()
                return {
                    'status_code': response.status_code,
                    'duration': end_time - start_time,
                    'file_index': file_index
                }
            
            # Execute concurrent uploads
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_uploads) as executor:
                futures = [
                    executor.submit(upload_document, authenticated_client, i)
                    for i in range(num_concurrent_uploads)
                ]
                
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Analyze results
            successful_uploads = [r for r in results if r['status_code'] in [200, 201]]
            durations = [r['duration'] for r in successful_uploads]
            
            assert len(successful_uploads) == num_concurrent_uploads
            assert statistics.mean(durations) < 5.0  # Average under 5 seconds
            assert max(durations) < 10.0  # No upload takes more than 10 seconds
            
            print(f"Concurrent uploads performance:")
            print(f"  Average duration: {statistics.mean(durations):.2f}s")
            print(f"  Max duration: {max(durations):.2f}s")
            print(f"  Min duration: {min(durations):.2f}s")
    
    def test_large_file_upload_performance(self, authenticated_client, app):
        """Test performance with large file uploads."""
        with app.app_context():
            file_sizes_mb = [1, 5, 10]  # Test different file sizes
            
            for size_mb in file_sizes_mb:
                start_time = time.time()
                
                # Create large test file
                content = "x" * (size_mb * 1024 * 1024)
                file_data = BytesIO(content.encode('utf-8'))
                file_storage = FileStorage(
                    stream=file_data,
                    filename=f'large_file_{size_mb}mb.txt',
                    content_type='text/plain'
                )
                
                response = authenticated_client.post('/api/llm/documents/upload',
                                                   data={'files': [file_storage]})
                
                end_time = time.time()
                duration = end_time - start_time
                
                assert response.status_code in [200, 201]
                
                # Performance expectations based on file size
                max_expected_time = size_mb * 2  # 2 seconds per MB
                assert duration < max_expected_time
                
                print(f"Large file upload ({size_mb}MB): {duration:.2f}s")
    
    def test_batch_processing_performance(self, authenticated_client, app):
        """Test performance of batch processing operations."""
        with app.app_context():
            # Create multiple documents first
            document_ids = []
            for i in range(20):
                content = f"Batch test document {i} content."
                file_data = BytesIO(content.encode('utf-8'))
                file_storage = FileStorage(
                    stream=file_data,
                    filename=f'batch_doc_{i}.txt',
                    content_type='text/plain'
                )
                
                response = authenticated_client.post('/api/llm/documents/upload',
                                                   data={'files': [file_storage]})
                assert response.status_code in [200, 201]
                
                data = response.get_json()
                document_ids.extend([doc['id'] for doc in data['data']['documents']])
            
            # Test batch dataset creation
            start_time = time.time()
            
            response = authenticated_client.post('/api/llm/datasets',
                                               json={
                                                   'name': 'batch_performance_dataset',
                                                   'description': 'Performance test dataset',
                                                   'document_ids': document_ids
                                               })
            
            end_time = time.time()
            duration = end_time - start_time
            
            assert response.status_code == 201
            assert duration < 5.0  # Should complete within 5 seconds
            
            print(f"Batch dataset creation (20 docs): {duration:.2f}s")
    
    def test_concurrent_training_jobs(self, authenticated_client, app):
        """Test performance with multiple concurrent training jobs."""
        with app.app_context():
            # Create dataset first
            dataset = self._create_test_dataset(authenticated_client)
            
            num_concurrent_jobs = 5
            
            def start_training_job(client, job_index):
                """Start a single training job."""
                start_time = time.time()
                
                response = client.post('/api/llm/training/jobs',
                                     json={
                                         'name': f'concurrent_job_{job_index}',
                                         'model_id': 'gpt-3.5-turbo',
                                         'dataset_id': dataset['id'],
                                         'config': {
                                             'epochs': 3,
                                             'batch_size': 4,
                                             'learning_rate': 0.001
                                         }
                                     })
                
                end_time = time.time()
                return {
                    'status_code': response.status_code,
                    'duration': end_time - start_time,
                    'job_index': job_index
                }
            
            # Execute concurrent job starts
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_jobs) as executor:
                futures = [
                    executor.submit(start_training_job, authenticated_client, i)
                    for i in range(num_concurrent_jobs)
                ]
                
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Analyze results
            successful_jobs = [r for r in results if r['status_code'] in [200, 201]]
            durations = [r['duration'] for r in successful_jobs]
            
            assert len(successful_jobs) == num_concurrent_jobs
            assert statistics.mean(durations) < 3.0  # Average under 3 seconds
            
            print(f"Concurrent training job starts:")
            print(f"  Average duration: {statistics.mean(durations):.2f}s")
            print(f"  Max duration: {max(durations):.2f}s")
    
    def test_database_query_performance(self, authenticated_client, app):
        """Test database query performance under load."""
        with app.app_context():
            # Create test data
            self._create_performance_test_data()
            
            # Test various query patterns
            query_tests = [
                ('Document list query', lambda: LLMDocument.query.all()),
                ('Dataset list query', lambda: LLMDataset.query.all()),
                ('Training job list query', lambda: LLMTrainingJob.query.all()),
                ('User documents query', lambda: LLMDocument.query.filter_by(user_id=User.query.first().id).all()),
                ('Recent jobs query', lambda: LLMTrainingJob.query.order_by(LLMTrainingJob.created_at.desc()).limit(10).all())
            ]
            
            for test_name, query_func in query_tests:
                # Run query multiple times to get average
                durations = []
                for _ in range(10):
                    start_time = time.time()
                    results = query_func()
                    end_time = time.time()
                    durations.append(end_time - start_time)
                
                avg_duration = statistics.mean(durations)
                max_duration = max(durations)
                
                # Performance expectations
                assert avg_duration < 0.5  # Average under 500ms
                assert max_duration < 1.0  # Max under 1 second
                
                print(f"{test_name}: avg={avg_duration*1000:.1f}ms, max={max_duration*1000:.1f}ms")
    
    def test_api_response_times(self, authenticated_client, app):
        """Test API endpoint response times."""
        with app.app_context():
            # Create some test data
            dataset = self._create_test_dataset(authenticated_client)
            
            # Test various API endpoints
            endpoints = [
                ('GET', '/api/llm/documents'),
                ('GET', '/api/llm/datasets'),
                ('GET', '/api/llm/training/jobs'),
                ('GET', f'/api/llm/datasets/{dataset["id"]}'),
                ('GET', '/api/llm/training/models'),
            ]
            
            for method, endpoint in endpoints:
                durations = []
                
                # Test each endpoint multiple times
                for _ in range(5):
                    start_time = time.time()
                    
                    if method == 'GET':
                        response = authenticated_client.get(endpoint)
                    elif method == 'POST':
                        response = authenticated_client.post(endpoint, json={})
                    
                    end_time = time.time()
                    durations.append(end_time - start_time)
                    
                    assert response.status_code in [200, 201, 400, 404]  # Valid responses
                
                avg_duration = statistics.mean(durations)
                max_duration = max(durations)
                
                # Performance expectations
                assert avg_duration < 2.0  # Average under 2 seconds
                assert max_duration < 5.0  # Max under 5 seconds
                
                print(f"{method} {endpoint}: avg={avg_duration*1000:.0f}ms, max={max_duration*1000:.0f}ms")
    
    def test_memory_usage_under_load(self, authenticated_client, app):
        """Test memory usage under load conditions."""
        import psutil
        import gc
        
        with app.app_context():
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Perform memory-intensive operations
            for i in range(50):
                # Upload document
                content = "x" * (100 * 1024)  # 100KB
                file_data = BytesIO(content.encode('utf-8'))
                file_storage = FileStorage(
                    stream=file_data,
                    filename=f'memory_test_{i}.txt',
                    content_type='text/plain'
                )
                
                response = authenticated_client.post('/api/llm/documents/upload',
                                                   data={'files': [file_storage]})
                assert response.status_code in [200, 201]
                
                # Check memory every 10 iterations
                if i % 10 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_increase = current_memory - initial_memory
                    
                    print(f"Iteration {i}: Memory usage = {current_memory:.1f}MB (+{memory_increase:.1f}MB)")
                    
                    # Memory shouldn't grow excessively
                    assert memory_increase < 500  # Less than 500MB increase
            
            # Force garbage collection
            gc.collect()
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            total_increase = final_memory - initial_memory
            
            print(f"Total memory increase: {total_increase:.1f}MB")
            assert total_increase < 200  # Less than 200MB total increase
    
    def test_concurrent_api_requests(self, authenticated_client, app):
        """Test performance with concurrent API requests."""
        with app.app_context():
            num_concurrent_requests = 20
            
            def make_api_request(client, request_index):
                """Make a single API request."""
                start_time = time.time()
                
                # Alternate between different endpoints
                endpoints = [
                    '/api/llm/documents',
                    '/api/llm/datasets',
                    '/api/llm/training/jobs',
                    '/api/llm/training/models'
                ]
                
                endpoint = endpoints[request_index % len(endpoints)]
                response = client.get(endpoint)
                
                end_time = time.time()
                return {
                    'status_code': response.status_code,
                    'duration': end_time - start_time,
                    'endpoint': endpoint
                }
            
            # Execute concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_requests) as executor:
                futures = [
                    executor.submit(make_api_request, authenticated_client, i)
                    for i in range(num_concurrent_requests)
                ]
                
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Analyze results
            successful_requests = [r for r in results if r['status_code'] == 200]
            durations = [r['duration'] for r in successful_requests]
            
            assert len(successful_requests) >= num_concurrent_requests * 0.9  # 90% success rate
            assert statistics.mean(durations) < 3.0  # Average under 3 seconds
            assert max(durations) < 10.0  # No request takes more than 10 seconds
            
            print(f"Concurrent API requests:")
            print(f"  Success rate: {len(successful_requests)}/{num_concurrent_requests}")
            print(f"  Average duration: {statistics.mean(durations):.2f}s")
            print(f"  Max duration: {max(durations):.2f}s")
    
    def test_load_testing_simulation(self, authenticated_client, app):
        """Simulate realistic load testing scenario."""
        with app.app_context():
            # Simulate realistic user behavior
            num_users = 5
            operations_per_user = 10
            
            def simulate_user_session(client, user_index):
                """Simulate a complete user session."""
                session_start = time.time()
                operations = []
                
                for op_index in range(operations_per_user):
                    op_start = time.time()
                    
                    # Simulate different user actions
                    if op_index % 4 == 0:
                        # Upload document
                        content = f"User {user_index} document {op_index}"
                        file_data = BytesIO(content.encode('utf-8'))
                        file_storage = FileStorage(
                            stream=file_data,
                            filename=f'user_{user_index}_doc_{op_index}.txt',
                            content_type='text/plain'
                        )
                        response = client.post('/api/llm/documents/upload',
                                             data={'files': [file_storage]})
                    elif op_index % 4 == 1:
                        # List documents
                        response = client.get('/api/llm/documents')
                    elif op_index % 4 == 2:
                        # List datasets
                        response = client.get('/api/llm/datasets')
                    else:
                        # List training jobs
                        response = client.get('/api/llm/training/jobs')
                    
                    op_end = time.time()
                    operations.append({
                        'operation': op_index,
                        'duration': op_end - op_start,
                        'status_code': response.status_code
                    })
                    
                    # Small delay between operations
                    time.sleep(0.1)
                
                session_end = time.time()
                return {
                    'user_index': user_index,
                    'session_duration': session_end - session_start,
                    'operations': operations
                }
            
            # Execute concurrent user sessions
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
                futures = [
                    executor.submit(simulate_user_session, authenticated_client, i)
                    for i in range(num_users)
                ]
                
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Analyze results
            all_operations = []
            for result in results:
                all_operations.extend(result['operations'])
            
            successful_ops = [op for op in all_operations if op['status_code'] in [200, 201]]
            durations = [op['duration'] for op in successful_ops]
            
            success_rate = len(successful_ops) / len(all_operations)
            avg_duration = statistics.mean(durations)
            
            assert success_rate >= 0.95  # 95% success rate
            assert avg_duration < 2.0  # Average under 2 seconds
            
            print(f"Load testing simulation:")
            print(f"  Users: {num_users}")
            print(f"  Operations per user: {operations_per_user}")
            print(f"  Success rate: {success_rate:.1%}")
            print(f"  Average operation duration: {avg_duration:.2f}s")
    
    def _create_test_dataset(self, client):
        """Create a test dataset for performance testing."""
        # Upload a few documents first
        document_ids = []
        for i in range(3):
            content = f"Performance test document {i} content."
            file_data = BytesIO(content.encode('utf-8'))
            file_storage = FileStorage(
                stream=file_data,
                filename=f'perf_doc_{i}.txt',
                content_type='text/plain'
            )
            
            response = client.post('/api/llm/documents/upload',
                                 data={'files': [file_storage]})
            assert response.status_code in [200, 201]
            
            data = response.get_json()
            document_ids.extend([doc['id'] for doc in data['data']['documents']])
        
        # Create dataset
        response = client.post('/api/llm/datasets',
                             json={
                                 'name': 'performance_test_dataset',
                                 'description': 'Dataset for performance testing',
                                 'document_ids': document_ids
                             })
        
        assert response.status_code == 201
        data = response.get_json()
        return data['data']['dataset']
    
    def _create_performance_test_data(self):
        """Create test data for performance testing."""
        user = User.query.first()
        
        # Create documents
        for i in range(50):
            doc = LLMDocument(
                user_id=user.id,
                name=f'perf_doc_{i}',
                original_name=f'perf_doc_{i}.txt',
                stored_name=f'perf_doc_{i}.txt',
                file_type='txt',
                mime_type='text/plain',
                file_size=1024,
                file_path=f'/tmp/perf_doc_{i}.txt',
                text_content=f'Performance test document {i} content.',
                word_count=10,
                character_count=100,
                extracted_text=True
            )
            db.session.add(doc)
        
        # Create datasets
        for i in range(10):
            dataset = LLMDataset(
                user_id=user.id,
                name=f'perf_dataset_{i}',
                description=f'Performance test dataset {i}',
                document_count=5,
                total_words=50,
                total_size=5120
            )
            db.session.add(dataset)
        
        # Create training jobs
        for i in range(20):
            job = LLMTrainingJob(
                user_id=user.id,
                name=f'perf_job_{i}',
                model_id='gpt-3.5-turbo',
                dataset_id=LLMDataset.query.first().id,
                status='completed' if i % 3 == 0 else 'pending',
                progress=1.0 if i % 3 == 0 else 0.0
            )
            db.session.add(job)
        
        db.session.commit()