from __future__ import annotations

import os
import re

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

WORKER_STATUS_FILE = (
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

REV_RE = re.compile(
    r"^[0-9a-f]{40}$"
)
