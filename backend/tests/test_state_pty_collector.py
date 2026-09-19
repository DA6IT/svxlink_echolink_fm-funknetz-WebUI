import json
import stat
from pathlib import Path

from app.state_pty_collector import parse_state_pty_line, write_snapshot
from app.state_pty_permissions import bind_permissions


def test_state_pty_units_require_the_restart_bound_binder():
    collector = (Path(__file__).parents[2] / 'deploy/systemd/svxlink-state-collector.service').read_text()
    binder = (Path(__file__).parents[2] / 'deploy/systemd/svxlink-state-pty-permissions.service').read_text()
    assert 'After=svxlink.service svxlink-state-pty-permissions.service' in collector
    assert 'Requires=svxlink.service svxlink-state-pty-permissions.service' in collector
    assert 'PrivateDevices=' not in collector
    assert 'WantedBy=svxlink.service' in binder
    assert 'Before=' not in binder
    assert 'WorkingDirectory=/opt/svxlink-webui/backend' in binder
    assert 'Environment=PYTHONPATH=/opt/svxlink-webui/backend' in binder
    assert 'ExecStart=/opt/svxlink-webui/.venv/bin/python -m app.state_pty_permissions' in binder


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


def test_permission_binder_accepts_sv_link_to_direct_pty(tmp_path, monkeypatch):
    import os

    master, slave = os.openpty()
    try:
        target = Path(os.ttyname(slave))
        link = tmp_path / 'state'
        link.symlink_to(target)
        monkeypatch.setattr('app.state_pty_permissions.grp.getgrnam', lambda name: type('Group', (), {'gr_gid': 1234})())
        chowned = []
        monkeypatch.setattr('app.state_pty_permissions.os.fchown', lambda fd, uid, gid: chowned.append(Path(os.ttyname(fd))))
        monkeypatch.setattr('app.state_pty_permissions.os.fchmod', lambda fd, mode: None)
        bind_permissions(link)
        assert chowned == [target]
    finally:
        os.close(master)
        os.close(slave)


def test_permission_binder_rejects_escaping_symlink(tmp_path):
    target = tmp_path / 'target'
    target.write_text('not a PTY')
    link = tmp_path / 'state'
    link.symlink_to(target)
    try:
        bind_permissions(link)
    except ValueError as error:
        assert 'direct /dev/pts' in str(error)
    else:
        raise AssertionError('symlink must be rejected')


def test_permission_binder_rejects_symlink_to_regular_file_under_pts(tmp_path, monkeypatch):
    link = tmp_path / 'state'
    link.symlink_to('/dev/pts/5')
    monkeypatch.setattr('app.state_pty_permissions.os.readlink', lambda path: '/dev/pts/5')

    def fake_lstat(path):
        return type('Info', (), {'st_mode': stat.S_IFLNK})()
    monkeypatch.setattr('app.state_pty_permissions.os.lstat', fake_lstat)
    monkeypatch.setattr('app.state_pty_permissions.os.open', lambda path, flags: 99)
    monkeypatch.setattr('app.state_pty_permissions.os.fstat', lambda fd: type('Info', (), {'st_mode': stat.S_IFREG})())
    monkeypatch.setattr('app.state_pty_permissions.os.close', lambda fd: None)
    try:
        bind_permissions(link)
    except ValueError as error:
        assert 'direct character device or FIFO' in str(error)
    else:
        raise AssertionError('regular file target must be rejected')


def test_permission_binder_sets_reader_group_and_read_only_mode(tmp_path, monkeypatch):
    import os

    path = tmp_path / 'state'
    os.mkfifo(path, 0o620)
    monkeypatch.setattr('app.state_pty_permissions.grp.getgrnam', lambda name: type('Group', (), {'gr_gid': 1234})())
    monkeypatch.setattr('app.state_pty_permissions.os.fchown', lambda fd, uid, gid: None)
    bind_permissions(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o640