"""Read-only SvxLink status API with an intentionally small data allowlist."""
from __future__ import annotations

import configparser
import json
import os
import platform
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

VERSION = "0.2.0"
DEMO = os.getenv("SVXLINK_WEBUI_DEMO", "false").lower() in {"1", "true", "yes"}
CONFIG_PATH = Path(os.getenv("SVXLINK_CONFIG_PATH", "/etc/svxlink/svxlink.conf"))
NODE_INFO_PATH = Path(os.getenv("SVXLINK_NODE_INFO_PATH", "/etc/svxlink/node_info.json"))
LOG_PATH = Path(os.getenv("SVXLINK_LOG_PATH", "/var/log/svxlink"))
PID_PATH = Path(os.getenv("SVXLINK_PID_PATH", "/run/svxlink.pid"))
SERVICE_NAME = os.getenv("SVXLINK_SERVICE_NAME", "svxlink")

app = FastAPI(title="SvxLink WebUI", version=VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

NODE_KEYS = {"Location", "Locator", "LAT", "LONG", "TXFREQ", "RXFREQ", "Mode", "Type", "nodeLocation", "Verbund", "DefaultTG", "Callsign", "CALLSIGN"}
CONFIG_KEYS = {"LOGICS", "DEFAULT_TG", "CALLSIGN", "NODE_INFO_FILE", "LINKS", "SERVICES"}
JOIN_RE = re.compile(r"(?P<time>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+.*?Node (?P<event>joined|left):\s*(?P<callsign>[A-Za-z0-9/_-]+)", re.I)


def parse_ini(path: Path) -> dict[str, dict[str, str]]:
    """Return only explicitly allowlisted operational values, never whole config."""
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    if not path.is_file():
        return {}
    try:
        parser.read(path, encoding="utf-8")
    except (OSError, configparser.Error):
        return {}
    return {section: {key: value for key, value in parser.items(section) if key.upper() in CONFIG_KEYS}
            for section in parser.sections() if any(key.upper() in CONFIG_KEYS for key in parser[section])}


def read_node_info(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return {key: value[key] for key in NODE_KEYS if key in value} if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _pid() -> int | None:
    try:
        value = int(PID_PATH.read_text().strip())
        return value if value > 0 else None
    except (OSError, ValueError):
        return None


def service_status() -> dict[str, Any]:
    if DEMO:
        return {"running": True, "status": "online", "service": SERVICE_NAME, "pid": 1234, "substate": "running"}
    try:
        result = subprocess.run(["systemctl", "show", SERVICE_NAME, "-p", "ActiveState", "-p", "SubState"],
                                capture_output=True, text=True, timeout=2, check=False)
        fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        active = fields.get("ActiveState") == "active"
        return {"running": active, "status": "online" if active else fields.get("ActiveState", "unavailable"),
                "service": SERVICE_NAME, "pid": _pid(), "substate": fields.get("SubState", "unknown")}
    except (OSError, subprocess.SubprocessError):
        return {"running": False, "status": "unavailable", "service": SERVICE_NAME, "pid": _pid(), "substate": "unknown"}


def log_files() -> list[Path]:
    if LOG_PATH.is_file():
        return [LOG_PATH]
    if LOG_PATH.is_dir():
        return sorted((p for p in LOG_PATH.iterdir() if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    return []


def reflector_activity(limit: int = 100) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for path in log_files():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        except OSError:
            continue
        for line in lines:
            match = JOIN_RE.search(line)
            if match:
                stamp = match.group("time").replace(" ", "T")
                events.append({"event": match.group("event").lower(), "callsign": match.group("callsign"), "timestamp": stamp})
    events = events[-limit:]
    return {"events": events, "count": len(events), "last_heard": events[-1] if events else None, "available": bool(log_files())}


def dashboard() -> dict[str, Any]:
    node = read_node_info(NODE_INFO_PATH)
    activity = reflector_activity()
    config = parse_ini(CONFIG_PATH)
    return {"node": node, "svxlink": service_status(), "reflector": activity,
            "config": config, "demo": DEMO, "version": VERSION, "updated_at": datetime.now().astimezone().isoformat()}


@app.get("/api/status")
def status():
    return dashboard()


@app.get("/api/svxlink/status")
def svxlink_status():
    return service_status()


@app.get("/api/system")
def system():
    return {"hostname": platform.node(), "os": platform.platform(), "python": platform.python_version(), "uptime": int(time.monotonic()), "version": VERSION}


@app.get("/api/node-info")
def node_info():
    return {"data": read_node_info(NODE_INFO_PATH), "available": NODE_INFO_PATH.is_file()}


@app.get("/api/last-heard")
def last_heard():
    return reflector_activity()["events"]


@app.get("/api/talkgroups")
def talkgroups():
    config = parse_ini(CONFIG_PATH)
    values = [value for section in config.values() for key, value in section.items() if key.upper() == "DEFAULT_TG"]
    return {"active": values[0] if values else None, "available": bool(values)}


@app.get("/api/svxlink/logs")
def logs():
    activity = reflector_activity()
    return {"events": activity["events"], "count": activity["count"], "available": activity["available"]}


@app.websocket("/api/ws/live")
async def live(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"event": "node.status", "data": dashboard()})
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        await websocket.close()


@app.get("/health")
def health():
    return {"ok": True, "version": VERSION}
