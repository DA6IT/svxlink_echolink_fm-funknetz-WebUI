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
