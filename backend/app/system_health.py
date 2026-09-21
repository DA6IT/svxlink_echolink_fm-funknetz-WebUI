from __future__ import annotations

import configparser
import os
import re
import subprocess
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(
    os.getenv(
        "SVXLINK_CONFIG_PATH",
        "/etc/svxlink/svxlink.conf",
    )
)

SERVICE_NAME = os.getenv(
    "SVXLINK_SERVICE_NAME",
    "svxlink",
)

STATE_COLLECTOR_SERVICE = (
    "svxlink-webui-state-collector.service"
)

CONTROL_PTY = Path(
    os.getenv(
        "TG_CONTROL_PTY",
        "/var/lib/svxlink/control/simplex_ctrl",
    )
)

NORMALIZED_STATE = Path(
    os.getenv(
        "SVXLINK_STATE_PTY_PATH",
        "/run/svxlink-webui/state.jsonl",
    )
)

SHARI_SERIAL_PORT = Path(
    os.getenv(
        "SHARI_SERIAL_PORT",
        "/dev/ttyUSB0",
    )
)


def _exists(
    path: Path,
) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def _config() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(
        interpolation=None,
        strict=False,
    )

    parser.optionxform = str

    if CONFIG_PATH.is_file():
        try:
            parser.read(
                CONFIG_PATH,
                encoding="utf-8",
            )
        except (
            OSError,
            configparser.Error,
        ):
            pass

    return parser


def _systemd_unit(
    unit: str,
    label: str,
) -> dict[str, Any]:

    try:
        result = subprocess.run(
            [
                "systemctl",
                "show",
                unit,
                "-p",
                "LoadState",
                "-p",
                "ActiveState",
                "-p",
                "SubState",
            ],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )

        fields = dict(
            line.split("=", 1)
            for line
            in result.stdout.splitlines()
            if "=" in line
        )

        load_state = fields.get(
            "LoadState",
            "",
        )

        active_state = fields.get(
            "ActiveState",
            "",
        )

        substate = fields.get(
            "SubState",
            "",
        )

        loaded = (
            load_state
            not in {
                "",
                "not-found",
                "error",
            }
        )

        active = (
            loaded
            and active_state == "active"
        )

        return {
            "ok": active,
            "status":
                "ok"
                if active
                else "error",
            "label": label,
            "value":
                active_state
                if loaded
                else "nicht installiert",
            "detail":
                substate
                if loaded
                else f"{unit} fehlt",
        }

    except (
        OSError,
        subprocess.SubprocessError,
    ) as exc:

        return {
            "ok": False,
            "status": "error",
            "label": label,
            "value": "unavailable",
            "detail": str(exc),
        }


def _control_pty() -> dict[str, Any]:

    exists = _exists(
        CONTROL_PTY
    )

    writable = (
        exists
        and os.access(
            CONTROL_PTY,
            os.W_OK,
        )
    )

    resolved = ""

    if exists:
        try:
            resolved = str(
                CONTROL_PTY.resolve()
            )
        except OSError:
            resolved = str(
                CONTROL_PTY
            )

    return {
        "ok":
            bool(
                exists
                and writable
            ),
        "status":
            "ok"
            if exists and writable
            else "error",
        "label":
            "Control PTY",
        "value":
            str(CONTROL_PTY)
            if exists
            else "fehlt",
        "detail":
            resolved
            if exists and writable
            else
            "vorhanden, aber nicht beschreibbar"
            if exists
            else
            "Control-PTY nicht vorhanden",
    }


def _state_collector() -> dict[str, Any]:

    result = _systemd_unit(
        STATE_COLLECTOR_SERVICE,
        "State Collector",
    )

    if result["ok"]:
        if _exists(
            NORMALIZED_STATE
        ):
            result["detail"] = (
                "running · "
                "normalisierter State verfügbar"
            )
        else:
            result["detail"] = (
                "running · "
                "wartet auf ersten State-Event"
            )

    return result


def _alsa_target(
    value: str,
) -> tuple[int | None, int | None]:

    value = str(
        value
    ).strip()

    numeric = re.search(
        r"(?:plug)?hw:(\d+),(\d+)",
        value,
        re.I,
    )

    if numeric:
        return (
            int(
                numeric.group(1)
            ),
            int(
                numeric.group(2)
            ),
        )

    named = re.search(
        r"CARD=([^,]+).*?DEV=(\d+)",
        value,
        re.I,
    )

    if not named:
        return (
            None,
            None,
        )

    wanted = (
        named.group(1)
        .strip()
    )

    device = int(
        named.group(2)
    )

    for path in Path(
        "/proc/asound"
    ).glob(
        "card*/id"
    ):
        try:
            card_id = (
                path.read_text()
                .strip()
            )
        except OSError:
            continue

        if card_id != wanted:
            continue

        match = re.search(
            r"card(\d+)",
            str(path),
        )

        if match:
            return (
                int(
                    match.group(1)
                ),
                device,
            )

    return (
        None,
        device,
    )


