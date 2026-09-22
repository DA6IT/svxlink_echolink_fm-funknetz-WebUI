import uuid

import pytest

from app import update_api as updater
from app import update_worker_prepare as updater_worker


def valid_request():
    return {
        "id": str(uuid.uuid4()),
        "action": "install",
        "expected_revision": "a" * 40,
        "target_revision": "b" * 40,
        "branch": "main",
    }


def test_web_update_disabled_by_default(
    monkeypatch,
):
    monkeypatch.setattr(
        updater,
        "UPDATE_ENABLED",
        False,
    )

    with pytest.raises(
        PermissionError
    ):
        updater.request_update(
            "install"
        )


def test_worker_rejects_request_when_disabled(
    monkeypatch,
):
    monkeypatch.setattr(
        updater_worker,
        "UPDATE_ENABLED",
        False,
    )

    with pytest.raises(
        RuntimeError,
        match="administrativ deaktiviert",
    ):
        updater_worker.validate_request(
            valid_request()
        )


def test_worker_accepts_valid_fixed_request(
    monkeypatch,
):
    monkeypatch.setattr(
        updater_worker,
        "UPDATE_ENABLED",
        True,
    )

    data = valid_request()

    result = (
        updater_worker
        .validate_request(
            data
        )
    )

    assert result == (
        data["id"],
        "install",
        "a" * 40,
        "b" * 40,
    )


@pytest.mark.parametrize(
    "action",
    [
        "shell",
        "exec",
        "upgrade-now",
        "../install",
    ],
)
def test_worker_rejects_unknown_actions(
    monkeypatch,
    action,
):
    monkeypatch.setattr(
        updater_worker,
        "UPDATE_ENABLED",
        True,
    )

    data = valid_request()
    data["action"] = action

    with pytest.raises(
        RuntimeError
    ):
        updater_worker.validate_request(
            data
        )


def test_worker_rejects_invalid_revision(
    monkeypatch,
):
    monkeypatch.setattr(
        updater_worker,
        "UPDATE_ENABLED",
        True,
    )

    data = valid_request()
    data["target_revision"] = (
        "../../etc/passwd"
    )

    with pytest.raises(
        RuntimeError
    ):
        updater_worker.validate_request(
            data
        )


def test_prepare_environment_is_isolated(
    tmp_path,
):
    from app.update_worker_testenv import (
        build_test_environment,
    )

    source = (
        tmp_path
        / "source"
    )

    job_dir = (
        tmp_path
        / "job"
    )

    (
        source
        / "backend"
    ).mkdir(
        parents=True
    )

    env = build_test_environment(
        source,
        job_dir,
    )

    assert env[
        "PYTHONPATH"
    ] == str(
        source
        / "backend"
    )

    assert env[
        "SVXLINK_ACTIVITY_DB"
    ] == str(
        job_dir
        / "test-state"
        / "activity.db"
    )

    assert env[
        "SVXLINK_LOG_PATH"
    ] == str(
        job_dir
        / "test-state"
        / "logs"
    )

    assert env[
        "FM_FUNKNETZ_MQTT_ENABLED"
    ] == "false"

    assert env[
        "SVXLINK_STATE_PTY_ENABLED"
    ] == "false"

    assert env[
        "SVXLINK_LOCAL_EVENT_INPUT_ENABLED"
    ] == "false"

    assert env[
        "TG_CONTROL_ENABLED"
    ] == "false"

    assert env[
        "SVXLINK_WEBUI_RESTART_WATCHER_ENABLED"
    ] == "false"


def test_prepare_environment_avoids_live_paths(
    tmp_path,
):
    from app.update_worker_testenv import (
        build_test_environment,
    )

    source = (
        tmp_path
        / "source"
    )

    (
        source
        / "backend"
    ).mkdir(
        parents=True
    )

    env = build_test_environment(
        source,
        tmp_path
        / "job",
    )

    forbidden_prefixes = (
        "/var/lib/svxlink-webui/",
        "/var/log/svxlink",
        "/run/svxlink",
        "/etc/svxlink/",
    )

    isolated_keys = (
        "SVXLINK_ACTIVITY_DB",
        "SVXLINK_CONFIG_PATH",
        "SVXLINK_NODE_INFO_PATH",
        "SVXLINK_LOG_PATH",
        "SVXLINK_PID_PATH",
        "SVXLINK_STATE_PTY_PATH",
        "TG_CONTROL_PTY",
    )

    for key in isolated_keys:
        value = env[key]

        assert not value.startswith(
            forbidden_prefixes
        )


