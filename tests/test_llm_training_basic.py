"""
Basic test for LLM training functionality
"""

import pytest
import json
from webapp.app_factory import create_app
from src.database.models import db, User, LLMDocument, LLMDataset
from werkzeug.security import generate_password_hash

@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
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
            username='testuser',
            email='test@example.com',
            password_hash=generate_password_hash('testpass123'),
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        return user

def test_llm_training_page_loads(client, test_user):
    """Test that the LLM training page loads correctly"""
    # Login first
    login_response = client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    })
    assert login_response.status_code in [200, 302]
    
    # Access LLM training page
    response = client.get('/llm-training/')
    assert response.status_code == 200
    assert b'LLM Training Platform' in response.data
    assert b'Documents' in response.data
    assert b'Datasets' in response.data
    assert b'Training' in response.data
    assert b'Reports' in response.data

def test_llm_training_stats_api(client, test_user):
    """Test the stats API endpoint"""
    # Login first
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # Test stats endpoint
    response = client.get('/llm-training/api/stats')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'stats' in data
    assert 'datasets' in data['stats']
    assert 'training' in data['stats']

def test_llm_documents_api(client, test_user):
    """Test the documents API endpoint"""
    # Login first
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # Test documents endpoint
    response = client.get('/llm-training/api/documents')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'documents' in data

def test_llm_datasets_api(client, test_user):
    """Test the datasets API endpoint"""
    # Login first
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # Test datasets endpoint
    response = client.get('/llm-training/api/datasets')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'datasets' in data

def test_llm_training_jobs_api(client, test_user):
    """Test the training jobs API endpoint"""
    # Login first
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # Test training jobs endpoint
    response = client.get('/llm-training/api/training-jobs')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'jobs' in data

def test_llm_reports_api(client, test_user):
    """Test the reports API endpoint"""
    # Login first
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # Test reports endpoint
    response = client.get('/llm-training/api/reports')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'reports' in data

def test_create_dataset_api(client, test_user):
    """Test creating a dataset via API"""
    # Login first
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # Create dataset
    response = client.post('/llm-training/api/datasets', 
                          json={
                              'name': 'Test Dataset',
                              'description': 'A test dataset'
                          },
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'dataset' in data
    assert data['dataset']['name'] == 'Test Dataset'

def test_models_api(client, test_user):
    """Test the models API endpoint"""
    # Login first
    client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    # Test models endpoint
    response = client.get('/llm-training/api/models')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'models' in data
    assert len(data['models']) > 0  # Should have some default models

if __name__ == '__main__':
    pytest.main([__file__])
