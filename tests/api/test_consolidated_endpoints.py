"""Tests for consolidated API endpoints."""

import json
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from flask_login import login_user

from src.api.consolidated_endpoints import init_consolidated_services
from src.database.models import db, User, MarkingGuide, Submission, GradingResult
from tests.conftest import create_test_app


class TestConsolidatedEndpoints(unittest.TestCase):
    """Test cases for consolidated API endpoints."""

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
        
        # Create test marking guide
        self.test_guide = MarkingGuide(
            name='Test Guide',
            subject='Mathematics',
            total_marks=100,
            content='Test marking guide content',
            user_id=self.test_user.id,
            is_active=True
        )
        db.session.add(self.test_guide)
        db.session.commit()
        
        # Create test submissions
        self.test_submission1 = Submission(
            student_name='John Doe',
            student_id='12345',
            file_path='/test/path1.pdf',
            content='Test submission content 1',
            marking_guide_id=self.test_guide.id,
            processing_status='completed'
        )
        
        self.test_submission2 = Submission(
            student_name='Jane Smith',
            student_id='67890',
            file_path='/test/path2.pdf',
            content='Test submission content 2',
            marking_guide_id=self.test_guide.id,
            processing_status='processing'
        )
        
        db.session.add_all([self.test_submission1, self.test_submission2])
        db.session.commit()
        
        # Create test grading result
        self.test_result = GradingResult(
            submission_id=self.test_submission1.id,
            total_score=85.5,
            letter_grade='B+',
            feedback='Good work overall',
            detailed_scores={'q1': 20, 'q2': 18, 'q3': 22, 'q4': 25.5}
        )
        db.session.add(self.test_result)
        db.session.commit()
        
        # Initialize services with mocks
        with patch('src.api.consolidated_endpoints.ConsolidatedOCRService'), \
             patch('src.api.consolidated_endpoints.UnifiedAIService'), \
             patch('src.api.consolidated_endpoints.EnhancedUploadService'):
            init_consolidated_services(self.app)
        
        self.client = self.app.test_client()
        
        # Set up authenticated session
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user.id
            sess['_fresh'] = True

    def tearDown(self):
        """Clean up test fixtures."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login_user(self):
        """Helper method to log in test user."""
        with self.app.test_request_context():
            login_user(self.test_user)

    def test_get_marking_guides(self):
        """Test getting marking guides."""
        with patch('flask_login.current_user', self.test_user):
            response = self.client.get('/api/v1/guides')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
        self.assertIn('pagination', data)
        
        # Check guide data
        guides = data['data']
        self.assertEqual(len(guides), 1)
        
        guide = guides[0]
        self.assertEqual(guide['id'], self.test_guide.id)
        self.assertEqual(guide['name'], 'Test Guide')
        self.assertEqual(guide['subject'], 'Mathematics')
        self.assertEqual(guide['total_marks'], 100)
        self.assertEqual(guide['submission_count'], 2)

    def test_get_marking_guides_with_search(self):
        """Test getting marking guides with search filter."""
        with patch('flask_login.current_user', self.test_user):
            response = self.client.get('/api/v1/guides?search=Test')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        guides = data['data']
        self.assertEqual(len(guides), 1)
        
        # Test search that should return no results
        with patch('flask_login.current_user', self.test_user):
            response = self.client.get('/api/v1/guides?search=NonExistent')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['data']), 0)

    def test_get_marking_guides_with_pagination(self):
        """Test getting marking guides with pagination."""
        with patch('flask_login.current_user', self.test_user):
            response = self.client.get('/api/v1/guides?page=1&per_page=10')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('pagination', data)
        
        pagination = data['pagination']
        self.assertEqual(pagination['page'], 1)
        self.assertEqual(pagination['per_page'], 10)
        self.assertEqual(pagination['total'], 1)
        self.assertEqual(pagination['pages'], 1)

    def test_get_marking_guide_by_id(self):
        """Test getting a specific marking guide."""
        with patch('flask_login.current_user', self.test_user):
            response = self.client.get(f'/api/v1/guides/{self.test_guide.id}')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        guide = data['data']
        self.assertEqual(guide['id'], self.test_guide.id)
        self.assertEqual(guide['name'], 'Test Guide')
        self.assertEqual(guide['content'], 'Test marking guide content')
        
        # Check statistics
        self.assertIn('statistics', guide)
        stats = guide['statistics']
        self.assertEqual(stats['total_submissions'], 2)
        self.assertEqual(stats['completed_submissions'], 1)
        self.assertEqual(stats['processing_submissions'], 1)

    def test_get_marking_guide_not_found(self):
        """Test getting a non-existent marking guide."""
        with patch('flask_login.current_user', self.test_user):
            response = self.client.get('/api/v1/guides/99999')
        
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Marking guide not found', data['message'])

    def test_create_marking_guide(self):
        """Test creating a new marking guide."""
        guide_data = {
            'name': 'New Test Guide',
            'subject': 'Physics',
            'total_marks': 150,
            'content': 'New guide content'
        }
        
        with patch('flask_login.current_user', self.test_user):
            response = self.client.post(
                '/api/v1/guides',
                data=json.dumps(guide_data),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        guide = data['data']
        self.assertEqual(guide['name'], 'New Test Guide')
        self.assertEqual(guide['subject'], 'Physics')
        self.assertEqual(guide['total_marks'], 150)
        
        # Verify guide was created in database
        created_guide = MarkingGuide.query.filter_by(name='New Test Guide').first()
        self.assertIsNotNone(created_guide)
        self.assertEqual(created_guide.user_id, self.test_user.id)

    def test_create_marking_guide_validation_errors(self):
        """Test creating marking guide with validation errors."""
        # Test missing required fields
        with patch('flask_login.current_user', self.test_user):
            response = self.client.post(
                '/api/v1/guides',
                data=json.dumps({'name': 'Test'}),  # Missing subject
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Validation failed', data['message'])
        
        # Test name too short
        with patch('flask_login.current_user', self.test_user):
            response = self.client.post(
                '/api/v1/guides',
                data=json.dumps({'name': 'AB', 'subject': 'Math'}),  # Name too short
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 400)
        
        # Test duplicate name
        with patch('flask_login.current_user', self.test_user):
            response = self.client.post(
                '/api/v1/guides',
                data=json.dumps({'name': 'Test Guide', 'subject': 'Math'}),  # Duplicate name
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('already exists', data['message'])

    def test_get_submissions(self):
        """Test getting submissions."""
        with patch('flask_login.current_user', self.test_user):
            response = self.client.get('/api/v1/submissions')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        submissions = data['data']
        self.assertEqual(len(submissions), 2)
        
        # Check submission data
        submission = submissions[0]  # Should be ordered by created_at desc
        self.assertIn('id', submission)
        self.assertIn('student_name', submission)
        self.assertIn('processing_status', submission)
        self.assertIn('marking_guide', submission)
        
        # Check marking guide data
        guide_data = submission['marking_guide']
        self.assertEqual(guide_data['id'], self.test_guide.id)
        self.assertEqual(guide_data['name'], 'Test Guide')

    def test_get_submissions_with_filters(self):
        """Test getting submissions with filters."""
        # Test guide filter
        with patch('flask_login.current_user', self.test_user):
            response = self.client.get(f'/api/v1/submissions?guide_id={self.test_guide.id}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['data']), 2)
        
        # Test status filter
        with patch('flask_login.current_user', self.test_user):
            response = self.client.get('/api/v1/submissions?status=completed')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['data']), 1)
        
        # Test search filter
        with patch('flask_login.current_user', self.test_user):
            response = self.client.get('/api/v1/submissions?search=John')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['student_name'], 'John Doe')

    def test_process_batch(self):
        """Test batch processing endpoint."""
        batch_data = {
            'guide_id': self.test_guide.id,
            'submission_ids': [self.test_submission1.id, self.test_submission2.id],
            'options': {'priority': 'high'}
        }
        
        with patch('flask_login.current_user', self.test_user):
            response = self.client.post(
                '/api/v1/processing/batch',
                data=json.dumps(batch_data),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 202)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        task_data = data['data']
        self.assertIn('task_id', task_data)
        self.assertEqual(task_data['status'], 'started')
        self.assertEqual(task_data['guide_id'], self.test_guide.id)
        self.assertEqual(task_data['submission_count'], 2)

    def test_process_batch_validation_errors(self):
        """Test batch processing with validation errors."""
        # Test missing required fields
        with patch('flask_login.current_user', self.test_user):
            response = self.client.post(
                '/api/v1/processing/batch',
                data=json.dumps({'guide_id': self.test_guide.id}),  # Missing submission_ids
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 400)
        
        # Test non-existent guide
        batch_data = {
            'guide_id': 99999,
            'submission_ids': [self.test_submission1.id]
        }
        
        with patch('flask_login.current_user', self.test_user):
            response = self.client.post(
                '/api/v1/processing/batch',
                data=json.dumps(batch_data),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 404)
        
        # Test non-existent submissions
        batch_data = {
            'guide_id': self.test_guide.id,
            'submission_ids': [99999]
        }
        
        with patch('flask_login.current_user', self.test_user):
            response = self.client.post(
                '/api/v1/processing/batch',
                data=json.dumps(batch_data),
                content_type='application/json'
            )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('not found or not accessible', data['message'])

    def test_get_processing_status(self):
        """Test getting processing status."""
        task_id = 'batch_20231201_120000_1'
        
        with patch('flask_login.current_user', self.test_user):
            response = self.client.get(f'/api/v1/processing/status/{task_id}')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        status_data = data['data']
        self.assertEqual(status_data['task_id'], task_id)
        self.assertIn('status', status_data)
        self.assertIn('progress', status_data)
        self.assertIn('results', status_data)

    def test_get_processing_status_invalid_task_id(self):
        """Test getting processing status with invalid task ID."""
        with patch('flask_login.current_user', self.test_user):
            response = self.client.get('/api/v1/processing/status/invalid')
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Invalid task ID', data['message'])

    def test_unauthorized_access(self):
        """Test unauthorized access to endpoints."""
        # Test without authentication
        response = self.client.get('/api/v1/guides')
        self.assertEqual(response.status_code, 401)
        
        response = self.client.post(
            '/api/v1/guides',
            data=json.dumps({'name': 'Test', 'subject': 'Math'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)

    def test_error_handling(self):
        """Test error handling in endpoints."""
        # Test database error simulation
        with patch('flask_login.current_user', self.test_user), \
             patch('src.api.consolidated_endpoints.MarkingGuide.query') as mock_query:
            
            mock_query.filter_by.side_effect = Exception('Database error')
            
            response = self.client.get('/api/v1/guides')
            self.assertEqual(response.status_code, 500)
            
            data = json.loads(response.data)
            self.assertEqual(data['status'], 'error')
            self.assertIn('Failed to fetch marking guides', data['message'])


if __name__ == '__main__':
    unittest.main()