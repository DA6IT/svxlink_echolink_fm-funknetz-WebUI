from fastapi.testclient import TestClient
from app.main import VERSION, app, parse_ini
from pathlib import Path

client = TestClient(app)

def test_health_and_status():
    assert client.get('/health').json()['version'] == VERSION
    assert isinstance(client.get('/api/status').json()['demo'], bool)

def test_missing_config_is_safe(tmp_path):
    assert parse_ini(tmp_path / 'missing.conf') == {}

def test_public_api_contracts():
    assert client.get('/api/config').status_code == 404
    assert client.get('/api/node-info').status_code == 200
    assert 'active' in client.get('/api/talkgroups').json()

def test_websocket():
    with client.websocket_connect('/api/ws/live') as ws:
        assert ws.receive_json()['event'] == 'node.status'
