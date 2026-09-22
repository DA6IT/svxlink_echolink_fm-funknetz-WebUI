from __future__ import annotations

import json
import os
import subprocess

from pathlib import Path
from typing import Any

from .update_config import (
    CHANGELOG_FILE,
    INSTALL_DIR,
    REV_RE,
    UPDATE_BRANCH,
    UPDATE_REMOTE,
    VERSION_FILE,
    WORKER_STATUS_FILE,
)


def run(
    args: list[str],
    *,
    timeout: int = 12,
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


def git(
    *args: str,
    timeout: int = 12,
) -> str:
    try:
        result = run(
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

    return result.stdout.strip()


def read_text(
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


def current_revision() -> str:
    return git(
        "rev-parse",
        "HEAD",
    )


def current_branch() -> str:
    return (
        git(
            "branch",
            "--show-current",
        )
        or "detached"
    )


def working_tree_dirty() -> bool:
    return bool(
        git(
            "status",
            "--porcelain",
        )
    )


def remote_revision() -> str:
    try:
        result = run(
            [
                "git",
                "ls-remote",
                UPDATE_REMOTE,
                f"refs/heads/{UPDATE_BRANCH}",
            ],
            timeout=20,
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return ""

    if result.returncode != 0:
        return ""

    rows = [
        line.split()
        for line
        in result.stdout.splitlines()
        if line.strip()
    ]

    if not rows:
        return ""

    revision = (
        rows[0][0]
        .strip()
        .lower()
    )

    return (
        revision
        if REV_RE.fullmatch(
            revision
        )
        else ""
    )


def commit_known(
    revision: str,
) -> bool:
    if not REV_RE.fullmatch(
        revision or ""
    ):
        return False

    try:
        result = run(
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


def is_ancestor(
    older: str,
    newer: str,
) -> bool:
    if (
        not older
        or not newer
    ):
        return False

    try:
        result = run(
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


def relation(
    current: str,
    target: str,
) -> str:
    if not target:
        return "unavailable"

    if current == target:
        return "current"

    if commit_known(
        target
    ):
        if is_ancestor(
            current,
            target,
        ):
            return "update_available"

        if is_ancestor(
            target,
            current,
        ):
            return "local_ahead"

        return "diverged"

    return "remote_new"


def worker_status() -> dict[str, Any]:
    try:
        data = json.loads(
            WORKER_STATUS_FILE
            .read_text(
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


def target_text(
    revision: str,
    path: str,
) -> str:
    if not commit_known(
        revision
    ):
        return ""

    return git(
        "show",
        f"{revision}:{path}",
        timeout=10,
    )


def installed_version() -> str:
    return read_text(
        VERSION_FILE,
        "unknown",
    )


def installed_changelog() -> str:
    return read_text(
        CHANGELOG_FILE,
        "",
    )
