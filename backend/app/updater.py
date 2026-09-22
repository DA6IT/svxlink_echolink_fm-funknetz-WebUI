from __future__ import annotations

import getpass
import json
import os
import subprocess
from pathlib import Path
from typing import Any


INSTALL_DIR = Path(
    os.getenv(
        "SVXLINK_WEBUI_INSTALL_DIR",
        "/opt/svxlink-webui",
    )
)

DOCROOT = Path(
    os.getenv(
        "SVXLINK_WEBUI_DOCROOT",
        "/var/www/new.shart",
    )
)

STATE_DIR = Path(
    os.getenv(
        "SVXLINK_WEBUI_STATE_DIR",
        "/var/lib/svxlink-webui",
    )
)

UPDATE_REMOTE = os.getenv(
    "SVXLINK_WEBUI_UPDATE_REMOTE",
    "https://github.com/DA6IT/"
    "svxlink_echolink_fm-funknetz-WebUI.git",
)

UPDATE_BRANCH = os.getenv(
    "SVXLINK_WEBUI_UPDATE_BRANCH",
    "main",
)

UPDATE_ENABLED = (
    os.getenv(
        "SVXLINK_WEBUI_UPDATE_ENABLED",
        "false",
    ).lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)

VERSION_FILE = (
    INSTALL_DIR
    / "VERSION"
)

CHANGELOG_FILE = (
    INSTALL_DIR
    / "CHANGELOG.md"
)

WORKER_STATUS_FILE = Path(
    os.getenv(
        "SVXLINK_WEBUI_UPDATE_STATUS_FILE",
        "/var/lib/svxlink-webui-update/worker-status.json",
    )
)


