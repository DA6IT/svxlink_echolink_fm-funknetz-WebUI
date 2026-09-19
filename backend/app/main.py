"""Read-only SvxLink status API with an intentionally small data allowlist."""
from __future__ import annotations

import configparser
import json
import os
import platform
import re
import subprocess
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
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
FM_LIVE_URL = os.getenv("FM_FUNKNETZ_LIVE_URL", "https://dashboard.fm-funknetz.de/data/live.json")
FM_LASTHEARD_URL = os.getenv("FM_FUNKNETZ_LASTHEARD_URL", "https://dashboard.fm-funknetz.de/data/lastheard.json")
# Deployment configuration only; the backend never writes to this public broker.
FM_MQTT_ENABLED = os.getenv("FM_FUNKNETZ_MQTT_ENABLED", "false").lower() in {"1", "true", "yes"}
FM_MQTT_WS_URL = os.getenv("FM_FUNKNETZ_MQTT_WS_URL", "wss://status.thueringen.link/mqtt")
FM_MQTT_TOPICS = ("/server/statethr", "/server/statethr/1", "/server/state/logins")
FM_FEED_ALLOWLIST = {"/data/live.json", "/data/lastheard.json"}
# This is deliberately a deployment setting, not user input.  It is used for
# displaying/validating local TG data even while control remains disabled.
TG_ALLOWLIST = frozenset(
    value for value in (item.strip() for item in os.getenv("SVXLINK_TG_ALLOWLIST", "").split(","))
    if value.isdigit() and value
)
# Optional, strictly read-only JSONL state source. The service never opens a
# command PTY and never writes to this path.
STATE_PTY_PATH = Path(os.getenv("SVXLINK_STATE_PTY_PATH", "/run/svxlink/state.jsonl"))
STATE_PTY_ENABLED = os.getenv("SVXLINK_STATE_PTY_ENABLED", "false").lower() in {"1", "true", "yes"}
LOCAL_EVENT_INPUT_ENABLED = os.getenv("SVXLINK_LOCAL_EVENT_INPUT_ENABLED", "false").lower() in {"1", "true", "yes"}

app = FastAPI(title="SvxLink WebUI", version=VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

NODE_KEYS = {"Location", "Locator", "LAT", "LONG", "TXFREQ", "RXFREQ", "Mode", "Type", "nodeLocation", "Verbund", "DefaultTG", "Callsign", "CALLSIGN"}
CONFIG_KEYS = {"LOGICS", "DEFAULT_TG", "CALLSIGN", "NODE_INFO_FILE", "LINKS", "SERVICES"}
JOIN_RE = re.compile(r"(?P<time>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+.*?Node (?P<event>joined|left):\s*(?P<callsign>[A-Za-z0-9/_-]+)", re.I)
SELECTING_TG_RE = re.compile(
    r"(?P<time>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+.*?"
    r"ReflectorLogic: Selecting TG #(?P<tg>\d+)\s*$",
    re.I,
)


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


def talkgroup_activity(limit: int = 100) -> list[dict[str, str]]:
    """Read confirmed local TG selections; never treats a PTY write as success."""
    selections: list[dict[str, str]] = []
    for path in log_files():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        except OSError:
            continue
        for line in lines:
            match = SELECTING_TG_RE.search(line)
            if match and match.group("tg") in TG_ALLOWLIST:
                selections.append({"talkgroup": match.group("tg"), "timestamp": match.group("time").replace(" ", "T")})
    return selections[-limit:]


def _state_event(value: Any) -> tuple[str, dict[str, Any]] | None:
    """Normalize documented Tx:state/Rx:state JSON without exposing raw input."""
    if not isinstance(value, dict):
        return None
    name = str(value.get("event", value.get("type", ""))).lower().replace("_", ":")
    payload = value.get("data")
    if not isinstance(payload, dict):
        payload = value
    kind = "tx" if name in {"tx:state", "tx", "transmit:state"} else "rx" if name in {"rx:state", "rx", "receive:state"} else ""
    if not kind:
        return None
    state = payload.get("state", payload.get("active", payload.get("value")))
    if isinstance(state, str):
        state = state.lower() in {"1", "true", "on", "active", "open", "squelch"}
    elif not isinstance(state, bool):
        state = None
    result: dict[str, Any] = {"source": "STATE_PTY", "kind": kind, "state": state}
    timestamp = payload.get("timestamp", value.get("timestamp", payload.get("time", value.get("time"))))
    if isinstance(timestamp, str) and len(timestamp) <= 64:
        result["timestamp"] = timestamp
    for key in ("squelch", "siglev"):
        number = payload.get(key)
        if isinstance(number, (int, float)) and not isinstance(number, bool):
            result[key] = number
    return kind, result


def local_rf_telemetry(limit: int = 100) -> dict[str, Any]:
    """Read only the tail of a local JSONL state source; never writes to it."""
    unavailable = {"available": False, "source": "STATE_PTY", "events": [], "tx": None, "rx": None,
                   "reason": "Lokale RF-Telemetrie nicht aktiviert oder nicht verfügbar."}
    if not STATE_PTY_ENABLED or not STATE_PTY_PATH.is_file():
        return unavailable
    events: list[dict[str, Any]] = []
    try:
        for line in STATE_PTY_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            try:
                normalized = _state_event(json.loads(line))
            except json.JSONDecodeError:
                continue
            if normalized:
                events.append(normalized[1])
    except OSError:
        return unavailable
    latest = {event["kind"]: event for event in events}
    return {"available": True, "source": "STATE_PTY", "events": events,
            "tx": latest.get("tx"), "rx": latest.get("rx"),
            "reason": "Read-only lokale SHARI-RF-Telemetrie."}


def normalized_local_events(limit: int = 100) -> dict[str, Any]:
    """Feature-gated future event input; disabled means explicitly unavailable."""
    if not LOCAL_EVENT_INPUT_ENABLED:
        return {"enabled": False, "available": False, "events": [],
                "reason": "Lokale Event-Schnittstelle ist feature-geflaggte und derzeit deaktiviert."}
    telemetry = local_rf_telemetry(limit)
    return {"enabled": True, "available": telemetry["available"], "events": telemetry["events"],
            "reason": telemetry["reason"]}


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _validate_feed_url(url: str) -> None:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != "dashboard.fm-funknetz.de"
            or parsed.username is not None or parsed.password is not None or parsed.port is not None
            or parsed.path not in FM_FEED_ALLOWLIST
            or parsed.query or parsed.fragment):
        raise ValueError("FM-Funknetz feed URL is not an allowlisted HTTPS source")


