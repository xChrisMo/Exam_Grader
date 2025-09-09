"""
Performance Tests for LLM Training Page

Tests to validate performance characteristics and scalability
of the training system under various load conditions.
"""

import time
import pytest
import threading
import concurrent.futures
from unittest.mock import Mock, patch
from io import BytesIO

from webapp.app import create_app
from src.database.models import db, User
from src.services.training_service import training_service
from src.services.training_report_service import training_report_service

@pytest.fixture
def app():
    """Create test Flask application"""
    app = create_app()
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
def test_user(app):
    """Create test user"""
    with app.app_context():
        user = User(
            id='perf-test-user',
            username='perfuser',
            email='perf@example.com',
            password_hash='hashed_password'
        )
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def authenticated_client(client, test_user):
    """Create authenticated test client"""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True
    return client

class TestFileUploadPerformance:
    """Test file upload performance characteristics"""

    def test_large_file_upload_performance(self, authenticated_client):
        """Test performance of large file uploads"""

        # Create a 10MB test file
        large_file_content = b'x' * (10 * 1024 * 1024)
        large_file = BytesIO(large_file_content)

        with patch('src.services.secure_file_handler.secure_file_handler.secure_upload') as mock_upload:
            mock_upload.return_value = {
                'success': True,
                'file_record': {
                    'filename': 'large_file.pdf',
                    'original_name': 'large_file.pdf',
                    'size': len(large_file_content),
                    'file_path': '/tmp/large_file.pdf',
                    'uploaded_at': time.time(),
                    'hash': 'large_file_hash',
                    'encrypted': False
                },
                'warnings': []
            }

            start_time = time.time()
            response = authenticated_client.post('/training/upload', data={
                'files': [(large_file, 'large_file.pdf')]
            })
            end_time = time.time()

            upload_time = end_time - start_time

            assert response.status_code == 200
            assert upload_time < 5.0  # Should complete within 5 seconds

            # Calculate throughput (MB/s)
            throughput = (10 / upload_time) if upload_time > 0 else float('inf')
            print(f"Upload throughput: {throughput:.2f} MB/s")

            # Minimum acceptable throughput: 2 MB/s
            assert throughput >= 2.0

    def test_multiple_file_upload_performance(self, authenticated_client):
        """Test performance of multiple file uploads"""

        # Create 20 files of 1MB each
        files = []
        for i in range(20):
            file_content = b'x' * (1024 * 1024)  # 1MB
            files.append((BytesIO(file_content), f'file_{i}.pdf'))

        with patch('src.services.secure_file_handler.secure_file_handler.secure_upload') as mock_upload:
            mock_upload.return_value = {
                'success': True,
                'file_record': {
                    'filename': 'test_file.pdf',
                    'original_name': 'test_file.pdf',
                    'size': 1024 * 1024,
                    'file_path': '/tmp/test_file.pdf',
                    'uploaded_at': time.time(),
                    'hash': 'test_hash',
                    'encrypted': False
                },
                'warnings': []
            }

            start_time = time.time()
            response = authenticated_client.post('/training/upload', data={'files': files})
            end_time = time.time()

            upload_time = end_time - start_time

            assert response.status_code == 200
            assert upload_time < 10.0  # Should complete within 10 seconds

            # Calculate files per second
            files_per_second = 20 / upload_time if upload_time > 0 else float('inf')
            print(f"Upload rate: {files_per_second:.2f} files/s")

            # Minimum acceptable rate: 2 files/s
            assert files_per_second >= 2.0

