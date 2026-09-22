from __future__ import annotations

from pathlib import Path


def build_test_environment(
    source: Path,
    job_dir: Path,
) -> dict[str, str]:
    """
    Build an isolated environment for updater validation.

    Staged tests must never write to or depend on the live
    SvxLink/WebUI runtime state.
    """

    state_dir = (
        job_dir
        / "test-state"
    )

    log_dir = (
        state_dir
        / "logs"
    )

    state_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return {
        "PYTHONPATH":
            str(
                source
                / "backend"
            ),

        "SVXLINK_ACTIVITY_DB":
            str(
                state_dir
                / "activity.db"
            ),

        "SVXLINK_CONFIG_PATH":
            str(
                state_dir
                / "svxlink.conf"
            ),

        "SVXLINK_NODE_INFO_PATH":
            str(
                state_dir
                / "node_info.json"
            ),

        "SVXLINK_LOG_PATH":
            str(
                log_dir
            ),

        "SVXLINK_PID_PATH":
            str(
                state_dir
                / "svxlink.pid"
            ),

        "SVXLINK_STATE_PTY_PATH":
            str(
                state_dir
                / "state.jsonl"
            ),

        "TG_CONTROL_PTY":
            str(
                state_dir
                / "simplex_ctrl"
            ),

        # No active production integrations during staged tests.
        "FM_FUNKNETZ_MQTT_ENABLED":
            "false",

        "SVXLINK_STATE_PTY_ENABLED":
            "false",

        "SVXLINK_LOCAL_EVENT_INPUT_ENABLED":
            "false",

        "TG_CONTROL_ENABLED":
            "false",

        # A staged test must never terminate the live backend.
        "SVXLINK_WEBUI_RESTART_WATCHER_ENABLED":
            "false",
    }