def _run(
    args: list[str],
    *,
    timeout: int = 8,
) -> subprocess.CompletedProcess[str]:

    env = dict(
        os.environ
    )

    env[
        "GIT_TERMINAL_PROMPT"
    ] = "0"

    if (
        args
        and args[0] == "git"
    ):
        args = [
            "git",
            "-c",
            f"safe.directory={INSTALL_DIR}",
            *args[1:],
        ]

    return subprocess.run(
        args,
        cwd=INSTALL_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


def _git(
    *args: str,
    timeout: int = 8,
) -> str:

    try:
        result = _run(
            [
                "git",
                *args,
            ],
            timeout=timeout,
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return ""

    if result.returncode != 0:
        return ""

    return (
        result.stdout
        .strip()
    )


def _read_text(
    path: Path,
    default: str = "",
) -> str:

    try:
        return (
            path.read_text(
                encoding="utf-8",
            )
            .strip()
        )
    except OSError:
        return default


def _current_revision() -> str:
    return _git(
        "rev-parse",
        "HEAD",
    )


def _current_branch() -> str:

    branch = _git(
        "branch",
        "--show-current",
    )

    return (
        branch
        or "detached"
    )


def _working_tree_dirty() -> bool:

    return bool(
        _git(
            "status",
            "--porcelain",
            "--untracked-files=no",
        )
    )


def _remote_revision() -> str:

    try:
        result = _run(
            [
                "git",
                "ls-remote",
                UPDATE_REMOTE,
                f"refs/heads/{UPDATE_BRANCH}",
            ],
            timeout=12,
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return ""

    if result.returncode != 0:
        return ""

    line = (
        result.stdout
        .strip()
        .splitlines()
    )

    if not line:
        return ""

    return (
        line[0]
        .split()[0]
        .strip()
    )


def _commit_known(
    revision: str,
) -> bool:

    if not revision:
        return False

    try:
        result = _run(
            [
                "git",
                "cat-file",
                "-e",
                f"{revision}^{{commit}}",
            ]
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return False

    return (
        result.returncode
        == 0
    )


def _is_ancestor(
    older: str,
    newer: str,
) -> bool:

    if (
        not older
        or not newer
    ):
        return False

    try:
        result = _run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                older,
                newer,
            ]
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return False

    return (
        result.returncode
        == 0
    )


def _relation(
    current: str,
    target: str,
) -> str:

    if not target:
        return "unavailable"

    if (
        current
        and current == target
    ):
        return "current"

    if (
        target
        and _commit_known(
            target
        )
    ):
        if _is_ancestor(
            current,
            target,
        ):
            return "update_available"

        if _is_ancestor(
            target,
            current,
        ):
            return "local_ahead"

        return "diverged"

    return "remote_new"


def _changelog() -> str:

    content = _read_text(
        CHANGELOG_FILE
    )

    if not content:
        return ""

    lines = (
        content
        .splitlines()
    )

    return "\n".join(
        lines[:80]
    )[:8000]


def _worker_status() -> dict[str, Any]:

    try:
        data = json.loads(
            WORKER_STATUS_FILE.read_text(
                encoding="utf-8",
            )
        )

        if isinstance(
            data,
            dict,
        ):
            return data

    except (
        OSError,
        ValueError,
        TypeError,
    ):
        pass

    return {}


def _writable(
    path: Path,
) -> bool:

    try:
        return (
            path.exists()
            and os.access(
                path,
                os.W_OK,
            )
        )
    except OSError:
        return False


def update_status() -> dict[str, Any]:

    current_revision = (
        _current_revision()
    )

    target_revision = (
        _remote_revision()
    )

    relation = _relation(
        current_revision,
        target_revision,
    )

    worker = (
        _worker_status()
    )

    permissions = (
        worker.get(
            "permissions",
            {},
        )
        if isinstance(
            worker,
            dict,
        )
        else {}
    )

    permissions = {
        "application":
            bool(
                permissions.get(
                    "application",
                    False,
                )
            ),

        "git":
            bool(
                permissions.get(
                    "git",
                    False,
                )
            ),

        "update_data":
            bool(
                permissions.get(
                    "update_data",
                    False,
                )
            ),

        "frontend":
            bool(
                permissions.get(
                    "frontend",
                    False,
                )
            ),
    }

    rootless_ready = bool(
        worker.get(
            "available",
            False,
        )
    ) and all(
        permissions.values()
    )

    current_version = (
        _read_text(
            VERSION_FILE,
            "unknown",
        )
    )

    available = (
        relation
        in {
            "update_available",
            "remote_new",
        }
    )

    if relation == "current":
        message = (
            "Der installierte Git-Stand "
            "entspricht dem Update-Kanal."
        )
    elif relation == "update_available":
        message = (
            "Eine neuere Revision ist "
            "im Update-Kanal verfügbar."
        )
    elif relation == "remote_new":
        message = (
            "Der Update-Kanal enthält "
            "eine noch nicht lokal "
            "vorhandene Revision."
        )
    elif relation == "local_ahead":
        message = (
            "Der lokale Entwicklungsstand "
            "ist neuer als der Update-Kanal."
        )
    elif relation == "diverged":
        message = (
            "Lokaler Stand und Update-Kanal "
            "haben sich auseinanderentwickelt."
        )
    else:
        message = (
            "Der Update-Kanal ist momentan "
            "nicht erreichbar."
        )

    return {
        "version":
            current_version,

        "revision":
            current_revision,

        "revision_short":
            current_revision[:8]
            if current_revision
            else "",

        "branch":
            _current_branch(),

        "dirty":
            _working_tree_dirty(),

        "channel": {
            "name":
                UPDATE_BRANCH,

            "remote":
                UPDATE_REMOTE,

            "revision":
                target_revision,

            "revision_short":
                target_revision[:8]
                if target_revision
                else "",
        },

        "relation":
            relation,

        "available":
            available,

        "enabled":
            UPDATE_ENABLED,

        "rootless_ready":
            rootless_ready,

        "permissions":
            permissions,

        "running_as":
            getpass.getuser(),

        "updater_user":
            worker.get(
                "user",
                "",
            ),

        "worker_available":
            bool(
                worker.get(
                    "available",
                    False,
                )
            ),

        "message":
            message,

        "changelog":
            _changelog(),

        "system_migration_required":
            False,
    }
