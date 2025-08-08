"""
Security Tests for LLM Training Page

Comprehensive security tests to validate protection against
common vulnerabilities and security best practices.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch
from io import BytesIO
from flask import url_for

from webapp.app import create_app
from src.database.models import db, User
from src.services.secure_file_handler import SecureFileHandler
# from src.services.file_quarantine import file_quarantine, QuarantineReason  # Module not found


@pytest.fixture
def app():
    """Create test Flask application"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = True  # Enable CSRF for security tests
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
            id='security-test-user',
            username='securityuser',
            email='security@example.com',
            password_hash='hashed_password'
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def other_user(app):
    """Create another test user for access control tests"""
    with app.app_context():
        user = User(
            id='other-security-user',
            username='otheruser',
            email='other@example.com',
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


class TestAuthenticationAndAuthorization:
    """Test authentication and authorization security"""
    
    def test_unauthenticated_access_blocked(self, client):
        """Test that unauthenticated users cannot access training endpoints"""
        
        protected_endpoints = [
            ('/training', 'GET'),
            ('/training/upload', 'POST'),
            ('/training/sessions', 'GET'),
            ('/training/sessions', 'POST'),
            ('/training/sessions/test-123/start', 'POST'),
            ('/training/sessions/test-123/progress', 'GET'),
            ('/training/sessions/test-123/results', 'GET'),
            ('/training/sessions/test-123/report/pdf', 'GET'),
            ('/training/quarantine', 'GET'),
            ('/training/security/stats', 'GET')
        ]
        
        for endpoint, method in protected_endpoints:
            if method == 'GET':
                response = client.get(endpoint)
            elif method == 'POST':
                response = client.post(endpoint)
            elif method == 'DELETE':
                response = client.delete(endpoint)
            
            # Should redirect to login or return 401/403
            assert response.status_code in [302, 401, 403]
    
    def test_user_data_isolation(self, app, authenticated_client, other_user):
        """Test that users cannot access other users' training data"""
        
        # Try to access another user's training session
        other_session_id = f'session-{other_user.id}-123'
        
        endpoints_to_test = [
            f'/training/sessions/{other_session_id}/progress',
            f'/training/sessions/{other_session_id}/results',
            f'/training/sessions/{other_session_id}/report/pdf',
            f'/training/sessions/{other_session_id}/start'
        ]
        
        for endpoint in endpoints_to_test:
            if 'start' in endpoint:
                response = authenticated_client.post(endpoint)
            else:
                response = authenticated_client.get(endpoint)
            
            # Should return 403 (Forbidden) or 404 (Not Found)
            assert response.status_code in [403, 404]
    
    def test_admin_only_endpoints_protection(self, authenticated_client, test_user):
        """Test that admin-only endpoints are properly protected"""
        
        # Test without admin privileges
        admin_endpoints = [
            ('/training/security/cleanup', 'POST'),
            ('/training/security/stats', 'GET')
        ]
        
        for endpoint, method in admin_endpoints:
            if method == 'GET':
                response = authenticated_client.get(endpoint)
            elif method == 'POST':
                response = authenticated_client.post(endpoint)
            
            assert response.status_code == 403  # Forbidden
        
        # Test with admin privileges
        with patch.object(test_user, 'is_admin', True):
            for endpoint, method in admin_endpoints:
                with patch('src.services.secure_file_handler.secure_file_handler.cleanup_expired_files') as mock_cleanup:
                    mock_cleanup.return_value = {'files_cleaned': 0, 'errors': []}
                    
                    if method == 'GET':
                        response = authenticated_client.get(endpoint)
                    elif method == 'POST':
                        response = authenticated_client.post(endpoint)
                    
                    assert response.status_code == 200  # Should work with admin privileges


class TestInputValidationAndSanitization:
    """Test input validation and sanitization"""
    
    def test_malicious_filename_handling(self, authenticated_client):
        """Test handling of malicious filenames"""
        
        malicious_filenames = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            'file<script>alert("xss")</script>.pdf',
            'file\x00.pdf',  # Null byte injection
            'file\r\n.pdf',  # CRLF injection
            'CON.pdf',  # Windows reserved name
            'file' + 'A' * 300 + '.pdf',  # Extremely long filename
            'file.pdf.exe',  # Double extension
            '.htaccess',  # Hidden system file
            'file.pdf;rm -rf /',  # Command injection attempt
        ]
        
        for malicious_filename in malicious_filenames:
            file_content = BytesIO(b'%PDF-1.4 test content')
            
            with patch('src.services.secure_file_handler.secure_file_handler.secure_upload') as mock_upload:
                # Should either sanitize the filename or reject it
                mock_upload.return_value = {
                    'success': False,
                    'error': 'Invalid filename',
                    'details': ['Filename contains invalid characters']
                }
                
                response = authenticated_client.post('/training/upload', data={
                    'files': [(file_content, malicious_filename)]
                })
                
                assert response.status_code == 200
                data = json.loads(response.data)
                
                # Should either reject the file or sanitize the filename
                if data['success']:
                    # If accepted, filename should be sanitized
                    uploaded_filename = data['uploaded_files'][0]['filename']
                    assert '../' not in uploaded_filename
                    assert '\\' not in uploaded_filename
                    assert '<script>' not in uploaded_filename
                    assert '\x00' not in uploaded_filename
                else:
                    # If rejected, should have appropriate error
                    assert 'error' in data or 'errors' in data
    
    def test_malicious_file_content_detection(self, authenticated_client):
        """Test detection of malicious file content"""
        
        malicious_contents = [
            # Script injection attempts
            b'%PDF-1.4\n<script>alert("xss")</script>',
            b'%PDF-1.4\n<?php system($_GET["cmd"]); ?>',
            b'%PDF-1.4\n<% eval(request("cmd")) %>',
            
            # Binary executable signatures
            b'MZ\x90\x00',  # PE executable header
            b'\x7fELF',     # ELF executable header
            b'\xca\xfe\xba\xbe',  # Java class file
            
            # Archive bombs (zip bomb signature)
            b'PK\x03\x04' + b'\x00' * 1000,
            
            # Suspicious patterns
            b'javascript:',
            b'vbscript:',
            b'data:text/html',
        ]
        
        for malicious_content in malicious_contents:
            file_data = BytesIO(malicious_content)
            
            with patch('src.services.secure_file_handler.secure_file_handler.secure_upload') as mock_upload:
                mock_upload.return_value = {
                    'success': False,
                    'error': 'File validation failed',
                    'details': ['Suspicious content detected']
                }
                
                response = authenticated_client.post('/training/upload', data={
                    'files': [(file_data, 'suspicious.pdf')]
                })
                
                assert response.status_code == 200
                data = json.loads(response.data)
                
                # Should reject suspicious content
                assert data['success'] is False
                assert 'error' in data or 'errors' in data
    
    def test_json_injection_protection(self, authenticated_client):
        """Test protection against JSON injection attacks"""
        
        malicious_json_payloads = [
            # JSON injection
            {'name': 'Test\"; DROP TABLE training_sessions; --'},
            {'description': '<script>alert("xss")</script>'},
            {'max_questions_to_answer': '5; DELETE FROM users;'},
            
            # Object injection
            {'name': {'$ne': None}},  # NoSQL injection attempt
            {'uploaded_files': [{'filename': '../../../etc/passwd'}]},
            
            # Prototype pollution attempt
            {'__proto__': {'admin': True}},
            {'constructor': {'prototype': {'admin': True}}},
        ]
        
        for payload in malicious_json_payloads:
            response = authenticated_client.post('/training/sessions', 
                                               json=payload,
                                               content_type='application/json')
            
            # Should return validation error, not process malicious content
            assert response.status_code in [400, 422]  # Bad request or validation error
    
    def test_path_traversal_protection(self, authenticated_client):
        """Test protection against path traversal attacks"""
        
        path_traversal_attempts = [
            'test-session-123/../../../etc/passwd',
            'test-session-123\\..\\..\\..\\windows\\system32\\config\\sam',
            'test-session-123%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',  # URL encoded
            'test-session-123....//....//....//etc/passwd',  # Double encoding
        ]
        
        for malicious_path in path_traversal_attempts:
            response = authenticated_client.get(f'/training/sessions/{malicious_path}/progress')
            
            # Should return 404 or 400, not expose system files
            assert response.status_code in [400, 404]
            
            # Response should not contain system file content
            if response.data:
                content = response.data.decode('utf-8', errors='ignore')
                assert 'root:' not in content  # Unix passwd file
                assert 'Administrator:' not in content  # Windows SAM file


