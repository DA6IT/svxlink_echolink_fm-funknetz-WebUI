from __future__ import annotations

import os
import shutil

from pathlib import Path
from typing import Any

from .update_worker_common import (
    BACKUP_DIR,
    INSTALL_DIR,
    JOBS_DIR,
    REQUEST_FILE,
    VENV_LINK,
    append_log,
    atomic_json,
    git,
    now_iso,
    phase,
    read_json,
    write_status,
)

from .update_worker_deploy import (
    activate_venv,
    clear_restart_handshake,
    deploy_frontend,
    restart_backend,
    wait_health,
)

from .update_worker_prepare import (
    build_frontend,
    build_runtime,
    fetch_target,
    manifest,
    remove_worktree,
    stage_source,
    test_backend,
    validate_request,
)


def process(
    data: dict[str, Any],
) -> bool:
    (
        request_id,
        action,
        expected,
        target,
    ) = validate_request(
        data
    )

    job_dir = (
        JOBS_DIR
        / request_id
    )

    job_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    log = (
        job_dir
        / "update.log"
    )

    job: dict[str, Any] = {
        "id":
            request_id,
        "action":
            action,
        "state":
            "validating",
        "progress":
            2,
        "message":
            "Update-Anforderung "
            "wird geprüft.",
        "started_at":
            now_iso(),
        "updated_at":
            now_iso(),
        "from_revision":
            expected,
        "target_revision":
            target,
        "target_version":
            "",
        "error":
            "",
    }

    source: Path | None = None
    activation_started = False
    previous_venv = ""
    previous_version = ""
    frontend_backup: Path | None = None

    write_status(
        job,
        log,
    )

    try:
        if (
            git(
                "rev-parse",
                "HEAD",
                log=log,
            ).lower()
            != expected
        ):
            raise RuntimeError(
                "Lokaler Stand hat "
                "sich geändert."
            )

        if git(
            "status",
            "--porcelain",
            log=log,
        ):
            raise RuntimeError(
                "Git-Checkout enthält "
                "lokale Änderungen."
            )

        phase(
            job,
            "fetching",
            8,
            "Zielrevision wird geladen.",
            log,
        )

        fetch_target(
            target,
            log,
        )

        if target != expected:
            git(
                "merge-base",
                "--is-ancestor",
                expected,
                target,
                log=log,
            )

        phase(
            job,
            "staging",
            15,
            "Update wird in "
            "Staging vorbereitet.",
            log,
        )

        source = stage_source(
            job_dir,
            target,
            log,
        )

        update_manifest = manifest(
            source
        )

        version = (
            source
            / "VERSION"
        ).read_text(
            encoding="utf-8",
        ).strip()

        if not version:
            raise RuntimeError(
                "Zielversion ist leer."
            )

        job[
            "target_version"
        ] = version

        job[
            "manifest"
        ] = {
            "schema":
                update_manifest
                .get("schema"),
            "system_migration_required":
                False,
        }

        phase(
            job,
            "security",
            28,
            "Backend-Security-Checks "
            "und Tests laufen.",
            log,
        )

        test_backend(
            source,
            job_dir,
            log,
        )

        shutil.rmtree(
            job_dir
            / "test-venv",
            ignore_errors=True,
        )

        phase(
            job,
            "building",
            52,
            "Frontend wird geprüft "
            "und gebaut.",
            log,
        )

        dist = build_frontend(
            source,
            log,
        )

        phase(
            job,
            "runtime",
            68,
            "Neue Python-Runtime "
            "wird vorbereitet.",
            log,
        )

        runtime = build_runtime(
            source,
            target,
            log,
        )

        if action == "prepare":
            phase(
                job,
                "prepared",
                100,
                "Update wurde vollständig "
                "geprüft und vorbereitet.",
                log,
            )

            job[
                "finished_at"
            ] = now_iso()

            write_status(
                job,
                log,
            )

            remove_worktree(
                source,
                log,
            )

            shutil.rmtree(
                runtime,
                ignore_errors=True,
            )

            return False

        previous_version = (
            INSTALL_DIR
            / "VERSION"
        ).read_text(
            encoding="utf-8",
        ).strip()

        if not VENV_LINK.is_symlink():
            raise RuntimeError(
                ".venv-current ist "
                "kein Symlink."
            )

        previous_venv = os.readlink(
            VENV_LINK
        )

        phase(
            job,
            "backup",
            74,
            "Frontend-Backup "
            "wird erstellt.",
            log,
        )

        frontend_backup = (
            BACKUP_DIR
            / request_id
            / "frontend"
        )

        frontend_backup.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.rmtree(
            frontend_backup,
            ignore_errors=True,
        )

        shutil.copytree(
            (
                Path(
                    "/var/www/new.shart"
                )
            ),
            frontend_backup,
            symlinks=True,
        )

        atomic_json(
            BACKUP_DIR
            / request_id
            / "metadata.json",
            {
                "revision":
                    expected,
                "version":
                    previous_version,
                "venv_target":
                    previous_venv,
                "created_at":
                    now_iso(),
            },
        )

        phase(
            job,
            "activating",
            82,
            "Neue Revision "
            "wird aktiviert.",
            log,
        )

        activation_started = True

        git(
            "reset",
            "--hard",
            target,
            log=log,
            timeout=120,
        )

        activate_venv(
            runtime
        )

        deploy_frontend(
            dist
        )

        phase(
            job,
            "restarting",
            90,
            "Backend wird kontrolliert "
            "neu gestartet.",
            log,
        )

        restart_id = restart_backend(
            request_id,
            target,
            version,
        )

        phase(
            job,
            "healthcheck",
            95,
            "Healthcheck der neuen "
            "Version läuft.",
            log,
        )

        if not wait_health(
            version
        ):
            raise RuntimeError(
                "Healthcheck der neuen "
                "Version fehlgeschlagen."
            )

        clear_restart_handshake(
            restart_id
        )

        phase(
            job,
            "completed",
            100,
            "Update erfolgreich "
            "installiert.",
            log,
        )

        job[
            "finished_at"
        ] = now_iso()

        write_status(
            job,
            log,
        )

        remove_worktree(
            source,
            log,
        )

        return True

    except Exception as exc:
        shutil.rmtree(
            job_dir
            / "test-venv",
            ignore_errors=True,
        )

        error = str(
            exc
        )

        append_log(
            log,
            "FEHLER: "
            + error,
        )

        if (
            activation_started
            and frontend_backup
            is not None
        ):
            try:
                phase(
                    job,
                    "rollback",
                    97,
                    "Update fehlgeschlagen; "
                    "Rollback läuft.",
                    log,
                )

                git(
                    "reset",
                    "--hard",
                    expected,
                    log=log,
                    timeout=120,
                )

                if previous_venv:
                    activate_venv(
                        Path(
                            previous_venv
                        )
                    )

                deploy_frontend(
                    frontend_backup
                )

                rollback_restart_id = (
                    restart_backend(
                        request_id,
                        expected,
                        previous_version,
                    )
                )

                job[
                    "rollback_ok"
                ] = (
                    wait_health(
                        previous_version
                    )
                    if previous_version
                    else False
                )

                if job[
                    "rollback_ok"
                ]:
                    clear_restart_handshake(
                        rollback_restart_id
                    )

            except Exception as rollback_exc:
                job[
                    "rollback_ok"
                ] = False

                job[
                    "rollback_error"
                ] = str(
                    rollback_exc
                )

        job.update(
            {
                "state":
                    "failed",
                "progress":
                    100,
                "message":
                    "Update fehlgeschlagen.",
                "error":
                    error,
                "finished_at":
                    now_iso(),
                "updated_at":
                    now_iso(),
            }
        )

        write_status(
            job,
            log,
        )

        if source is not None:
            try:
                remove_worktree(
                    source,
                    log,
                )
            except Exception:
                pass

        return activation_started


def claim() -> dict[str, Any]:
    if not REQUEST_FILE.is_file():
        return {}

    processing = (
        REQUEST_FILE.parent
        / (
            "request.processing."
            f"{os.getpid()}.json"
        )
    )

    try:
        os.replace(
            REQUEST_FILE,
            processing,
        )
    except OSError:
        return {}

    data = read_json(
        processing
    )

    processing.unlink(
        missing_ok=True
    )

    return data
