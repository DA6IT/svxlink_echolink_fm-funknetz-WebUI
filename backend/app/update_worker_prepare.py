from __future__ import annotations

import re
import shutil

from pathlib import Path
from typing import Any

from .update_worker_testenv import (
    build_test_environment,
)

from .update_worker_common import (
    BRANCH_RE,
    INSTALL_DIR,
    REV_RE,
    REQ_RE,
    UPDATE_BRANCH,
    UPDATE_ENABLED,
    UPDATE_REMOTE,
    UPDATER_PROTOCOL,
    VENV_DIR,
    git,
    read_json,
    run,
)


def validate_request(
    data: dict[str, Any],
) -> tuple[str, str, str, str]:
    if not UPDATE_ENABLED:
        raise RuntimeError(
            "Update-Worker ist "
            "administrativ deaktiviert."
        )

    request_id = str(
        data.get("id", "")
    ).lower()

    action = str(
        data.get("action", "")
    ).lower()

    expected = str(
        data.get(
            "expected_revision",
            "",
        )
    ).lower()

    target = str(
        data.get(
            "target_revision",
            "",
        )
    ).lower()

    if not REQ_RE.fullmatch(
        request_id
    ):
        raise RuntimeError(
            "Ungültige Request-ID."
        )

    if action not in {
        "prepare",
        "install",
    }:
        raise RuntimeError(
            "Ungültige Update-Aktion."
        )

    if (
        not REV_RE.fullmatch(
            expected
        )
        or not REV_RE.fullmatch(
            target
        )
    ):
        raise RuntimeError(
            "Ungültige Revision."
        )

    return (
        request_id,
        action,
        expected,
        target,
    )


def remote_revision(
    log: Path,
) -> str:
    if not BRANCH_RE.fullmatch(
        UPDATE_BRANCH
    ):
        raise RuntimeError(
            "Ungültiger Update-Branch."
        )

    result = run(
        [
            "git",
            "ls-remote",
            UPDATE_REMOTE,
            f"refs/heads/{UPDATE_BRANCH}",
        ],
        cwd=INSTALL_DIR,
        log=log,
        timeout=30,
    )

    rows = [
        line.split()
        for line
        in result.stdout.splitlines()
        if line.strip()
    ]

    if not rows:
        raise RuntimeError(
            "Remote-Revision "
            "nicht verfügbar."
        )

    revision = (
        rows[0][0]
        .lower()
    )

    if not REV_RE.fullmatch(
        revision
    ):
        raise RuntimeError(
            "Ungültige Remote-Revision."
        )

    return revision


def fetch_target(
    target: str,
    log: Path,
) -> None:
    if remote_revision(
        log
    ) != target:
        raise RuntimeError(
            "Zielrevision hat "
            "sich geändert."
        )

    ref = (
        "refs/remotes/"
        "svxlink-webui-updater/"
        + UPDATE_BRANCH
    )

    git(
        "fetch",
        "--quiet",
        "--no-tags",
        UPDATE_REMOTE,
        (
            f"+refs/heads/"
            f"{UPDATE_BRANCH}:"
            f"{ref}"
        ),
        log=log,
        timeout=180,
    )

    fetched = (
        git(
            "rev-parse",
            ref,
            log=log,
        )
        .lower()
    )

    if fetched != target:
        raise RuntimeError(
            "Fetch-Ergebnis stimmt "
            "nicht mit Zielrevision "
            "überein."
        )


def remove_worktree(
    path: Path,
    log: Path,
) -> None:
    if path.exists():
        try:
            git(
                "worktree",
                "remove",
                "--force",
                str(path),
                log=log,
            )
        except Exception:
            shutil.rmtree(
                path,
                ignore_errors=True,
            )

    try:
        git(
            "worktree",
            "prune",
            log=log,
        )
    except Exception:
        pass


def stage_source(
    job_dir: Path,
    target: str,
    log: Path,
) -> Path:
    source = (
        job_dir
        / "source"
    )

    remove_worktree(
        source,
        log,
    )

    git(
        "worktree",
        "add",
        "--detach",
        "--force",
        str(source),
        target,
        log=log,
        timeout=120,
    )

    return source