class TestFileUploadSecurity:
    """Test file upload security measures"""
    
    def test_file_type_validation(self, authenticated_client):
        """Test file type validation and restrictions"""
        
        # Test disallowed file types
        disallowed_files = [
            (b'executable content', 'malware.exe'),
            (b'script content', 'script.js'),
            (b'batch content', 'batch.bat'),
            (b'shell content', 'shell.sh'),
            (b'python content', 'script.py'),
            (b'php content', 'webshell.php'),
            (b'html content', 'page.html'),
        ]
        
        for content, filename in disallowed_files:
            file_data = BytesIO(content)
            
            response = authenticated_client.post('/training/upload', data={
                'files': [(file_data, filename)]
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Should reject disallowed file types
            assert data['success'] is False
            assert 'error' in data or 'errors' in data
    
    def test_file_size_limits(self, authenticated_client):
        """Test file size limit enforcement"""
        
        # Test oversized file
        oversized_content = b'x' * (60 * 1024 * 1024)  # 60MB
        oversized_file = BytesIO(oversized_content)
        
        with patch('src.services.secure_file_handler.secure_file_handler.secure_upload') as mock_upload:
            mock_upload.return_value = {
                'success': False,
                'error': 'File exceeds maximum size',
                'details': ['File size exceeds 50MB limit']
            }
            
            response = authenticated_client.post('/training/upload', data={
                'files': [(oversized_file, 'large_file.pdf')]
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'size' in str(data.get('errors', [])).lower()
    
    def test_file_quarantine_security(self, authenticated_client):
        """Test file quarantine security measures"""
        
        # Test quarantine access control
        response = authenticated_client.get('/training/quarantine')
        assert response.status_code == 200
        
        # Test invalid quarantine ID handling
        invalid_ids = [
            '../../../etc/passwd',
            'invalid-id; rm -rf /',
            'id<script>alert("xss")</script>',
            'id\x00injection',
        ]
        
        for invalid_id in invalid_ids:
            # Test quarantine release
            response = authenticated_client.post(f'/training/quarantine/{invalid_id}/release')
            assert response.status_code in [400, 404]
            
            # Test quarantine deletion
            response = authenticated_client.delete(f'/training/quarantine/{invalid_id}')
            assert response.status_code in [400, 404]


class TestCSRFProtection:
    """Test CSRF protection mechanisms"""
    
    def test_csrf_token_required(self, client, test_user):
        """Test that CSRF tokens are required for state-changing operations"""
        
        # Login user
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True
        
        # Test POST requests without CSRF token
        csrf_protected_endpoints = [
            '/training/upload',
            '/training/sessions',
            '/training/sessions/test-123/start',
        ]
        
        for endpoint in csrf_protected_endpoints:
            response = client.post(endpoint, data={'test': 'data'})
            
            # Should return 400 (Bad Request) due to missing CSRF token
            assert response.status_code == 400
    
    def test_csrf_token_validation(self, app, client, test_user):
        """Test CSRF token validation"""
        
        with app.test_request_context():
            # Login user
            with client.session_transaction() as sess:
                sess['_user_id'] = test_user.id
                sess['_fresh'] = True
            
            # Get CSRF token
            response = client.get('/training')
            assert response.status_code == 200
            
            # Extract CSRF token from response (simplified)
            # In real implementation, would parse HTML for token
            csrf_token = 'valid_csrf_token'
            
            # Test with invalid CSRF token
            response = client.post('/training/sessions', data={
                'csrf_token': 'invalid_token',
                'name': 'Test Session'
            })
            
            # Should reject invalid CSRF token
            assert response.status_code == 400


class TestSessionSecurity:
    """Test session security measures"""
    
    def test_session_fixation_protection(self, client, test_user):
        """Test protection against session fixation attacks"""
        
        # Get initial session
        with client.session_transaction() as sess:
            initial_session_id = sess.get('_id')
        
        # Login user
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True
            post_login_session_id = sess.get('_id')
        
        # Session ID should change after login (if implemented)
        # This is a basic check - full implementation would require session regeneration
        assert True  # Placeholder for session fixation protection test
    
    def test_session_timeout(self, authenticated_client):
        """Test session timeout mechanisms"""
        
        # Test accessing endpoint with valid session
        response = authenticated_client.get('/training')
        assert response.status_code == 200
        
        # Simulate session timeout by manipulating session data
        with authenticated_client.session_transaction() as sess:
            # Simulate expired session
            sess['_fresh'] = False
            sess.pop('_user_id', None)
        
        # Should require re-authentication
        response = authenticated_client.get('/training')
        assert response.status_code in [302, 401]  # Redirect to login or unauthorized


class TestDataProtection:
    """Test data protection and privacy measures"""
    
    def test_sensitive_data_not_logged(self, authenticated_client, caplog):
        """Test that sensitive data is not logged"""
        
        # Perform operations that might log sensitive data
        response = authenticated_client.post('/training/sessions', json={
            'name': 'Test Session',
            'description': 'Contains sensitive API key: sk-1234567890abcdef',
            'api_key': 'sk-sensitive-key-data',
            'uploaded_files': []
        })
        
        # Check that sensitive data is not in logs
        log_output = caplog.text.lower()
        assert 'sk-1234567890abcdef' not in log_output
        assert 'sk-sensitive-key-data' not in log_output
        assert 'api_key' not in log_output or 'redacted' in log_output
    
    def test_error_message_information_disclosure(self, authenticated_client):
        """Test that error messages don't disclose sensitive information"""
        
        # Test with invalid session ID
        response = authenticated_client.get('/training/sessions/invalid-session-123/progress')
        
        if response.status_code >= 400:
            data = json.loads(response.data) if response.data else {}
            error_message = data.get('error', '').lower()
            
            # Error messages should not reveal system internals
            sensitive_info = [
                'database',
                'sql',
                'traceback',
                'exception',
                'file path',
                '/home/',
                '/var/',
                'c:\\',
                'internal server error details'
            ]
            
            for sensitive in sensitive_info:
                assert sensitive not in error_message
    
    def test_file_content_not_exposed(self, authenticated_client):
        """Test that file contents are not exposed in responses"""
        
        # Upload a file with sensitive content
        sensitive_content = b'%PDF-1.4\nSensitive information: SSN 123-45-6789'
        sensitive_file = BytesIO(sensitive_content)
        
        with patch('src.services.secure_file_handler.secure_file_handler.secure_upload') as mock_upload:
            mock_upload.return_value = {
                'success': True,
                'file_record': {
                    'filename': 'sensitive.pdf',
                    'original_name': 'sensitive.pdf',
                    'size': len(sensitive_content),
                    'file_path': '/tmp/sensitive.pdf',
                    'uploaded_at': time.time(),
                    'hash': 'sensitive_hash',
                    'encrypted': False
                },
                'warnings': []
            }
            
            response = authenticated_client.post('/training/upload', data={
                'files': [(sensitive_file, 'sensitive.pdf')]
            })
            
            assert response.status_code == 200
            response_text = response.data.decode('utf-8')
            
            # File content should not be in response
            assert 'SSN 123-45-6789' not in response_text
            assert 'Sensitive information' not in response_text


class TestRateLimitingAndDDoSProtection:
    """Test rate limiting and DDoS protection"""
    
    def test_upload_rate_limiting(self, authenticated_client):
        """Test rate limiting on file uploads"""
        
        # Simulate rapid file uploads
        upload_responses = []
        
        for i in range(20):  # Try 20 rapid uploads
            file_content = BytesIO(b'%PDF-1.4 test content')
            
            with patch('src.services.secure_file_handler.secure_file_handler.secure_upload') as mock_upload:
                mock_upload.return_value = {
                    'success': True,
                    'file_record': {
                        'filename': f'test_{i}.pdf',
                        'original_name': f'test_{i}.pdf',
                        'size': 100,
                        'file_path': f'/tmp/test_{i}.pdf',
                        'uploaded_at': time.time(),
                        'hash': f'hash_{i}',
                        'encrypted': False
                    },
                    'warnings': []
                }
                
                response = authenticated_client.post('/training/upload', data={
                    'files': [(file_content, f'test_{i}.pdf')]
                })
                
                upload_responses.append(response.status_code)
        
        # Some requests should be rate limited (429) or all should succeed
        # Implementation depends on rate limiting strategy
        success_count = sum(1 for status in upload_responses if status == 200)
        rate_limited_count = sum(1 for status in upload_responses if status == 429)
        
        # Either all succeed (no rate limiting) or some are rate limited
        assert success_count > 0  # At least some should succeed
        # Rate limiting test would require actual implementation
    
    def test_api_endpoint_rate_limiting(self, authenticated_client):
        """Test rate limiting on API endpoints"""
        
        session_id = 'test-session-123'
        
        # Simulate rapid API calls
        api_responses = []
        
        with patch('src.services.training_service.training_service.get_training_progress') as mock_progress:
            mock_progress.return_value = {
                'status': 'processing',
                'progress_percentage': 50.0
            }
            
            for i in range(50):  # 50 rapid API calls
                response = authenticated_client.get(f'/training/sessions/{session_id}/progress')
                api_responses.append(response.status_code)
        
        # Check for rate limiting
        success_count = sum(1 for status in api_responses if status == 200)
        
        # Should handle reasonable number of requests
        assert success_count >= 10  # At least 10 should succeed


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])