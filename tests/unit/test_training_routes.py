"""
Unit tests for Training Routes

Tests the Flask routes and endpoints for the training functionality.
"""

import json
from pathlib import Path
import pytest
import tempfile
from unittest.mock import Mock, patch

from tests.conftest import create_test_user
from webapp.routes.training_routes import training_bp

class TestTrainingRoutes:
    """Test cases for training routes"""

    @pytest.fixture
    def client(self, app):
        """Create a test client"""
        # Blueprint is already registered in app_factory, no need to register again
        return app.test_client()

    @pytest.fixture
    def test_user(self, db_session):
        """Create a test user"""
        return create_test_user()

    @pytest.fixture
    def authenticated_client(self, client, test_user):
        """Create an authenticated test client"""
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)
            sess['_fresh'] = True
        return client

    def test_dashboard_route_authenticated(self, authenticated_client):
        """Test training dashboard route with authentication"""
        response = authenticated_client.get('/training/')

        assert response.status_code == 200
        assert b'LLM Training Dashboard' in response.data

    def test_dashboard_route_unauthenticated(self, client):
        """Test training dashboard route without authentication"""
        response = client.get('/training/')

        # Should redirect to login
        assert response.status_code == 302

    def test_upload_files_success(self, authenticated_client):
        """Test successful file upload"""
        # Create a test file
        test_file_content = b'%PDF-1.4 test content'

        data = {
            'files': (tempfile.NamedTemporaryFile(suffix='.pdf', delete=False), 'test.pdf')
        }

        with patch('webapp.routes.training_routes.allowed_file', return_value=True):
            with patch('pathlib.Path.mkdir'):
                with patch('werkzeug.datastructures.FileStorage.save'):
                    response = authenticated_client.post('/training/upload',
                                                       data=data,
                                                       content_type='multipart/form-data')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'files' in response_data

    def test_upload_files_no_files(self, authenticated_client):
        """Test file upload with no files"""
        response = authenticated_client.post('/training/upload',
                                           data={},
                                           content_type='multipart/form-data')

        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data

    def test_upload_files_invalid_type(self, authenticated_client):
        """Test file upload with invalid file type"""
        data = {
            'files': (tempfile.NamedTemporaryFile(suffix='.exe', delete=False), 'test.exe')
        }

        response = authenticated_client.post('/training/upload',
                                           data=data,
                                           content_type='multipart/form-data')

        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data

    def test_create_session_success(self, authenticated_client):
        """Test successful training session creation"""
        session_data = {
            'sessionName': 'Test Training Session',
            'confidenceThreshold': 0.7,
            'maxQuestions': 10,
            'useInMainApp': False,
            'files': [
                {
                    'filename': 'test_file_123.pdf',
                    'original_name': 'test.pdf',
                    'size': 1024,
                    'category': 'qa',
                    'extension': '.pdf'
                }
            ]
        }

        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 1024

                response = authenticated_client.post('/training/create-session',
                                                   data=json.dumps(session_data),
                                                   content_type='application/json')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'session_id' in response_data

    def test_create_session_missing_name(self, authenticated_client):
        """Test session creation with missing name"""
        session_data = {
            'confidenceThreshold': 0.7,
            'files': []
        }

        response = authenticated_client.post('/training/create-session',
                                           data=json.dumps(session_data),
                                           content_type='application/json')

        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data

    def test_create_session_invalid_confidence(self, authenticated_client):
        """Test session creation with invalid confidence threshold"""
        session_data = {
            'sessionName': 'Test Session',
            'confidenceThreshold': 1.5,  # Invalid
            'files': [{'filename': 'test.pdf'}]
        }

        response = authenticated_client.post('/training/create-session',
                                           data=json.dumps(session_data),
                                           content_type='application/json')

        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data

    def test_start_training_success(self, authenticated_client, test_user):
        """Test successful training start"""
        training_data = {
            'session_id': f'session_{test_user.id}_123456',
            'priority': 'normal'
        }

        response = authenticated_client.post('/training/start-training',
                                           data=json.dumps(training_data),
                                           content_type='application/json')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True

    def test_start_training_missing_session_id(self, authenticated_client):
        """Test training start with missing session ID"""
        training_data = {
            'priority': 'normal'
        }

        response = authenticated_client.post('/training/start-training',
                                           data=json.dumps(training_data),
                                           content_type='application/json')

        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data

    def test_start_training_access_denied(self, authenticated_client):
        """Test training start with access denied"""
        training_data = {
            'session_id': 'session_999_123456',  # Different user
            'priority': 'normal'
        }

        response = authenticated_client.post('/training/start-training',
                                           data=json.dumps(training_data),
                                           content_type='application/json')

        assert response.status_code == 403
        response_data = json.loads(response.data)
        assert 'error' in response_data

    def test_pause_session(self, authenticated_client, test_user):
        """Test pausing a training session"""
        session_id = f'session_{test_user.id}_123456'

        response = authenticated_client.post(f'/training/session/{session_id}/pause')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True

    def test_resume_session(self, authenticated_client, test_user):
        """Test resuming a training session"""
        session_id = f'session_{test_user.id}_123456'
        resume_data = {'priority': 'high'}

        response = authenticated_client.post(f'/training/session/{session_id}/resume',
                                           data=json.dumps(resume_data),
                                           content_type='application/json')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True

    def test_stop_session(self, authenticated_client, test_user):
        """Test stopping a training session"""
        session_id = f'session_{test_user.id}_123456'
        stop_data = {'save_partial_results': True, 'reason': 'user_requested'}

        response = authenticated_client.post(f'/training/session/{session_id}/stop',
                                           data=json.dumps(stop_data),
                                           content_type='application/json')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True

    def test_get_progress(self, authenticated_client, test_user):
        """Test getting training progress"""
        session_id = f'session_{test_user.id}_123456'

        response = authenticated_client.get(f'/training/progress/{session_id}')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert 'percentage' in response_data
        assert 'current_step' in response_data

    def test_list_sessions(self, authenticated_client):
        """Test listing training sessions"""
        response = authenticated_client.get('/training/sessions')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'sessions' in response_data

    def test_manage_sessions_page(self, authenticated_client):
        """Test sessions management page"""
        response = authenticated_client.get('/training/sessions/manage')

        assert response.status_code == 200
        assert b'Training Sessions' in response.data

    def test_get_session_details(self, authenticated_client, test_user):
        """Test getting session details"""
        session_id = f'session_{test_user.id}_123456'

        response = authenticated_client.get(f'/training/session/{session_id}')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'session' in response_data

    def test_get_report_page(self, authenticated_client, test_user):
        """Test getting training report page"""
        session_id = f'session_{test_user.id}_123456'

        response = authenticated_client.get(f'/training/session/{session_id}/report')

        assert response.status_code == 200
        assert b'Training Report' in response.data

    def test_download_report(self, authenticated_client, test_user):
        """Test downloading training report"""
        session_id = f'session_{test_user.id}_123456'

        response = authenticated_client.get(f'/training/session/{session_id}/report/download')

        assert response.status_code == 200
        assert response.content_type == 'application/pdf'

    def test_get_markdown_report(self, authenticated_client, test_user):
        """Test getting markdown report"""
        session_id = f'session_{test_user.id}_123456'

        response = authenticated_client.get(f'/training/session/{session_id}/report/markdown')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'markdown' in response_data

    def test_get_report_chart(self, authenticated_client, test_user):
        """Test getting report chart data"""
        session_id = f'session_{test_user.id}_123456'
        chart_type = 'confidence'

        response = authenticated_client.get(f'/training/session/{session_id}/report/charts/{chart_type}')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'chart_config' in response_data

    def test_get_invalid_chart_type(self, authenticated_client, test_user):
        """Test getting invalid chart type"""
        session_id = f'session_{test_user.id}_123456'
        chart_type = 'invalid_chart'

        response = authenticated_client.get(f'/training/session/{session_id}/report/charts/{chart_type}')

        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data

    def test_export_report(self, authenticated_client, test_user):
        """Test exporting training report"""
        session_id = f'session_{test_user.id}_123456'
        export_data = {
            'format': 'pdf',
            'include_charts': True,
            'include_raw_data': False
        }

        response = authenticated_client.post(f'/training/session/{session_id}/report/export',
                                           data=json.dumps(export_data),
                                           content_type='application/json')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'export_id' in response_data

    def test_share_report(self, authenticated_client, test_user):
        """Test sharing training report"""
        session_id = f'session_{test_user.id}_123456'
        share_data = {
            'expires_in_hours': 24,
            'password_protected': False,
            'allow_download': True
        }

        response = authenticated_client.post(f'/training/session/{session_id}/report/share',
                                           data=json.dumps(share_data),
                                           content_type='application/json')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'share_url' in response_data

    def test_upload_test_submission(self, authenticated_client, test_user):
        """Test uploading test submission"""
        session_id = f'session_{test_user.id}_123456'

        data = {
            'file': (tempfile.NamedTemporaryFile(suffix='.pdf', delete=False), 'test_submission.pdf')
        }

        with patch('webapp.routes.training_routes.allowed_file', return_value=True):
            with patch('pathlib.Path.mkdir'):
                with patch('werkzeug.datastructures.FileStorage.save'):
                    response = authenticated_client.post(f'/training/session/{session_id}/test/upload',
                                                       data=data,
                                                       content_type='multipart/form-data')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'test_submission' in response_data

    def test_run_model_test(self, authenticated_client, test_user):
        """Test running model test"""
        session_id = f'session_{test_user.id}_123456'
        test_data = {
            'test_submission_ids': ['test_1', 'test_2'],
            'compare_with_baseline': False,
            'generate_detailed_report': True
        }

        response = authenticated_client.post(f'/training/session/{session_id}/test/run',
                                           data=json.dumps(test_data),
                                           content_type='application/json')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'test_run_id' in response_data

    def test_get_test_progress(self, authenticated_client, test_user):
        """Test getting test progress"""
        session_id = f'session_{test_user.id}_123456'
        test_run_id = 'test_run_123'

        response = authenticated_client.get(f'/training/session/{session_id}/test/{test_run_id}/progress')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'progress' in response_data

    def test_get_test_results(self, authenticated_client, test_user):
        """Test getting test results"""
        session_id = f'session_{test_user.id}_123456'
        test_run_id = 'test_run_123'

        response = authenticated_client.get(f'/training/session/{session_id}/test/{test_run_id}/results')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'results' in response_data

    def test_session_config_get(self, authenticated_client, test_user):
        """Test getting session configuration"""
        session_id = f'session_{test_user.id}_123456'

        response = authenticated_client.get(f'/training/session/{session_id}/config')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'config' in response_data

    def test_session_config_update(self, authenticated_client, test_user):
        """Test updating session configuration"""
        session_id = f'session_{test_user.id}_123456'
        config_data = {
            'name': 'Updated Session Name',
            'confidence_threshold': 0.8,
            'max_questions': 20
        }

        response = authenticated_client.put(f'/training/session/{session_id}/config',
                                          data=json.dumps(config_data),
                                          content_type='application/json')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True

    def test_delete_session(self, authenticated_client, test_user):
        """Test deleting a training session"""
        session_id = f'session_{test_user.id}_123456'

        response = authenticated_client.delete(f'/training/session/{session_id}')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True

    def test_remove_uploaded_file(self, authenticated_client, test_user):
        """Test removing an uploaded file"""
        remove_data = {
            'filename': f'test_file_{test_user.id}_123.pdf'
        }

        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.unlink'):
                response = authenticated_client.post('/training/upload/remove',
                                                   data=json.dumps(remove_data),
                                                   content_type='application/json')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True

    def test_validate_uploaded_files(self, authenticated_client, test_user):
        """Test validating uploaded files"""
        validate_data = {
            'filenames': [f'test_file_{test_user.id}_123.pdf']
        }

        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 1024

                response = authenticated_client.post('/training/upload/validate',
                                                   data=json.dumps(validate_data),
                                                   content_type='application/json')

        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'validation_results' in response_data