def manifest(
    source: Path,
) -> dict[str, Any]:
    data = read_json(
        source
        / "UPDATE.json"
    )

    if (
        not data
        or int(
            data.get(
                "schema",
                0,
            )
        )
        != 1
    ):
        raise RuntimeError(
            "UPDATE.json fehlt "
            "oder ist ungültig."
        )

    if (
        int(
            data.get(
                "minimum_updater_protocol",
                0,
            )
        )
        > UPDATER_PROTOCOL
    ):
        raise RuntimeError(
            "Update benötigt "
            "neueren Updater."
        )

    if bool(
        data.get(
            "system_migration_required",
            False,
        )
    ):
        raise RuntimeError(
            "Update benötigt "
            "administrative "
            "Systemmigration."
        )

    return data


def test_backend(
    source: Path,
    job_dir: Path,
    log: Path,
) -> None:
    venv = (
        job_dir
        / "test-venv"
    )

    shutil.rmtree(
        venv,
        ignore_errors=True,
    )

    run(
        [
            "/usr/bin/python3",
            "-m",
            "venv",
            str(venv),
        ],
        cwd=source,
        log=log,
        timeout=120,
    )

    pip = (
        venv
        / "bin"
        / "pip"
    )

    run(
        [
            str(pip),
            "install",
            "-q",
            "--upgrade",
            "pip",
        ],
        cwd=source,
        log=log,
        timeout=180,
    )

    run(
        [
            str(pip),
            "install",
            "-q",
            "-r",
            "backend/"
            "requirements-test.txt",
        ],
        cwd=source,
        log=log,
        timeout=300,
    )

    run(
        [
            str(pip),
            "install",
            "-q",
            "bandit",
            "pip-audit",
        ],
        cwd=source,
        log=log,
        timeout=300,
    )

    run(
        [
            str(
                venv
                / "bin"
                / "bandit"
            ),
            "-q",
            "-r",
            "backend/app",
            "-ll",
        ],
        cwd=source,
        log=log,
        timeout=180,
    )

    for req in (
        "backend/requirements.txt",
        "backend/"
        "requirements-test.txt",
    ):
        run(
            [
                str(
                    venv
                    / "bin"
                    / "pip-audit"
                ),
                "-r",
                req,
            ],
            cwd=source,
            log=log,
            timeout=180,
        )

    run(
        [
            str(
                venv
                / "bin"
                / "pytest"
            ),
            "-q",
            "backend/tests",
        ],
        cwd=source,
        log=log,
        timeout=300,
        extra_env=
            build_test_environment(
                source,
                job_dir,
            ),
    )


def build_frontend(
    source: Path,
    log: Path,
) -> Path:
    frontend = (
        source
        / "frontend"
    )

    commands = (
        (["npm", "ci"], 600),
        (
            [
                "npm",
                "audit",
                "--audit-level=moderate",
            ],
            300,
        ),
        (
            [
                "npm",
                "run",
                "lint",
            ],
            300,
        ),
        (
            [
                "npm",
                "run",
                "build",
            ],
            600,
        ),
    )

    for args, timeout in commands:
        run(
            args,
            cwd=frontend,
            log=log,
            timeout=timeout,
        )

    dist = (
        frontend
        / "dist"
    )

    if not (
        dist
        / "index.html"
    ).is_file():
        raise RuntimeError(
            "Frontend-Build ungültig."
        )

    return dist


def build_runtime(
    source: Path,
    target: str,
    log: Path,
) -> Path:
    version = (
        source
        / "VERSION"
    ).read_text(
        encoding="utf-8",
    ).strip()

    safe_version = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        version,
    )[:64]

    runtime = (
        VENV_DIR
        / (
            f"{safe_version}-"
            f"{target[:12]}"
        )
    )

    shutil.rmtree(
        runtime,
        ignore_errors=True,
    )

    run(
        [
            "/usr/bin/python3",
            "-m",
            "venv",
            str(runtime),
        ],
        cwd=source,
        log=log,
        timeout=120,
    )

    pip = (
        runtime
        / "bin"
        / "pip"
    )

    run(
        [
            str(pip),
            "install",
            "-q",
            "--upgrade",
            "pip",
        ],
        cwd=source,
        log=log,
        timeout=180,
    )

    run(
        [
            str(pip),
            "install",
            "-q",
            "-r",
            "backend/"
            "requirements.txt",
        ],
        cwd=source,
        log=log,
        timeout=300,
    )

    return runtime
