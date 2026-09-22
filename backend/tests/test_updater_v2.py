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
