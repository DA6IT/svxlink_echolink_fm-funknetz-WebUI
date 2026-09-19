from email.message import Message
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


def test_talkgroups_exposes_confirmed_fm_funknetz_data(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'CONFIG_PATH', tmp_path / 'missing.conf')
    monkeypatch.setattr(main, 'LOG_PATH', tmp_path / 'missing.log')
    monkeypatch.setattr(main, 'fm_funknetz_live', lambda: {
        'available': True, 'active': {'call': 'DL1ABC', 'tg': '26298'}, 'client_count': None,
        'live': [{'call': 'DL1ABC', 'tg': '26298'}, {'call': 'DL3XYZ', 'tg': '91166'}],
        'last_heard': [{'call': 'DL2XYZ', 'tg': '26298'}],
    })
    body = client.get('/api/talkgroups').json()
    assert body['external']['available'] is True
    assert body['external']['source'] == 'FM-Funknetz'
    assert body['external']['active'] == {'call': 'DL1ABC', 'tg': '26298'}
    assert body['external']['live'] == [{'call': 'DL1ABC', 'tg': '26298'}, {'call': 'DL3XYZ', 'tg': '91166'}]
    assert body['control']['enabled'] is False
    assert body['confirmed'] is False


def test_fm_funknetz_failure_is_safe(monkeypatch):
    monkeypatch.setattr(main, 'FM_MQTT_ENABLED', True)
    monkeypatch.setattr(main, '_get_json', lambda url: (_ for _ in ()).throw(OSError('offline')))
    result = main.fm_funknetz_live()
    assert result['available'] is False
    assert result['live'] == []
    assert result['mqtt']['topics'] == ['/server/statethr', '/server/statethr/1', '/server/state/logins']
    assert result['mqtt']['configured'] is main.FM_MQTT_ENABLED
    assert result['mqtt']['adapter_active'] is False


def test_fm_feed_urls_are_strictly_allowlisted():
    main._validate_feed_url('https://dashboard.fm-funknetz.de/data/live.json')
    for invalid in (
        'file:///etc/passwd', 'http://dashboard.fm-funknetz.de/data/live.json',
        'https://127.0.0.1/data/live.json', 'https://dashboard.fm-funknetz.de/data/other.json',
        'https://example.test/data/live.json',
        'https://dashboard.fm-funknetz.de@127.0.0.1/data/live.json',
        'https://dashboard.fm-funknetz.de/data/live.json?redirect=http://127.0.0.1',
    ):
        try:
            main._validate_feed_url(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f'accepted unallowlisted feed URL: {invalid}')


def test_fm_feed_redirect_is_not_followed(monkeypatch):
    class RedirectOpener:
        def open(self, request, timeout):
            headers = Message()
            headers['Location'] = 'https://example.test/data/live.json'
            raise main.urllib.error.HTTPError(
                request.full_url, 302, 'redirect', headers, None)

    monkeypatch.setattr(main.urllib.request, 'build_opener', lambda handler: RedirectOpener())
    try:
        main._get_json('https://dashboard.fm-funknetz.de/data/live.json')
    except main.urllib.error.HTTPError:
        pass
    else:
        raise AssertionError('followed an unverified feed redirect')


def test_talkgroups_only_confirms_new_allowlisted_selection(tmp_path, monkeypatch):
    log = tmp_path / 'svxlink.log'
    log.write_text('2026-09-19 12:00:00 ReflectorLogic: Selecting TG #123\n'
                   '2026-09-19 12:01:00 ReflectorLogic: Selecting TG #999\n')
    monkeypatch.setattr(main, 'LOG_PATH', log)
    monkeypatch.setattr(main, 'TG_ALLOWLIST', frozenset({'123'}))
    result = main.talkgroup_activity()
    assert result == [{'talkgroup': '123', 'timestamp': '2026-09-19T12:00:00'}]


def test_talkgroups_accepts_colon_separated_production_timestamp(tmp_path, monkeypatch):
    log = tmp_path / 'svxlink.log'
    log.write_text('19 Sep 2026 22:57:36.214: ReflectorLogic: Selecting TG #47669\n')
    monkeypatch.setattr(main, 'LOG_PATH', log)
    monkeypatch.setattr(main, 'TG_ALLOWLIST', frozenset({'47669'}))
    assert main.talkgroup_activity() == [
        {'talkgroup': '47669', 'timestamp': '2026-09-19T22:57:36.214'}
    ]