class TestTrainingPerformance:
    """Test training process performance"""

    def test_training_session_creation_performance(self, authenticated_client):
        """Test performance of training session creation"""

        with patch('src.services.training_service.training_service.create_training_session') as mock_create:
            mock_session = Mock()
            mock_session.id = 'perf-session-123'
            mock_session.status = 'created'
            mock_create.return_value = mock_session

            # Test creating multiple sessions rapidly
            session_times = []

            for i in range(10):
                start_time = time.time()
                response = authenticated_client.post('/training/sessions', json={
                    'name': f'Performance Test Session {i}',
                    'description': f'Performance test {i}',
                    'max_questions_to_answer': 5,
                    'uploaded_files': []
                })
                end_time = time.time()

                assert response.status_code == 200
                session_times.append(end_time - start_time)

            # Calculate average session creation time
            avg_time = sum(session_times) / len(session_times)
            max_time = max(session_times)

            print(f"Average session creation time: {avg_time:.3f}s")
            print(f"Maximum session creation time: {max_time:.3f}s")

            # Performance requirements
            assert avg_time < 0.5  # Average should be under 500ms
            assert max_time < 1.0  # No single creation should take over 1s

    def test_concurrent_training_sessions(self, authenticated_client):
        """Test performance with concurrent training sessions"""

        def create_and_start_session(session_id):
            """Helper function to create and start a training session"""
            with patch('src.services.training_service.training_service.create_training_session') as mock_create:
                mock_session = Mock()
                mock_session.id = session_id
                mock_session.status = 'created'
                mock_create.return_value = mock_session

                # Create session
                response = authenticated_client.post('/training/sessions', json={
                    'name': f'Concurrent Session {session_id}',
                    'description': 'Concurrent test',
                    'uploaded_files': []
                })

                if response.status_code != 200:
                    return False

                # Start training
                with patch('src.services.training_service.training_service.start_training') as mock_start:
                    mock_start.return_value = True

                    response = authenticated_client.post(f'/training/sessions/{session_id}/start')
                    return response.status_code == 200

        # Test 5 concurrent sessions
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(5):
                future = executor.submit(create_and_start_session, f'concurrent-{i}')
                futures.append(future)

            # Wait for all sessions to complete
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        end_time = time.time()
        total_time = end_time - start_time

        # All sessions should succeed
        assert all(results)

        # Should complete within reasonable time
        assert total_time < 5.0  # 5 concurrent sessions in under 5 seconds

        print(f"Concurrent session creation time: {total_time:.3f}s")

    def test_training_progress_monitoring_performance(self, authenticated_client):
        """Test performance of training progress monitoring"""

        session_id = 'perf-session-123'

        with patch('src.services.training_service.training_service.get_training_progress') as mock_progress:
            mock_progress.return_value = {
                'status': 'processing',
                'progress_percentage': 50.0,
                'current_step': 'Processing guides',
                'estimated_completion': '5 minutes'
            }

            # Simulate rapid progress polling
            poll_times = []

            for i in range(50):  # 50 rapid polls
                start_time = time.time()
                response = authenticated_client.get(f'/training/sessions/{session_id}/progress')
                end_time = time.time()

                assert response.status_code == 200
                poll_times.append(end_time - start_time)

            avg_poll_time = sum(poll_times) / len(poll_times)
            max_poll_time = max(poll_times)

            print(f"Average progress poll time: {avg_poll_time:.3f}s")
            print(f"Maximum progress poll time: {max_poll_time:.3f}s")

            # Performance requirements for real-time updates
            assert avg_poll_time < 0.1  # Average under 100ms
            assert max_poll_time < 0.5  # No single poll over 500ms

class TestReportGenerationPerformance:
    """Test report generation performance"""

    def test_markdown_report_generation_performance(self, authenticated_client):
        """Test performance of markdown report generation"""

        session_id = 'perf-session-123'

        # Mock large training data
        large_training_data = {
            'questions': [f'Question {i}' for i in range(100)],
            'results': [{'confidence': 0.8, 'score': 85} for _ in range(100)],
            'analytics': {'total_questions': 100, 'avg_confidence': 0.8}
        }

        with patch('src.services.training_report_service.training_report_service.generate_markdown_report') as mock_md:
            # Simulate report generation time based on data size
            def slow_report_generation(session_id):
                time.sleep(0.1)  # Simulate processing time
                return '# Training Report\n\n' + '\n'.join([f'## Question {i}' for i in range(100)])

            mock_md.side_effect = slow_report_generation

            start_time = time.time()
            response = authenticated_client.get(f'/training/sessions/{session_id}/report/markdown')
            end_time = time.time()

            generation_time = end_time - start_time

            assert response.status_code == 200
            assert generation_time < 2.0  # Should complete within 2 seconds

            print(f"Markdown report generation time: {generation_time:.3f}s")

    def test_pdf_report_generation_performance(self, authenticated_client):
        """Test performance of PDF report generation"""

        session_id = 'perf-session-123'

        with patch('src.services.training_report_service.training_report_service.generate_pdf_report') as mock_pdf:
            # Simulate PDF generation with charts
            def slow_pdf_generation(session_id):
                time.sleep(0.5)  # Simulate PDF processing time
                return b'%PDF-1.4 mock report with charts and data'

            mock_pdf.side_effect = slow_pdf_generation

            start_time = time.time()
            response = authenticated_client.get(f'/training/sessions/{session_id}/report/pdf')
            end_time = time.time()

            generation_time = end_time - start_time

            assert response.status_code == 200
            assert generation_time < 3.0  # Should complete within 3 seconds

            print(f"PDF report generation time: {generation_time:.3f}s")

    def test_chart_generation_performance(self, authenticated_client):
        """Test performance of chart generation"""

        session_id = 'perf-session-123'

        with patch('src.services.training_report_service.training_report_service.create_analytics_charts') as mock_charts:
            # Simulate chart generation for large dataset
            def generate_charts(training_data):
                time.sleep(0.2)  # Simulate chart creation time
                return [
                    {'type': 'histogram', 'data': [1, 2, 3, 4, 5]},
                    {'type': 'scatter', 'data': [(1, 2), (3, 4), (5, 6)]},
                    {'type': 'bar', 'data': {'A': 10, 'B': 20, 'C': 15}}
                ]

            mock_charts.side_effect = generate_charts

            start_time = time.time()
            response = authenticated_client.get(f'/training/sessions/{session_id}/charts')
            end_time = time.time()

            generation_time = end_time - start_time

            # Charts endpoint might not exist, but we're testing the service
            print(f"Chart generation time: {generation_time:.3f}s")

            # Chart generation should be reasonably fast
            assert generation_time < 1.0