def _get_json(url: str) -> Any:
    """Fetch a confirmed public feed with one bounded reconnect attempt."""
    _validate_feed_url(url)
    opener = urllib.request.build_opener(_NoRedirectHandler)
    for attempt in range(2):
        try:
            request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "svxlink-webui/0.2"})
            with opener.open(request, timeout=4) as response:
                return json.loads(response.read(512 * 1024).decode("utf-8"))
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt:
                raise
            time.sleep(0.1)
    raise RuntimeError("unreachable")


def fm_funknetz_live() -> dict[str, Any]:
    """Read current FM-Funknetz dashboard telemetry with failure-safe reconnect."""
    try:
        live, heard = _get_json(FM_LIVE_URL), _get_json(FM_LASTHEARD_URL)
        if not isinstance(live, list) or not isinstance(heard, list):
            raise ValueError("feed is not an array")
        return {"available": True, "source": "FM-Funknetz Dashboard-Livedaten",
                "active": live[0] if live else None, "live": live[:100], "last_heard": heard[:100],
                "client_count": None, "updated_at": datetime.now().astimezone().isoformat(),
                "mqtt": {"configured": FM_MQTT_ENABLED, "adapter_active": False, "ws_url": FM_MQTT_WS_URL, "topics": list(FM_MQTT_TOPICS)}}
    except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return {"available": False, "source": "FM-Funknetz Dashboard-Livedaten", "active": None,
                "live": [], "last_heard": [], "client_count": None,
                "reason": "FM-Funknetz-Livedaten momentan nicht erreichbar.",
                "mqtt": {"configured": FM_MQTT_ENABLED, "adapter_active": False, "ws_url": FM_MQTT_WS_URL, "topics": list(FM_MQTT_TOPICS)}}


def dashboard() -> dict[str, Any]:
    node = read_node_info(NODE_INFO_PATH)
    activity = reflector_activity()
    config = parse_ini(CONFIG_PATH)
    return {"node": node, "svxlink": service_status(), "reflector": activity,
            "rf": local_rf_telemetry(), "events": normalized_local_events(),
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
    confirmed = talkgroup_activity()
    external = fm_funknetz_live()
    return {
        "active": confirmed[-1]["talkgroup"] if confirmed else (values[0] if values else None),
        "confirmed": bool(confirmed),
        "last_selection": confirmed[-1] if confirmed else None,
        "allowlist_configured": bool(TG_ALLOWLIST),
        "external": {"available": external["available"], "source": "FM-Funknetz",
                     "active": external["active"], "client_count": external["client_count"],
                     "live": external["live"], "last_heard": external["last_heard"],
                     "reason": external.get("reason", "Aktive TG stammt aus FM-Funknetz-Livedaten.")},
        "control": {"enabled": False, "reason": "TG-Steuerung bleibt bis TLS sowie starker AuthN/AuthZ sicher deaktiviert."},
    }


@app.get("/api/fm-funknetz/live")
def fm_funknetz():
    return fm_funknetz_live()


@app.get("/api/rf/status")
def rf_status():
    return local_rf_telemetry()


@app.get("/api/events")
def events():
    return normalized_local_events()


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
