"""Read-only SA818/SA818S hardware detection for the SHARI UI."""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

import serial


SERIAL_PORT = os.getenv(
    "SHARI_SERIAL_PORT",
    "/dev/ttyUSB0",
)

SERIAL_BAUD = int(
    os.getenv(
        "SHARI_SERIAL_BAUD",
        "9600",
    )
)

SERIAL_TIMEOUT = float(
    os.getenv(
        "SHARI_SERIAL_TIMEOUT",
        "0.8",
    )
)


CTCSS = {
    "0001": "67.0 Hz",
    "0002": "71.9 Hz",
    "0003": "74.4 Hz",
    "0004": "77.0 Hz",
    "0005": "79.7 Hz",
    "0006": "82.5 Hz",
    "0007": "85.4 Hz",
    "0008": "88.5 Hz",
    "0009": "91.5 Hz",
    "0010": "94.8 Hz",
    "0011": "97.4 Hz",
    "0012": "100.0 Hz",
    "0013": "103.5 Hz",
    "0014": "107.2 Hz",
    "0015": "110.9 Hz",
    "0016": "114.8 Hz",
    "0017": "118.8 Hz",
    "0018": "123.0 Hz",
    "0019": "127.3 Hz",
    "0020": "131.8 Hz",
    "0021": "136.5 Hz",
    "0022": "141.3 Hz",
    "0023": "146.2 Hz",
    "0024": "151.4 Hz",
    "0025": "156.7 Hz",
    "0026": "162.2 Hz",
    "0027": "167.9 Hz",
    "0028": "173.8 Hz",
    "0029": "179.9 Hz",
    "0030": "186.2 Hz",
    "0031": "192.8 Hz",
    "0032": "203.5 Hz",
    "0033": "210.7 Hz",
    "0034": "218.1 Hz",
    "0035": "225.7 Hz",
    "0036": "233.6 Hz",
    "0037": "241.8 Hz",
    "0038": "250.3 Hz",
}


def _cxcss_label(code: str) -> str:
    code = str(code).strip()

    if code == "0000":
        return "Aus"

    return CTCSS.get(
        code,
        code,
    )


def _command(
    radio: serial.Serial,
    command: str,
) -> str:
    radio.reset_input_buffer()

    radio.write(
        (
            command
            + "\r\n"
        ).encode("ascii")
    )

    radio.flush()

    time.sleep(0.08)

    raw = radio.readline()

    if not raw:
        raise RuntimeError(
            f"Keine Antwort auf {command}"
        )

    return (
        raw.decode(
            "ascii",
            errors="replace",
        )
        .strip()
    )


def _parse_group(
    response: str,
) -> dict[str, Any]:
    if ":" in response:
        payload = response.split(
            ":",
            1,
        )[1]
    elif "=" in response:
        payload = response.split(
            "=",
            1,
        )[1]
    else:
        raise ValueError(
            "Ungültige DMOREADGROUP-Antwort"
        )

    fields = [
        value.strip()
        for value in payload.split(",")
    ]

    if len(fields) != 6:
        raise ValueError(
            "DMOREADGROUP enthält nicht sechs Felder"
        )

    (
        bandwidth,
        tx_frequency,
        rx_frequency,
        tx_cxcss,
        squelch,
        rx_cxcss,
    ) = fields

    if bandwidth == "0":
        bandwidth_khz = 12.5
    elif bandwidth == "1":
        bandwidth_khz = 25.0
    else:
        bandwidth_khz = None

    return {
        "bandwidth_raw": bandwidth,
        "bandwidth_khz": bandwidth_khz,

        "tx_frequency_mhz":
            tx_frequency,

        "rx_frequency_mhz":
            rx_frequency,

        "tx_cxcss_code":
            tx_cxcss,

        "tx_cxcss_label":
            _cxcss_label(
                tx_cxcss
            ),

        "rx_cxcss_code":
            rx_cxcss,

        "rx_cxcss_label":
            _cxcss_label(
                rx_cxcss
            ),

        "squelch":
            int(squelch),
    }


def read_shari_hardware() -> dict[str, Any]:
    base: dict[str, Any] = {
        "available": False,
        "port": SERIAL_PORT,
        "baudrate": SERIAL_BAUD,
        "read_only": True,
        "updated_at":
            datetime.now()
            .astimezone()
            .isoformat(),
    }

    try:
        with serial.Serial(
            port=SERIAL_PORT,
            baudrate=SERIAL_BAUD,
            bytesize=8,
            parity=serial.PARITY_NONE,
            stopbits=1,
            timeout=SERIAL_TIMEOUT,
            write_timeout=SERIAL_TIMEOUT,
        ) as radio:

            connect = _command(
                radio,
                "AT+DMOCONNECT",
            )

            if not connect.startswith(
                "+DMOCONNECT:0"
            ):
                raise RuntimeError(
                    f"SHARI antwortet unerwartet: {connect}"
                )

            version_response = _command(
                radio,
                "AT+VERSION",
            )

            group_response = _command(
                radio,
                "AT+DMOREADGROUP",
            )

        version_raw = (
            version_response
            .split(
                ":",
                1,
            )[1]
            .strip()
            if ":"
            in version_response
            else version_response
        )

        module = version_raw

        firmware = ""

        if "_V" in version_raw:
            module_part, version_part = (
                version_raw.split(
                    "_V",
                    1,
                )
            )

            module = module_part
            firmware = (
                "V"
                + version_part
            )

        group = _parse_group(
            group_response
        )

        return {
            **base,
            **group,

            "available": True,

            "module":
                module,

            "firmware":
                firmware
                or version_raw,

            "firmware_raw":
                version_raw,

            "handshake":
                connect,

            "source":
                "SA818 UART",

            "commands": [
                "AT+DMOCONNECT",
                "AT+VERSION",
                "AT+DMOREADGROUP",
            ],
        }

    except Exception as exc:
        return {
            **base,

            "reason":
                str(exc),
        }