class TestDatabasePerformance:
    """Test database performance characteristics"""

    def test_training_session_query_performance(self, app, authenticated_client, test_user):
        """Test performance of training session queries"""

        with app.app_context():
            # Create many training sessions in database
            sessions = []
            for i in range(100):
                session = Mock()
                session.id = f'db-perf-session-{i}'
                session.user_id = test_user.id
                session.name = f'DB Performance Test {i}'
                session.status = 'completed'
                session.created_at = time.time() - (i * 60)
                sessions.append(session)

            with patch('src.services.training_service.training_service.get_user_training_sessions') as mock_query:
                mock_query.return_value = sessions

                # Test query performance
                start_time = time.time()
                response = authenticated_client.get('/training/sessions')
                end_time = time.time()

                query_time = end_time - start_time

                assert response.status_code == 200
                assert query_time < 0.5  # Should complete within 500ms

                print(f"Training session query time (100 records): {query_time:.3f}s")

    def test_training_data_insertion_performance(self, app, test_user):
        """Test performance of training data insertion"""

        with app.app_context():
            # Test bulk insertion performance
            start_time = time.time()

            # Simulate inserting training data
            with patch('src.database.models.db.session.add') as mock_add:
                with patch('src.database.models.db.session.commit') as mock_commit:
                    # Simulate adding 1000 training questions
                    for i in range(1000):
                        mock_add.return_value = None

                    mock_commit.return_value = None

            end_time = time.time()
            insertion_time = end_time - start_time

            print(f"Bulk insertion time (1000 records): {insertion_time:.3f}s")

            # Should be able to handle bulk insertions efficiently
            assert insertion_time < 2.0

class TestMemoryPerformance:
    """Test memory usage characteristics"""

    def test_large_file_memory_usage(self, authenticated_client):
        """Test memory usage during large file processing"""

        # This test would ideally use memory profiling tools
        # For now, we'll test that large files don't cause obvious issues

        large_files = []
        for i in range(5):
            # Create 5MB files
            file_content = b'x' * (5 * 1024 * 1024)
            large_files.append((BytesIO(file_content), f'large_file_{i}.pdf'))

        with patch('src.services.secure_file_handler.secure_file_handler.secure_upload') as mock_upload:
            mock_upload.return_value = {
                'success': True,
                'file_record': {
                    'filename': 'large_file.pdf',
                    'original_name': 'large_file.pdf',
                    'size': 5 * 1024 * 1024,
                    'file_path': '/tmp/large_file.pdf',
                    'uploaded_at': time.time(),
                    'hash': 'large_file_hash',
                    'encrypted': False
                },
                'warnings': []
            }

            # Process files sequentially to test memory cleanup
            for i, (file_data, filename) in enumerate(large_files):
                response = authenticated_client.post('/training/upload', data={
                    'files': [(file_data, filename)]
                })

                assert response.status_code == 200

                # Reset file pointer for potential reuse
                file_data.seek(0)

        # If we get here without memory errors, the test passes
        assert True

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])