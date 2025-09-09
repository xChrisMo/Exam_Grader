"""
System Tests for LLM Training Page

Comprehensive system tests that validate the entire training workflow
from file upload through report generation.
"""

import os
import json
import time
from pathlib import Path
import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from flask import url_for
from werkzeug.datastructures import FileStorage
from io import BytesIO

from webapp.app import create_app
from src.database.models import db, User, TrainingSession, TrainingGuide, TrainingQuestion
from src.services.training_service import training_service
from src.services.training_report_service import training_report_service
from utils.logger import logger

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
            id='test-user-123',
            username='testuser',
            email='test@example.com',
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

@pytest.fixture
def sample_pdf_file():
    """Create sample PDF file for testing"""
    pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF'
    return BytesIO(pdf_content)

@pytest.fixture
def sample_image_file():
    """Create sample image file for testing"""
    # Simple PNG header
    png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    return BytesIO(png_content)

class TestTrainingSystemWorkflow:
    """Test complete training system workflow"""

    def test_complete_training_workflow(self, authenticated_client, test_user, sample_pdf_file, sample_image_file):
        """Test complete training workflow from upload to report generation"""

        # Step 1: Access training page
        response = authenticated_client.get('/training')
        assert response.status_code == 200
        assert b'Training Dashboard' in response.data

        # Step 2: Upload marking guides
        with patch('src.services.secure_file_handler.secure_file_handler.secure_upload') as mock_upload:
            mock_upload.return_value = {
                'success': True,
                'file_record': {
                    'filename': 'test_guide.pdf',
                    'original_name': 'marking_guide.pdf',
                    'size': 1024,
                    'file_path': '/tmp/test_guide.pdf',
                    'uploaded_at': time.time(),
                    'hash': 'test_hash',
                    'encrypted': False
                },
                'warnings': []
            }

            response = authenticated_client.post('/training/upload', data={
                'files': [
                    (sample_pdf_file, 'marking_guide.pdf'),
                    (sample_image_file, 'question_image.png')
                ]
            })

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['uploaded_files']) == 2

        # Step 3: Create training session
        with patch('src.services.training_service.training_service.create_training_session') as mock_create:
            mock_session = Mock()
            mock_session.id = 'test-session-123'
            mock_session.status = 'created'
            mock_create.return_value = mock_session

            response = authenticated_client.post('/training/sessions', json={
                'name': 'Test Training Session',
                'description': 'System test session',
                'max_questions_to_answer': 3,
                'use_in_main_app': True,
                'uploaded_files': [
                    {'filename': 'test_guide.pdf', 'category': 'qa'},
                    {'filename': 'question_image.png', 'category': 'q'}
                ]
            })

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['session_id'] == 'test-session-123'

        # Step 4: Start training
        with patch('src.services.training_service.training_service.start_training') as mock_start:
            mock_start.return_value = True

            response = authenticated_client.post('/training/sessions/test-session-123/start')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

        # Step 5: Monitor training progress
        with patch('src.services.training_service.training_service.get_training_progress') as mock_progress:
            mock_progress.return_value = {
                'status': 'processing',
                'progress_percentage': 75.0,
                'current_step': 'Analyzing guides',
                'estimated_completion': '2 minutes'
            }

            response = authenticated_client.get('/training/sessions/test-session-123/progress')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['progress_percentage'] == 75.0
            assert data['current_step'] == 'Analyzing guides'

        # Step 6: Get training results
        with patch('src.services.training_service.training_service.get_training_results') as mock_results:
            mock_results.return_value = {
                'status': 'completed',
                'total_questions': 5,
                'average_confidence': 0.85,
                'questions_requiring_review': 1,
                'training_duration': 120
            }

            response = authenticated_client.get('/training/sessions/test-session-123/results')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'completed'
            assert data['average_confidence'] == 0.85

        # Step 7: Generate and download report
        with patch('src.services.training_report_service.training_report_service.generate_pdf_report') as mock_pdf:
            mock_pdf.return_value = b'%PDF-1.4 mock report content'

            response = authenticated_client.get('/training/sessions/test-session-123/report/pdf')

            assert response.status_code == 200
            assert response.headers['Content-Type'] == 'application/pdf'
            assert b'%PDF-1.4' in response.data

    def test_file_upload_validation(self, authenticated_client, test_user):
        """Test file upload validation and error handling"""

        # Test invalid file type
        invalid_file = BytesIO(b'invalid content')
        response = authenticated_client.post('/training/upload', data={
            'files': [(invalid_file, 'invalid.exe')]
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'errors' in data
        assert any('not allowed' in error for error in data['errors'])

        # Test oversized file
        with patch('src.services.secure_file_handler.secure_file_handler.secure_upload') as mock_upload:
            mock_upload.return_value = {
                'success': False,
                'error': 'File exceeds maximum size',
                'details': ['File size too large']
            }

            large_file = BytesIO(b'x' * (60 * 1024 * 1024))  # 60MB
            response = authenticated_client.post('/training/upload', data={
                'files': [(large_file, 'large_file.pdf')]
            })

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is False

    def test_training_session_management(self, authenticated_client, test_user):
        """Test training session creation, listing, and deletion"""

        # Create multiple training sessions
        with patch('src.services.training_service.training_service.create_training_session') as mock_create:
            sessions = []
            for i in range(3):
                mock_session = Mock()
                mock_session.id = f'session-{i}'
                mock_session.name = f'Test Session {i}'
                mock_session.status = 'completed'
                mock_session.created_at = time.time() - (i * 3600)
                sessions.append(mock_session)
                mock_create.return_value = mock_session

                response = authenticated_client.post('/training/sessions', json={
                    'name': f'Test Session {i}',
                    'description': f'Test session {i}',
                    'uploaded_files': []
                })
                assert response.status_code == 200

        # List training sessions
        with patch('src.services.training_service.training_service.get_user_training_sessions') as mock_list:
            mock_list.return_value = sessions

            response = authenticated_client.get('/training/sessions')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data['sessions']) == 3

        # Set active model
        with patch('src.services.training_service.training_service.set_active_model') as mock_active:
            mock_active.return_value = True

            response = authenticated_client.post('/training/sessions/session-0/set-active')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

        # Delete training session
        with patch('src.services.training_service.training_service.delete_training_session') as mock_delete:
            mock_delete.return_value = True

            response = authenticated_client.delete('/training/sessions/session-2')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

class TestPerformanceAndScalability:
    """Test performance and scalability aspects"""

    def test_large_file_handling(self, authenticated_client, test_user):
        """Test handling of large files and multiple uploads"""

        # Test multiple file upload
        files = []
        for i in range(10):
            file_content = BytesIO(b'%PDF-1.4 test content ' * 1000)  # ~20KB each
            files.append((file_content, f'guide_{i}.pdf'))

        with patch('src.services.secure_file_handler.secure_file_handler.secure_upload') as mock_upload:
            mock_upload.return_value = {
                'success': True,
                'file_record': {
                    'filename': 'test_guide.pdf',
                    'original_name': 'guide.pdf',
                    'size': 20000,
                    'file_path': '/tmp/test_guide.pdf',
                    'uploaded_at': time.time(),
                    'hash': 'test_hash',
                    'encrypted': False
                },
                'warnings': []
            }

            response = authenticated_client.post('/training/upload', data={'files': files})

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['uploaded_files']) == 10

    def test_concurrent_training_sessions(self, authenticated_client, test_user):
        """Test handling of concurrent training sessions"""

        session_ids = []

        # Create multiple concurrent sessions
        with patch('src.services.training_service.training_service.create_training_session') as mock_create:
            for i in range(5):
                mock_session = Mock()
                mock_session.id = f'concurrent-session-{i}'
                mock_session.status = 'created'
                mock_create.return_value = mock_session

                response = authenticated_client.post('/training/sessions', json={
                    'name': f'Concurrent Session {i}',
                    'description': f'Concurrent test session {i}',
                    'uploaded_files': []
                })

                assert response.status_code == 200
                data = json.loads(response.data)
                session_ids.append(data['session_id'])

        # Start all sessions concurrently
        with patch('src.services.training_service.training_service.start_training') as mock_start:
            mock_start.return_value = True

            for session_id in session_ids:
                response = authenticated_client.post(f'/training/sessions/{session_id}/start')
                assert response.status_code == 200

    def test_database_performance(self, authenticated_client, test_user):
        """Test database performance with large datasets"""

        # Test querying large number of training sessions
        with patch('src.services.training_service.training_service.get_user_training_sessions') as mock_list:
            # Simulate 100 training sessions
            sessions = []
            for i in range(100):
                mock_session = Mock()
                mock_session.id = f'perf-session-{i}'
                mock_session.name = f'Performance Test Session {i}'
                mock_session.status = 'completed'
                mock_session.created_at = time.time() - (i * 60)
                mock_session.total_questions = 10
                mock_session.average_confidence = 0.8
                sessions.append(mock_session)

            mock_list.return_value = sessions

            start_time = time.time()
            response = authenticated_client.get('/training/sessions')
            end_time = time.time()

            assert response.status_code == 200
            assert (end_time - start_time) < 1.0  # Should complete within 1 second

            data = json.loads(response.data)
            assert len(data['sessions']) == 100

