from __future__ import annotations

import getpass

from typing import Any

from .update_config import (
    UPDATE_BRANCH,
    UPDATE_ENABLED,
    UPDATE_REMOTE,
)

from .update_repository import (
    current_branch,
    current_revision,
    installed_changelog,
    installed_version,
    relation,
    remote_revision,
    target_text,
    worker_status,
    working_tree_dirty,
)


def update_status() -> dict[str, Any]:
    current = (
        current_revision()
    )

    target = (
        remote_revision()
    )

    current_relation = relation(
        current,
        target,
    )

    worker = (
        worker_status()
    )

    raw_permissions = (
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
        key:
            bool(
                raw_permissions.get(
                    key,
                    False,
                )
            )
        for key in (
            "application",
            "git",
            "update_data",
            "frontend",
        )
    }

    rootless_ready = (
        bool(
            worker.get(
                "available",
                False,
            )
        )
        and all(
            permissions.values()
        )
    )

    current_version = (
        installed_version()
    )

    target_version = (
        target_text(
            target,
            "VERSION",
        ).strip()
    )

    target_changelog = (
        target_text(
            target,
            "CHANGELOG.md",
        ).strip()
    )

    local_changelog = (
        installed_changelog()
    )

    branch = (
        current_branch()
    )

    available = (
        current_relation
        in {
            "update_available",
            "remote_new",
        }
    )

    branch_ok = (
        branch
        in {
            UPDATE_BRANCH,
            "detached",
        }
    )

    job = (
        worker.get(
            "job"
        )
    )

    if not isinstance(
        job,
        dict,
    ):
        job = None

    active_job = bool(
        job
        and job.get(
            "state"
        )
        not in {
            "completed",
            "prepared",
            "failed",
        }
    )

    dirty = (
        working_tree_dirty()
    )

    can_install = bool(
        UPDATE_ENABLED
        and rootless_ready
        and available
        and not dirty
        and branch_ok
        and not active_job
    )

    messages = {
        "current":
            "Der installierte Git-Stand "
            "entspricht dem Update-Kanal.",

        "update_available":
            "Eine neuere Revision ist "
            "im Update-Kanal verfügbar.",

        "remote_new":
            "Der Update-Kanal enthält "
            "eine neue Revision.",

        "local_ahead":
            "Der lokale Entwicklungsstand "
            "ist neuer als der Update-Kanal.",

        "diverged":
            "Lokaler Stand und Update-Kanal "
            "haben sich auseinanderentwickelt.",

        "unavailable":
            "Der Update-Kanal ist momentan "
            "nicht erreichbar.",
    }

    return {
        "version":
            current_version,

        "revision":
            current,

        "revision_short":
            current[:8]
            if current
            else "",

        "branch":
            branch,

        "dirty":
            dirty,

        "channel": {
            "name":
                UPDATE_BRANCH,

            "remote":
                UPDATE_REMOTE,

            "revision":
                target,

            "revision_short":
                target[:8]
                if target
                else "",

            "version":
                target_version,
        },

        "relation":
            current_relation,

        "available":
            available,

        "enabled":
            UPDATE_ENABLED,

        "can_install":
            can_install,

        "branch_ok":
            branch_ok,

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
            messages.get(
                current_relation,
                messages[
                    "unavailable"
                ],
            ),

        "changelog":
            (
                target_changelog
                or local_changelog
            ),

        "installed_changelog":
            local_changelog,

        "system_migration_required":
            False,

        "job":
            job,
    }
