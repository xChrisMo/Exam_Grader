import pytest
from webapp.exam_grader_app import app

def test_health_check(client):
    response = client.get('/api/health')
    assert response.status_code in (200, 503)
    data = response.get_json()
    assert 'status' in data
    assert 'db' in data['status']
    # Redis removed - no longer checked
    assert 'celery' in data['status']
    assert 'socketio' in data['status']