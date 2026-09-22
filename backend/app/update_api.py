from __future__ import annotations

import json
import os
import threading
import time
import uuid

from pathlib import Path
from typing import Any

from .update_config import (
    REQUEST_FILE,
    RESTART_REQUEST_FILE,
    REV_RE,
    UPDATE_BRANCH,
    UPDATE_ENABLED,
)

from .update_status import (
    update_status,
)


_restart_thread: (
    threading.Thread | None
) = None


def atomic_json(
    path: Path,
    data: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_name(
        f".{path.name}."
        f"{os.getpid()}.tmp"
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


def request_update(
    action: str = "install",
) -> dict[str, Any]:
    if not UPDATE_ENABLED:
        raise PermissionError(
            "Browser-Updates sind "
            "noch nicht freigeschaltet."
        )

    status = (
        update_status()
    )

    if action != "install":
        raise RuntimeError(
            "Ungültige Update-Aktion."
        )

    if not status[
        "worker_available"
    ]:
        raise RuntimeError(
            "Update-Worker ist "
            "nicht verfügbar."
        )

    if not status[
        "rootless_ready"
    ]:
        raise RuntimeError(
            "Rootless Updater ist "
            "nicht bereit."
        )

    if status[
        "dirty"
    ]:
        raise RuntimeError(
            "Lokaler Git-Checkout "
            "enthält Änderungen."
        )

    if not status[
        "branch_ok"
    ]:
        raise RuntimeError(
            "Der lokale Branch entspricht "
            "nicht dem Update-Kanal."
        )

    if not status[
        "available"
    ]:
        raise RuntimeError(
            "Es ist kein Update verfügbar."
        )

    local_revision = (
        status[
            "revision"
        ]
        or ""
    )

    target_revision = (
        status[
            "channel"
        ][
            "revision"
        ]
        or ""
    )

    if not REV_RE.fullmatch(
        local_revision
    ):
        raise RuntimeError(
            "Lokale Revision konnte "
            "nicht sicher bestimmt werden."
        )

    if not REV_RE.fullmatch(
        target_revision
    ):
        raise RuntimeError(
            "Zielrevision konnte nicht "
            "sicher bestimmt werden."
        )

    job = status.get(
        "job"
    )

    if (
        isinstance(
            job,
            dict,
        )
        and job.get(
            "state"
        )
        not in {
            "completed",
            "prepared",
            "failed",
        }
    ):
        raise RuntimeError(
            "Es läuft bereits ein Update."
        )

    if REQUEST_FILE.exists():
        raise RuntimeError(
            "Es wartet bereits eine "
            "Update-Anforderung."
        )

    request_id = str(
        uuid.uuid4()
    )

    payload = {
        "id":
            request_id,

        "action":
            "install",

        "expected_revision":
            local_revision,

        "target_revision":
            target_revision,

        "branch":
            UPDATE_BRANCH,

        "created_at":
            time.time(),
    }

    atomic_json(
        REQUEST_FILE,
        payload,
    )

    return {
        "accepted":
            True,

        "job_id":
            request_id,

        "target_revision":
            target_revision,
    }


def _restart_watch_loop() -> None:
    while True:
        try:
            data = json.loads(
                RESTART_REQUEST_FILE
                .read_text(
                    encoding="utf-8",
                )
            )

            revision = str(
                data.get(
                    "revision",
                    "",
                )
            ).lower()

            if (
                isinstance(
                    data,
                    dict,
                )
                and data.get(
                    "action"
                )
                == "restart"
                and REV_RE.fullmatch(
                    revision
                )
            ):
                RESTART_REQUEST_FILE.unlink(
                    missing_ok=True
                )

                time.sleep(
                    0.25
                )

                os._exit(
                    75
                )

        except (
            FileNotFoundError,
            OSError,
            ValueError,
            TypeError,
        ):
            pass

        time.sleep(
            0.5
        )


def start_restart_watcher() -> None:
    global _restart_thread

    enabled = (
        os.getenv(
            "SVXLINK_WEBUI_RESTART_WATCHER_ENABLED",
            "true",
        ).lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )

    if not enabled:
        return

    if (
        _restart_thread
        and _restart_thread.is_alive()
    ):
        return

    _restart_thread = threading.Thread(
        target=
            _restart_watch_loop,
        name=
            "webui-update-restart",
        daemon=
            True,
    )

    _restart_thread.start()
