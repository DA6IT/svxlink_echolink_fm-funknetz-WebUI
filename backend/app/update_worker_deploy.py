from __future__ import annotations

import http.client
import json
import os
import shutil
import time

from pathlib import Path

from .update_worker_common import (
    DOCROOT,
    INSTALL_DIR,
    RESTART_REQUEST_FILE,
    VENV_LINK,
    atomic_json,
    now_iso,
)


def deploy_frontend(
    source: Path,
) -> None:
    assets_source = (
        source
        / "assets"
    )

    assets_target = (
        DOCROOT
        / "assets"
    )

    assets_target.mkdir(
        parents=True,
        exist_ok=True,
    )

    if assets_source.is_dir():
        shutil.copytree(
            assets_source,
            assets_target,
            dirs_exist_ok=True,
        )

    for item in source.iterdir():
        if item.name in {
            "assets",
            "index.html",
        }:
            continue

        target = (
            DOCROOT
            / item.name
        )

        if item.is_dir():
            shutil.copytree(
                item,
                target,
                dirs_exist_ok=True,
            )
        else:
            tmp = target.with_name(
                f".{target.name}.update"
            )

            shutil.copy2(
                item,
                tmp,
            )

            os.replace(
                tmp,
                target,
            )

    index_tmp = (
        DOCROOT
        / ".index.html.update"
    )

    shutil.copy2(
        source
        / "index.html",
        index_tmp,
    )

    os.replace(
        index_tmp,
        DOCROOT
        / "index.html",
    )

    if assets_source.is_dir():
        keep = {
            item.name
            for item
            in assets_source.iterdir()
        }

        for item in (
            assets_target
            .iterdir()
        ):
            if item.name in keep:
                continue

            if item.is_dir():
                shutil.rmtree(
                    item,
                    ignore_errors=True,
                )
            else:
                item.unlink(
                    missing_ok=True
                )


def activate_venv(
    runtime: Path,
) -> None:
    tmp = (
        INSTALL_DIR
        / ".venv-current.next"
    )

    tmp.unlink(
        missing_ok=True
    )

    tmp.symlink_to(
        runtime
    )

    os.replace(
        tmp,
        VENV_LINK,
    )


def restart_backend(
    request_id: str,
    revision: str,
    version: str,
) -> None:
    atomic_json(
        RESTART_REQUEST_FILE,
        {
            "action":
                "restart",
            "request_id":
                request_id,
            "revision":
                revision,
            "version":
                version,
            "created_at":
                now_iso(),
        },
    )


def health(
    expected_version: str,
) -> bool:
    connection = (
        http.client
        .HTTPConnection(
            "127.0.0.1",
            12346,
            timeout=2,
        )
    )

    try:
        connection.request(
            "GET",
            "/health",
        )

        response = (
            connection
            .getresponse()
        )

        raw = response.read(
            1024 * 1024
        )

        if response.status != 200:
            return False

        data = json.loads(
            raw.decode(
                "utf-8"
            )
        )

        return (
            data.get("ok")
            is True
            and str(
                data.get(
                    "version",
                    "",
                )
            )
            == expected_version
        )

    except (
        OSError,
        ValueError,
        http.client.HTTPException,
    ):
        return False

    finally:
        connection.close()


def wait_health(
    version: str,
    timeout: int = 60,
) -> bool:
    deadline = (
        time.monotonic()
        + timeout
    )

    while (
        time.monotonic()
        < deadline
    ):
        if health(
            version
        ):
            return True

        time.sleep(1)

    return False
