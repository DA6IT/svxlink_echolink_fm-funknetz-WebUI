from __future__ import annotations

import getpass
import json
import os
import re
import subprocess

from datetime import datetime
from pathlib import Path
from typing import Any


UPDATER_PROTOCOL = 2

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

UPDATE_DATA_DIR = Path(
    os.getenv(
        "SVXLINK_WEBUI_UPDATE_DATA_DIR",
        "/var/lib/svxlink-webui-updater",
    )
)

IPC_DIR = Path(
    os.getenv(
        "SVXLINK_WEBUI_UPDATE_IPC_DIR",
        "/var/lib/svxlink-webui-update",
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
    in {"1", "true", "yes", "on"}
)

STATUS_FILE = (
    IPC_DIR
    / "status"
    / "worker-status.json"
)

REQUEST_FILE = (
    IPC_DIR
    / "requests"
    / "request.json"
)

RESTART_REQUEST_FILE = (
    IPC_DIR
    / "control"
    / "backend-restart.json"
)

RESTART_ACK_FILE = (
    IPC_DIR
    / "requests"
    / "backend-restart-ack.json"
)

JOBS_DIR = UPDATE_DATA_DIR / "jobs"
VENV_DIR = UPDATE_DATA_DIR / "venvs"
BACKUP_DIR = UPDATE_DATA_DIR / "backups"

VENV_LINK = (
    INSTALL_DIR
    / ".venv-current"
)

REV_RE = re.compile(
    r"^[0-9a-f]{40}$"
)

REQ_RE = re.compile(
    r"^[0-9a-f]{8}-"
    r"[0-9a-f]{4}-"
    r"[0-9a-f]{4}-"
    r"[0-9a-f]{4}-"
    r"[0-9a-f]{12}$"
)

BRANCH_RE = re.compile(
    r"^[A-Za-z0-9._/-]{1,128}$"
)


def now_iso() -> str:
    return (
        datetime.now()
        .astimezone()
        .isoformat()
    )


def writable(
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


def atomic_json(
    path: Path,
    data: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_name(
        f".{path.name}.{os.getpid()}.tmp"
    )

    tmp.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    os.chmod(
        tmp,
        0o640,
    )

    os.replace(
        tmp,
        path,
    )


def read_json(
    path: Path,
) -> dict[str, Any]:
    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        ValueError,
        TypeError,
    ):
        return {}

    return (
        data
        if isinstance(
            data,
            dict,
        )
        else {}
    )


def append_log(
    path: Path,
    message: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            f"[{now_iso()}] "
            f"{message}\n"
        )


def run(
    args: list[str],
    *,
    cwd: Path,
    log: Path,
    timeout: int = 300,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(
        os.environ
    )

    env.update(
        {
            "HOME":
                str(
                    UPDATE_DATA_DIR
                ),
            "GIT_TERMINAL_PROMPT":
                "0",
            "PIP_DISABLE_PIP_VERSION_CHECK":
                "1",
        }
    )

    if extra_env:
        env.update(
            extra_env
        )

    append_log(
        log,
        "$ " + " ".join(args),
    )

    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )

    if result.stdout:
        append_log(
            log,
            result.stdout.rstrip(),
        )

    if result.stderr:
        append_log(
            log,
            result.stderr.rstrip(),
        )

    if result.returncode != 0:
        raise RuntimeError(
            "Befehl fehlgeschlagen "
            f"({result.returncode}): "
            + " ".join(args)
        )

    return result


def git(
    *args: str,
    log: Path,
    timeout: int = 120,
) -> str:
    result = run(
        [
            "git",
            "-c",
            f"safe.directory={INSTALL_DIR}",
            *args,
        ],
        cwd=INSTALL_DIR,
        log=log,
        timeout=timeout,
    )

    return result.stdout.strip()


def log_tail(
    path: Path,
    limit: int = 30,
) -> list[str]:
    try:
        return (
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
            .splitlines()[-limit:]
        )
    except OSError:
        return []


def base_snapshot() -> dict[str, Any]:
    permissions = {
        "application":
            writable(
                INSTALL_DIR
            ),
        "git":
            writable(
                INSTALL_DIR
                / ".git"
            ),
        "update_data":
            writable(
                UPDATE_DATA_DIR
            ),
        "frontend":
            writable(
                DOCROOT
            ),
    }

    return {
        "available":
            True,
        "protocol":
            UPDATER_PROTOCOL,
        "user":
            getpass.getuser(),
        "permissions":
            permissions,
        "ready":
            all(
                permissions.values()
            ),
        "updated_at":
            now_iso(),
    }


def write_status(
    job: dict[str, Any] | None = None,
    log: Path | None = None,
) -> None:
    payload = (
        base_snapshot()
    )

    if job is not None:
        item = dict(
            job
        )

        if log is not None:
            item[
                "log_tail"
            ] = log_tail(
                log
            )

        payload[
            "job"
        ] = item

    atomic_json(
        STATUS_FILE,
        payload,
    )


def phase(
    job: dict[str, Any],
    state: str,
    progress: int,
    message: str,
    log: Path,
) -> None:
    job.update(
        {
            "state":
                state,
            "progress":
                max(
                    0,
                    min(
                        100,
                        int(progress),
                    ),
                ),
            "message":
                message,
            "updated_at":
                now_iso(),
        }
    )

    append_log(
        log,
        message,
    )

    write_status(
        job,
        log,
    )


def ensure_dirs() -> None:
    UPDATE_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for path in (
        JOBS_DIR,
        VENV_DIR,
        BACKUP_DIR,
    ):
        path.mkdir(
            parents=True,
            exist_ok=True,
        )
