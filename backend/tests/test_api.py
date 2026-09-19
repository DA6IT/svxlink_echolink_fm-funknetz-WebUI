from fastapi.testclient import TestClient
from app.main import app, parse_ini
from pathlib import Path

client = TestClient(app)

def test_health_and_status():
    assert client.get('/health').json()['version'] == '0.1.0'
    assert client.get('/api/status').json()['demo'] is True

def test_missing_config_is_safe(tmp_path):
    assert parse_ini(tmp_path / 'missing.conf') == {}

def test_api_contracts():
    assert client.get('/api/config').status_code == 200
    assert client.get('/api/node-info').status_code == 200
    assert client.get('/api/talkgroups').json()['active'] == 26298

def test_websocket():
    with client.websocket_connect('/api/ws/live') as ws:
        assert ws.receive_json()['event'] == 'node.status'