def _audio(
    parser: configparser.ConfigParser,
    section: str,
    capture: bool,
    label: str,
) -> dict[str, Any]:

    value = ""

    if parser.has_section(
        section
    ):
        value = parser.get(
            section,
            "AUDIO_DEV",
            fallback="",
        ).strip()

    if not value:
        return {
            "ok": False,
            "status": "error",
            "label": label,
            "value":
                "nicht konfiguriert",
            "detail":
                f"{section}.AUDIO_DEV fehlt",
        }

    card, device = (
        _alsa_target(
            value
        )
    )

    if (
        card is None
        or device is None
    ):
        return {
            "ok": False,
            "status": "error",
            "label": label,
            "value": value,
            "detail":
                "ALSA-Gerät konnte nicht "
                "auf eine Soundkarte "
                "aufgelöst werden",
        }

    suffix = (
        "c"
        if capture
        else "p"
    )

    pcm = Path(
        f"/dev/snd/"
        f"pcmC{card}D{device}{suffix}"
    )

    control = Path(
        f"/dev/snd/controlC{card}"
    )

    missing = []

    if not _exists(
        pcm
    ):
        missing.append(
            pcm.name
        )

    if not _exists(
        control
    ):
        missing.append(
            control.name
        )

    ok = not missing

    return {
        "ok": ok,
        "status":
            "ok"
            if ok
            else "error",
        "label": label,
        "value": value,
        "detail":
            (
                f"{pcm.name} + "
                f"{control.name}"
                if ok
                else
                "fehlt: "
                + ", ".join(
                    missing
                )
            ),
    }


def _ptt(
    parser: configparser.ConfigParser,
) -> dict[str, Any]:

    if not parser.has_section(
        "Tx1"
    ):
        return {
            "ok": False,
            "status": "error",
            "label": "PTT",
            "value":
                "nicht konfiguriert",
            "detail":
                "Tx1 fehlt",
        }

    ptt_type = parser.get(
        "Tx1",
        "PTT_TYPE",
        fallback="",
    ).strip()

    hid_device = parser.get(
        "Tx1",
        "HID_DEVICE",
        fallback="",
    ).strip()

    if (
        ptt_type.upper()
        == "HIDRAW"
        or hid_device
    ):
        path = Path(
            hid_device
            or "/dev/hidraw0"
        )

        available = _exists(
            path
        )

        return {
            "ok": available,
            "status":
                "ok"
                if available
                else "error",
            "label": "PTT",
            "value":
                ptt_type
                or "HIDRAW",
            "detail":
                str(path)
                if available
                else f"{path} fehlt",
        }

    return {
        "ok": bool(
            ptt_type
        ),
        "status":
            "ok"
            if ptt_type
            else "warning",
        "label": "PTT",
        "value":
            ptt_type
            or "unbekannt",
        "detail":
            "kein HID-PTT konfiguriert",
    }


def _shari_uart() -> dict[str, Any]:

    exists = _exists(
        SHARI_SERIAL_PORT
    )

    usable = (
        exists
        and os.access(
            SHARI_SERIAL_PORT,
            os.R_OK | os.W_OK,
        )
    )

    return {
        "ok": usable,
        "status":
            "ok"
            if usable
            else "error",
        "label":
            "SHARI UART",
        "value":
            str(
                SHARI_SERIAL_PORT
            ),
        "detail":
            "Gerät verfügbar"
            if usable
            else
            "Gerät fehlt oder "
            "WebUI hat keine Berechtigung",
    }


def system_health() -> dict[str, Any]:

    parser = _config()

    service = _systemd_unit(
        SERVICE_NAME,
        "SvxLink",
    )

    collector = (
        _state_collector()
    )

    control = (
        _control_pty()
    )

    simplex_ready = (
        service["ok"]
        and collector["ok"]
        and control["ok"]
    )

    simplex = {
        "ok":
            simplex_ready,
        "status":
            "ok"
            if simplex_ready
            else "error",
        "label":
            "SimplexLogic",
        "value":
            "bereit"
            if simplex_ready
            else "nicht bereit",
        "detail":
            (
                "SvxLink, State-Collector "
                "und Control-PTY bereit"
                if simplex_ready
                else
                "SvxLink, State-Collector "
                "oder Control-PTY fehlerhaft"
            ),
    }

    checks = [
        service,
        simplex,
        collector,
        control,

        _audio(
            parser,
            "Rx1",
            True,
            "RX Audio",
        ),

        _audio(
            parser,
            "Tx1",
            False,
            "TX Audio",
        ),

        _ptt(
            parser
        ),

        _shari_uart(),
    ]

    failed = [
        item
        for item in checks
        if item["status"]
        == "error"
    ]

    warnings = [
        item
        for item in checks
        if item["status"]
        == "warning"
    ]

    return {
        "ok":
            not failed,
        "status":
            "error"
            if failed
            else
            "warning"
            if warnings
            else "ok",
        "checks":
            checks,
    }
