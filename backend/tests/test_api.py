from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)


def test_health_and_status(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DEMO", False)
    monkeypatch.setattr(main, "NODE_INFO_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(main, "CONFIG_PATH", tmp_path / "missing.conf")
    monkeypatch.setattr(main, "LOG_PATH", tmp_path / "missing.log")
    response = client.get('/api/status')
    assert response.status_code == 200
    body = response.json()
    assert body['demo'] is False
    assert 'updated_at' in body
    assert client.get('/health').json()['version'] == '0.2.0'


def test_missing_config_is_safe(tmp_path):
    assert main.parse_ini(tmp_path / 'missing.conf') == {}


def test_config_and_node_are_allowlisted(tmp_path):
    config = tmp_path / 'svxlink.conf'
    config.write_text('[ReflectorLogic]\nDEFAULT_TG=26298\nAUTH_KEY=secret\n')
    node = tmp_path / 'node.json'
    node.write_text('{"Location":"Lab","DefaultTG":26298,"password":"secret"}')
    assert main.parse_ini(config) == {'ReflectorLogic': {'DEFAULT_TG': '26298'}}
    assert main.read_node_info(node) == {'Location': 'Lab', 'DefaultTG': 26298}


def test_reflector_activity_reads_join_leave_only(tmp_path, monkeypatch):
    log = tmp_path / 'svxlink.log'
    log.write_text('2026-09-19 12:00:00.100 ReflectorLogic: Node joined: DA6IT-L\n'
                   '2026-09-19 12:01:00.000 ReflectorLogic: Node left: DL1ABC\n')
    monkeypatch.setattr(main, 'LOG_PATH', log)
    activity = main.reflector_activity()
    assert activity['count'] == 2
    assert activity['last_heard']['callsign'] == 'DL1ABC'


def test_config_endpoint_is_not_public():
    assert client.get('/api/config').status_code == 404


def test_websocket():
    with client.websocket_connect('/api/ws/live') as ws:
        assert ws.receive_json()['event'] == 'node.status'


def test_talkgroups_never_claim_external_or_control(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'CONFIG_PATH', tmp_path / 'missing.conf')
    monkeypatch.setattr(main, 'LOG_PATH', tmp_path / 'missing.log')
    body = client.get('/api/talkgroups').json()
    assert body['external'] == {'available': False, 'reason': 'Keine bestätigte FM-Funknetz-Datenquelle konfiguriert.'}
    assert body['control']['enabled'] is False
    assert body['confirmed'] is False


def test_talkgroups_only_confirms_new_allowlisted_selection(tmp_path, monkeypatch):
    log = tmp_path / 'svxlink.log'
    log.write_text('2026-09-19 12:00:00 ReflectorLogic: Selecting TG #123\n'
                   '2026-09-19 12:01:00 ReflectorLogic: Selecting TG #999\n')
    monkeypatch.setattr(main, 'LOG_PATH', log)
    monkeypatch.setattr(main, 'TG_ALLOWLIST', frozenset({'123'}))
    result = main.talkgroup_activity()
    assert result == [{'talkgroup': '123', 'timestamp': '2026-09-19T12:00:00'}]
