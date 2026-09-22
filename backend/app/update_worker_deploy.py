from __future__ import annotations

import http.client
import json
import os
import shutil
import time
import uuid

from pathlib import Path

from .update_worker_common import (
    DOCROOT,
    INSTALL_DIR,
    RESTART_ACK_FILE,
    RESTART_REQUEST_FILE,
    VENV_LINK,
    atomic_json,
    now_iso,
    read_json,
)


def backup_frontend(
    destination: Path,
) -> None:
    """
    Copy only frontend content.

    Do not preserve ownership, ACLs, xattrs, timestamps or
    SUID/SGID bits from the live webroot.  The updater service
    deliberately runs with RestrictSUIDSGID=true.
    """

    if not DOCROOT.is_dir():
        raise RuntimeError(
            "Frontend-DocumentRoot fehlt."
        )

    shutil.rmtree(
        destination,
        ignore_errors=True,
    )

    destination.mkdir(
        parents=True,
        mode=0o700,
    )

    for root, dirs, files in os.walk(
        DOCROOT,
        topdown=True,
        followlinks=False,
    ):
        source_root = Path(
            root
        )

        relative = (
            source_root
            .relative_to(
                DOCROOT
            )
        )

        target_root = (
            destination
            / relative
        )

        target_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        os.chmod(
            target_root,
            0o700,
        )

        for name in tuple(
            dirs
        ):
            source_dir = (
                source_root
                / name
            )

            if source_dir.is_symlink():
                raise RuntimeError(
                    "Symlink im Frontend "
                    f"nicht erlaubt: {source_dir}"
                )

            target_dir = (
                target_root
                / name
            )

            target_dir.mkdir(
                exist_ok=True,
            )

            os.chmod(
                target_dir,
                0o700,
            )

        for name in files:
            source_file = (
                source_root
                / name
            )

            if (
                source_file.is_symlink()
                or not source_file.is_file()
            ):
                raise RuntimeError(
                    "Nicht reguläre Frontend-Datei: "
                    f"{source_file}"
                )

            target_file = (
                target_root
                / name
            )

            shutil.copyfile(
                source_file,
                target_file,
            )

            os.chmod(
                target_file,
                0o600,
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
) -> str:
    restart_id = str(
        uuid.uuid4()
    )

    atomic_json(
        RESTART_REQUEST_FILE,
        {
            "action":
                "restart",

            "request_id":
                request_id,

            "restart_id":
                restart_id,

            "revision":
                revision,

            "version":
                version,

            "created_at":
                now_iso(),
        },
    )

    return restart_id


def clear_restart_handshake(
    restart_id: str,
) -> None:
    request = read_json(
        RESTART_REQUEST_FILE
    )

    if (
        request.get(
            "restart_id"
        )
        == restart_id
    ):
        RESTART_REQUEST_FILE.unlink(
            missing_ok=True
        )

    ack = read_json(
        RESTART_ACK_FILE
    )

    if (
        ack.get(
            "restart_id"
        )
        == restart_id
    ):
        RESTART_ACK_FILE.unlink(
            missing_ok=True
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
