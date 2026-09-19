import json
import stat

from app.state_pty_collector import parse_state_pty_line, write_snapshot


def test_parse_documented_tx_state_line():
    assert parse_state_pty_line('1789854400.123 Tx:state {"transmit":true,"ignored":"no"}\n') == {
        'event': 'Tx:state', 'timestamp': '1789854400.123', 'kind': 'tx', 'state': True,
    }


def test_parse_documented_rx_state_arrays():
    assert parse_state_pty_line('1789854401.456 Rx:state {"sql_open":[true,false],"active":[true,true],"siglev":[42,17]}\n') == {
        'event': 'Rx:state', 'timestamp': '1789854401.456', 'kind': 'rx', 'state': [True, False],
        'sql_open': [True, False], 'active': [True, True], 'siglev': [42, 17],
    }


def test_parser_rejects_unknown_or_malformed_lines():
    assert parse_state_pty_line('1.0 SimplexLogic:sql_state {"sql_open":true}\n') is None
    assert parse_state_pty_line('1.0 Rx:state not-json\n') is None
    assert parse_state_pty_line('1.0 Rx:state {"name":"Rx1"}\n') is None


def test_snapshot_is_private_jsonl_and_atomic(tmp_path):
    output = tmp_path / 'nested' / 'state.jsonl'
    events = [{'event': 'Tx:state', 'kind': 'tx', 'state': True, 'timestamp': '1.0'}]
    write_snapshot(output, events)
    assert [json.loads(line) for line in output.read_text().splitlines()] == events
    assert stat.S_IMODE(output.stat().st_mode) == 0o640