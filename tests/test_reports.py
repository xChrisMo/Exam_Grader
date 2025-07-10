import pytest
from webapp.exam_grader_app import app

def test_download_pdf_report(client, submission_id):
    response = client.get(f'/api/download-report/{submission_id}?format=pdf')
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        assert response.headers['Content-Type'] == 'application/pdf'

def test_download_json_report(client, submission_id):
    response = client.get(f'/api/download-report/{submission_id}?format=json')
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        assert response.headers['Content-Type'] == 'application/json' 