"""One-way SvxLink STATE_PTY to normalized JSONL collector.

This module intentionally has no subprocess, shell, or output-to-PTY code.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import select
import stat
import tempfile
from collections import deque
from pathlib import Path
from typing import Any

MAX_LINE_BYTES = 8192
DEFAULT_HISTORY = 200


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    return None


def _bool_or_array(value: Any) -> bool | list[bool] | None:
    scalar = _bool(value)
    if scalar is not None:
        return scalar
    if isinstance(value, list) and all(_bool(item) is not None for item in value):
        return [_bool(item) for item in value]  # type: ignore[misc]
    return None


def _number_or_array(value: Any) -> int | float | list[int | float] | None:
    def valid(item: Any) -> bool:
        return isinstance(item, (int, float)) and not isinstance(item, bool)

    if valid(value):
        return value
    if isinstance(value, list) and all(valid(item) for item in value):
        return value
    return None


def parse_state_pty_line(line: str) -> dict[str, Any] | None:
    """Parse one documented ``<time> Tx:state|Rx:state <JSON>`` PTY line.

    Unknown contexts, malformed JSON, and fields outside the narrow telemetry
    schema are ignored.  The returned value is safe to expose through JSONL.
    """
    if not line or len(line.encode("utf-8", errors="ignore")) > MAX_LINE_BYTES:
        return None
    try:
        timestamp, event, raw_payload = line.rstrip("\r\n").split(maxsplit=2)
        payload = json.loads(raw_payload)
    except (ValueError, json.JSONDecodeError):
        return None
    if event not in {"Tx:state", "Rx:state"} or not isinstance(payload, dict):
        return None

    normalized: dict[str, Any] = {"event": event, "timestamp": timestamp}
    if event == "Tx:state":
        state = _bool(payload.get("transmit", payload.get("state")))
        if state is None:
            return None
        normalized.update({"kind": "tx", "state": state})
        return normalized

    sql_open = _bool_or_array(payload.get("sql_open"))
    active = _bool_or_array(payload.get("active"))
    siglev = _number_or_array(payload.get("siglev"))
    if sql_open is None and active is None and siglev is None:
        return None
    normalized["kind"] = "rx"
    # ``state`` is the primary UI indicator; prefer sql_open over active.
    normalized["state"] = sql_open if sql_open is not None else active
    if sql_open is not None:
        normalized["sql_open"] = sql_open
    if active is not None:
        normalized["active"] = active
    if siglev is not None:
        normalized["siglev"] = siglev
    return normalized


def write_snapshot(output_path: Path, events: list[dict[str, Any]]) -> None:
    """Atomically replace a private JSONL snapshot; never append raw PTY data."""
    output_path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    payload = "".join(json.dumps(event, separators=(",", ":"), allow_nan=False) + "\n" for event in events)
    fd, temporary_name = tempfile.mkstemp(prefix=".state.", dir=output_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.chmod(temporary_name, 0o640)
        os.replace(temporary_name, output_path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def collect(input_path: Path, output_path: Path, history: int = DEFAULT_HISTORY) -> None:
    """Read a STATE_PTY until it closes, then fail for systemd to restart us."""
    if history < 1:
        raise ValueError("history must be positive")
    mode = input_path.stat().st_mode
    if not stat.S_ISCHR(mode) and not stat.S_ISFIFO(mode):
        raise ValueError("STATE_PTY input must be a character device or FIFO")
    events: deque[dict[str, Any]] = deque(maxlen=history)
    with input_path.open("r", encoding="utf-8", errors="replace") as source:
        while True:
            readable, _, _ = select.select([source], [], [], 30)
            if not readable:
                continue
            line = source.readline(MAX_LINE_BYTES + 1)
            if not line:
                raise OSError("STATE_PTY closed")
            event = parse_state_pty_line(line)
            if event is not None:
                events.append(event)
                write_snapshot(output_path, list(events))


def main() -> None:
    parser = argparse.ArgumentParser(description="Read SvxLink STATE_PTY and write normalized JSONL")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--history", type=int, default=DEFAULT_HISTORY)
    args = parser.parse_args()
    try:
        collect(args.input, args.output, args.history)
    except (OSError, ValueError) as error:
        logging.error("STATE_PTY collector stopped: %s", error)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()