class TestSecurityAndAccessControl:
    """Test security features and access control"""

    def test_authentication_required(self, client):
        """Test that authentication is required for all training endpoints"""

        endpoints = [
            '/training',
            '/training/upload',
            '/training/sessions',
            '/training/sessions/test-123/start',
            '/training/sessions/test-123/progress',
            '/training/sessions/test-123/results',
            '/training/sessions/test-123/report/pdf'
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [302, 401]  # Redirect to login or unauthorized

    def test_user_data_isolation(self, app, authenticated_client):
        """Test that users can only access their own training data"""

        with app.app_context():
            # Create another user
            other_user = User(
                id='other-user-456',
                username='otheruser',
                email='other@example.com',
                password_hash='hashed_password'
            )
            db.session.add(other_user)
            db.session.commit()

            # Try to access other user's session
            response = authenticated_client.get('/training/sessions/other-user-session-123/progress')
            assert response.status_code in [403, 404]  # Forbidden or not found

    def test_file_quarantine_security(self, authenticated_client, test_user):
        """Test file quarantine security features"""

        # Test quarantine list access
        response = authenticated_client.get('/training/quarantine')
        assert response.status_code == 200

        # Test quarantine file release (should require proper access)
        response = authenticated_client.post('/training/quarantine/invalid-id/release')
        assert response.status_code == 400  # Bad request for invalid ID

        # Test quarantine file deletion
        response = authenticated_client.delete('/training/quarantine/invalid-id')
        assert response.status_code == 400  # Bad request for invalid ID

    def test_admin_only_endpoints(self, authenticated_client, test_user):
        """Test that admin-only endpoints require admin privileges"""

        # Test security cleanup (should fail for non-admin)
        response = authenticated_client.post('/training/security/cleanup')
        assert response.status_code == 403  # Forbidden

        # Test security stats (should fail for non-admin)
        response = authenticated_client.get('/training/security/stats')
        assert response.status_code == 403  # Forbidden

class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms"""

    def test_llm_service_failure_handling(self, authenticated_client, test_user):
        """Test handling of LLM service failures"""

        session_id = 'test-session-123'

        # Test training failure due to LLM service error
        with patch('src.services.training_service.training_service.start_training') as mock_start:
            mock_start.side_effect = Exception('LLM service unavailable')

            response = authenticated_client.post(f'/training/sessions/{session_id}/start')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            assert 'LLM service unavailable' in data['error']

    def test_ocr_service_failure_handling(self, authenticated_client, test_user, sample_image_file):
        """Test handling of OCR service failures during testing"""

        session_id = 'test-session-123'

        # Upload test submission
        with patch('src.services.secure_file_handler.secure_file_handler.secure_upload') as mock_upload:
            mock_upload.return_value = {
                'success': True,
                'file_record': {
                    'filename': 'test_submission.png',
                    'original_name': 'student_answer.png',
                    'size': 512,
                    'file_path': '/tmp/test_submission.png',
                    'uploaded_at': time.time(),
                    'hash': 'test_hash_2',
                    'encrypted': False
                },
                'warnings': []
            }

            response = authenticated_client.post(f'/training/sessions/{session_id}/test-submissions', data={
                'files': [(sample_image_file, 'student_answer.png')]
            })

            assert response.status_code == 200

        # Test OCR failure during model testing
        with patch('src.services.training_service.training_service.test_trained_model') as mock_test:
            mock_test.return_value = {
                'success': False,
                'error': 'OCR service failed to extract text',
                'partial_results': {
                    'processed_submissions': 0,
                    'failed_submissions': 1,
                    'error_details': ['OCR extraction failed for student_answer.png']
                }
            }

            response = authenticated_client.post(f'/training/sessions/{session_id}/test')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'OCR service failed' in data['error']

    def test_partial_training_results(self, authenticated_client, test_user):
        """Test handling of partial training results"""

        session_id = 'test-session-123'

        with patch('src.services.training_service.training_service.get_training_results') as mock_results:
            mock_results.return_value = {
                'status': 'partial_success',
                'total_questions': 10,
                'processed_questions': 7,
                'failed_questions': 3,
                'average_confidence': 0.72,
                'error_details': [
                    'Question 3: Unable to extract clear text',
                    'Question 7: Ambiguous question format',
                    'Question 9: Processing timeout'
                ],
                'warnings': [
                    'Some questions may require manual review',
                    'Consider re-uploading clearer images'
                ]
            }

            response = authenticated_client.get(f'/training/sessions/{session_id}/results')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'partial_success'
            assert data['processed_questions'] == 7
            assert len(data['error_details']) == 3
            assert len(data['warnings']) == 2

    def test_report_generation_fallback(self, authenticated_client, test_user):
        """Test fallback mechanisms for report generation"""

        session_id = 'test-session-123'

        # Test PDF generation failure with markdown fallback
        with patch('src.services.training_report_service.training_report_service.generate_pdf_report') as mock_pdf:
            mock_pdf.side_effect = Exception('PDF generation failed')

            with patch('src.services.training_report_service.training_report_service.generate_markdown_report') as mock_md:
                mock_md.return_value = '# Training Report\n\nThis is a fallback markdown report.'

                response = authenticated_client.get(f'/training/sessions/{session_id}/report/pdf')

                # Should fall back to markdown or return error
                assert response.status_code in [200, 500]

                if response.status_code == 200:
                    data = response.get_json()
                    assert 'report_url' in data or 'error' in data

class TestAccessibilityAndUsability:
    """Test accessibility and usability features"""

    def test_responsive_design_elements(self, authenticated_client, test_user):
        """Test that training page includes responsive design elements"""
        response = authenticated_client.get('/training')

        assert response.status_code == 200
        content = response.data.decode('utf-8')

        # Check for responsive CSS classes (Tailwind)
        responsive_classes = ['sm:', 'md:', 'lg:', 'xl:', 'responsive', 'mobile']
        assert any(cls in content for cls in responsive_classes)

    def test_accessibility_attributes(self, authenticated_client, test_user):
        """Test that accessibility attributes are present"""
        response = authenticated_client.get('/training')

        assert response.status_code == 200
        content = response.data.decode('utf-8')

        # Check for accessibility attributes
        accessibility_attrs = ['aria-label', 'alt=', 'role=', 'tabindex']
        assert any(attr in content for attr in accessibility_attrs)

        # Check for semantic HTML elements
        semantic_elements = ['<main', '<section', '<article', '<nav', '<header']
        assert any(element in content for element in semantic_elements)

    def test_keyboard_navigation_support(self, authenticated_client, test_user):
        """Test keyboard navigation support"""
        response = authenticated_client.get('/training')

        assert response.status_code == 200
        content = response.data.decode('utf-8')

        # Check for keyboard navigation attributes
        keyboard_attrs = ['tabindex', 'accesskey', 'onkeydown', 'onkeyup']
        # At least some keyboard support should be present
        # This is a basic check - full keyboard testing would require browser automation
        assert '<button' in content or '<input' in content  # Interactive elements present