def test_restart_ack_is_exactly_once(
    tmp_path,
    monkeypatch,
):
    import json

    from app import update_api

    control = (
        tmp_path
        / "control"
        / "backend-restart.json"
    )

    ack = (
        tmp_path
        / "requests"
        / "backend-restart-ack.json"
    )

    monkeypatch.setattr(
        update_api,
        "RESTART_REQUEST_FILE",
        control,
    )

    monkeypatch.setattr(
        update_api,
        "RESTART_ACK_FILE",
        ack,
    )

    restart_id = str(
        uuid.uuid4()
    )

    update_api.atomic_json(
        control,
        {
            "action":
                "restart",

            "request_id":
                str(
                    uuid.uuid4()
                ),

            "restart_id":
                restart_id,

            "revision":
                "a" * 40,

            "version":
                "test",
        },
    )

    assert (
        update_api
        .acknowledge_restart_request()
        is True
    )

    data = json.loads(
        ack.read_text(
            encoding="utf-8",
        )
    )

    assert (
        data[
            "restart_id"
        ]
        == restart_id
    )

    assert (
        update_api
        .acknowledge_restart_request()
        is False
    )


def test_restart_rejects_invalid_nonce(
    tmp_path,
    monkeypatch,
):
    from app import update_api

    control = (
        tmp_path
        / "control"
        / "backend-restart.json"
    )

    ack = (
        tmp_path
        / "requests"
        / "backend-restart-ack.json"
    )

    monkeypatch.setattr(
        update_api,
        "RESTART_REQUEST_FILE",
        control,
    )

    monkeypatch.setattr(
        update_api,
        "RESTART_ACK_FILE",
        ack,
    )

    update_api.atomic_json(
        control,
        {
            "action":
                "restart",

            "restart_id":
                "../../bad",

            "revision":
                "a" * 40,
        },
    )

    assert (
        update_api
        .acknowledge_restart_request()
        is False
    )

    assert not ack.exists()


def test_worker_cleans_matching_restart_handshake(
    tmp_path,
    monkeypatch,
):
    from app import update_worker_deploy

    control = (
        tmp_path
        / "control"
        / "backend-restart.json"
    )

    ack = (
        tmp_path
        / "requests"
        / "backend-restart-ack.json"
    )

    monkeypatch.setattr(
        update_worker_deploy,
        "RESTART_REQUEST_FILE",
        control,
    )

    monkeypatch.setattr(
        update_worker_deploy,
        "RESTART_ACK_FILE",
        ack,
    )

    restart_id = str(
        uuid.uuid4()
    )

    update_worker_deploy.atomic_json(
        control,
        {
            "restart_id":
                restart_id,
        },
    )

    update_worker_deploy.atomic_json(
        ack,
        {
            "restart_id":
                restart_id,
        },
    )

    update_worker_deploy.clear_restart_handshake(
        restart_id
    )

    assert not control.exists()
    assert not ack.exists()


def test_frontend_backup_uses_private_modes(
    tmp_path,
    monkeypatch,
):
    import stat

    from app import update_worker_deploy

    source = (
        tmp_path
        / "live"
    )

    assets = (
        source
        / "assets"
    )

    assets.mkdir(
        parents=True
    )

    (
        source
        / "index.html"
    ).write_text(
        "hello",
        encoding="utf-8",
    )

    (
        assets
        / "app.js"
    ).write_text(
        "console.log('ok')",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        update_worker_deploy,
        "DOCROOT",
        source,
    )

    destination = (
        tmp_path
        / "backup"
    )

    update_worker_deploy.backup_frontend(
        destination
    )

    assert (
        destination
        / "index.html"
    ).read_text(
        encoding="utf-8"
    ) == "hello"

    assets_mode = stat.S_IMODE(
        (
            destination
            / "assets"
        ).stat().st_mode
    )

    index_mode = stat.S_IMODE(
        (
            destination
            / "index.html"
        ).stat().st_mode
    )

    app_mode = stat.S_IMODE(
        (
            destination
            / "assets"
            / "app.js"
        ).stat().st_mode
    )

    assert assets_mode == 0o700
    assert index_mode == 0o600
    assert app_mode == 0o600


def test_frontend_backup_rejects_symlinks(
    tmp_path,
    monkeypatch,
):
    import pytest

    from app import update_worker_deploy

    source = (
        tmp_path
        / "live"
    )

    source.mkdir()

    outside = (
        tmp_path
        / "outside"
    )

    outside.write_text(
        "secret",
        encoding="utf-8",
    )

    (
        source
        / "bad-link"
    ).symlink_to(
        outside
    )

    monkeypatch.setattr(
        update_worker_deploy,
        "DOCROOT",
        source,
    )

    with pytest.raises(
        RuntimeError,
        match="nicht erlaubt|Nicht reguläre",
    ):
        update_worker_deploy.backup_frontend(
            tmp_path
            / "backup"
        )
