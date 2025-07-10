import pytest
from src.services.realtime_service import socketio
from flask import Flask

@pytest.fixture
def test_app():
    app = Flask(__name__)
    socketio.init_app(app)
    return app

def test_websocket_connect(test_app):
    client = socketio.test_client(test_app)
    received = client.get_received()
    assert any(event['name'] == 'connected' for event in received)
    client.disconnect() 