def test_local_log_rf_activity_tracks_rx_tg_and_talker_resets(tmp_path, monkeypatch):
    log = tmp_path / 'svxlink.log'
    log.write_text(
        '2026-09-19 12:00:00 INFO Rx1: The squelch is OPEN (-42.5)\n'
        '2026-09-19 12:00:01 INFO ReflectorLogic: Selecting TG #47669\n'
        '2026-09-19 12:00:02 INFO ReflectorLogic: Talker start on TG #47669: DA6IT-HS\n'
        '2026-09-19 12:00:03 INFO Rx1: The squelch is CLOSED (-55)\n'
        '2026-09-19 12:00:04 INFO ReflectorLogic: Talker stop on TG #47669: DA6IT-HS\n'
        'this line is ignored\n')
    monkeypatch.setattr(main, 'LOG_PATH', log)
    result = main.local_log_rf_activity()
    assert result['source'] == 'SvxLink-Log'
    assert result['rx'] == {'squelch': 'closed', 'level': -55.0, 'timestamp': '2026-09-19T12:00:03'}
    assert result['talkgroup'] == {'tg': '47669', 'timestamp': '2026-09-19T12:00:01'}
    assert result['talker'] is None
    assert result['updated_at'] == '2026-09-19T12:00:04'


def test_local_log_rf_activity_accepts_production_sv_link_timestamps(tmp_path, monkeypatch):
    log = tmp_path / 'svxlink.log'
    log.write_text(
        '19 Sep 2026 22:23:43.114 INFO Rx1: The squelch is OPEN (-42.5)\n'
        '19 Sep 2026 22:23:44.114 INFO ReflectorLogic: Selecting TG #47669\n'
        '19 Sep 2026 22:23:45.114 INFO ReflectorLogic: Talker start on TG #47669: DA6IT-HS\n')
    monkeypatch.setattr(main, 'LOG_PATH', log)
    result = main.local_log_rf_activity()
    assert result['rx'] == {'squelch': 'open', 'level': -42.5, 'timestamp': '2026-09-19T22:23:43.114'}
    assert result['talkgroup'] == {'tg': '47669', 'timestamp': '2026-09-19T22:23:44.114'}
    assert result['talker'] == {'tg': '47669', 'callsign': 'DA6IT-HS', 'timestamp': '2026-09-19T22:23:45.114'}
    assert result['updated_at'] == '2026-09-19T22:23:45.114'


def test_local_log_rf_activity_resets_production_states_on_close_and_stop(tmp_path, monkeypatch):
    log = tmp_path / 'svxlink.log'
    log.write_text(
        '19 Sep 2026 22:57:35.214: Rx1: The squelch is OPEN (120)\n'
        '19 Sep 2026 22:57:36.214: ReflectorLogic: Selecting TG #47669\n'
        '19 Sep 2026 22:57:36.314: ReflectorLogic: Talker start on TG #47669: DA6IT-HS\n'
        '19 Sep 2026 22:57:37.214: Rx1: The squelch is CLOSED (182)\n'
        '19 Sep 2026 22:57:38.214: ReflectorLogic: Talker stop on TG #47669: DA6IT-HS\n')
    monkeypatch.setattr(main, 'LOG_PATH', log)
    result = main.local_log_rf_activity()
    assert result['rx'] == {'squelch': 'closed', 'level': 182.0, 'timestamp': '2026-09-19T22:57:37.214'}
    assert result['talkgroup'] == {'tg': '47669', 'timestamp': '2026-09-19T22:57:36.214'}
    assert result['talker'] is None


def test_state_pty_collector_is_opt_in_read_only_and_normalized(tmp_path, monkeypatch):
    state = tmp_path / 'state.jsonl'
    state.write_text('{"event":"Tx:state","state":true,"timestamp":"1789854400.123"}\n'
                     '{"event":"Rx:state","state":[true,false],"sql_open":[true,false],"active":[true,true],"siglev":[42,17],"timestamp":"1789854401.456"}\n'
                     '{"event":"unknown","state":true}\nnot json\n')
    monkeypatch.setattr(main, 'STATE_PTY_PATH', state)
    monkeypatch.setattr(main, 'STATE_PTY_ENABLED', True)
    result = main.local_rf_telemetry()
    assert result['available'] is True
    assert result['tx']['state'] is True
    assert result['rx'] == {'source': 'STATE_PTY', 'kind': 'rx', 'state': [True, False], 'sql_open': [True, False], 'active': [True, True], 'siglev': [42, 17], 'timestamp': '1789854401.456'}
    monkeypatch.setattr(main, 'STATE_PTY_ENABLED', False)
    assert main.local_rf_telemetry()['available'] is False


def test_normalized_event_input_is_feature_flagged(monkeypatch):
    monkeypatch.setattr(main, 'LOCAL_EVENT_INPUT_ENABLED', False)
    assert main.normalized_local_events()['enabled'] is False
