from __future__ import annotations

import getpass
import json
import os
import time
from datetime import datetime
from pathlib import Path


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

STATUS_FILE = Path(
    os.getenv(
        "SVXLINK_WEBUI_UPDATE_STATUS_FILE",
        "/var/lib/svxlink-webui-update/worker-status.json",
    )
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


def snapshot() -> dict:

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

        "user":
            getpass.getuser(),

        "permissions":
            permissions,

        "ready":
            all(
                permissions.values()
            ),

        "updated_at":
            datetime.now()
            .astimezone()
            .isoformat(),
    }


def write_status() -> None:

    STATUS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = STATUS_FILE.with_suffix(
        ".tmp"
    )

    tmp.write_text(
        json.dumps(
            snapshot(),
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

    tmp.replace(
        STATUS_FILE
    )


def main() -> None:

    os.umask(
        0o027
    )

    while True:
        write_status()
        time.sleep(5)


if __name__ == "__main__":
    main()
