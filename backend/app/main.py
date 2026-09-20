"""Read-only SvxLink status API with an intentionally small data allowlist."""
from __future__ import annotations

import asyncio
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

from .activity_store import ActivityStore
from .fm_mqtt import FMFunknetzMQTT
from .fm_nodes import FMNodeDirectory
from .fm_stats import FMStatsDirectory
from .fm_tg_names import FMTalkgroupNames

VERSION = "0.7.0"
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
FM_MQTT_HOST = os.getenv("FM_FUNKNETZ_MQTT_HOST", "mqtt.fm-funknetz.de")
FM_MQTT_PORT = int(os.getenv("FM_FUNKNETZ_MQTT_PORT", "1883"))
FM_MQTT_TOPICS = tuple(
    topic.strip()
    for topic in os.getenv(
        "FM_FUNKNETZ_MQTT_TOPICS",
        "/server/statethr/1,/server/state/loginz,/server/state/logins",
    ).split(",")
    if topic.strip()
)
FM_MQTT_STALE_AFTER = int(
    os.getenv(
        "FM_FUNKNETZ_MQTT_STALE_AFTER",
        "120",
    )
)

ACTIVITY_DB = os.getenv(
    "SVXLINK_ACTIVITY_DB",
    "/var/lib/svxlink-webui/activity.db",
)

FM_NODES_HOST = os.getenv(
    "FM_FUNKNETZ_NODES_MQTT_HOST",
    "status.thueringen.link",
)

FM_NODES_PORT = int(
    os.getenv(
        "FM_FUNKNETZ_NODES_MQTT_PORT",
        "1883",
    )
)

FM_STATS_URL = os.getenv(
    "FM_FUNKNETZ_STATS_URL",
    "https://dashboard.fm-funknetz.de/stats_api.php",
)

FM_STATS_CACHE_TTL = int(
    os.getenv(
        "FM_FUNKNETZ_STATS_CACHE_TTL",
        "300",
    )
)

FM_FEED_ALLOWLIST = {"/data/live.json", "/data/lastheard.json"}
# This is deliberately a deployment setting, not user input.  It is used for
# displaying/validating local TG data even while control remains disabled.
TG_ALLOWLIST = frozenset(
    value for value in (item.strip() for item in os.getenv("SVXLINK_TG_ALLOWLIST", "").split(","))
    if value.isdigit() and value
)
# Optional, strictly read-only normalized JSONL state source written by the
# separate STATE_PTY collector.  The WebUI never opens the raw PTY.
STATE_PTY_PATH = Path(os.getenv("SVXLINK_STATE_PTY_PATH", "/run/svxlink-webui/state.jsonl"))
STATE_PTY_ENABLED = os.getenv("SVXLINK_STATE_PTY_ENABLED", "false").lower() in {"1", "true", "yes"}
LOCAL_EVENT_INPUT_ENABLED = os.getenv("SVXLINK_LOCAL_EVENT_INPUT_ENABLED", "false").lower() in {"1", "true", "yes"}

app = FastAPI(title="SvxLink WebUI", version=VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

activity_store = ActivityStore(
    ACTIVITY_DB,
)

fm_mqtt = FMFunknetzMQTT(
    FM_MQTT_HOST,
    FM_MQTT_PORT,
    FM_MQTT_TOPICS,
    FM_MQTT_STALE_AFTER,
    activity_store=activity_store,
)

_ws_clients: set[WebSocket] = set()
_app_loop: asyncio.AbstractEventLoop | None = None


async def _broadcast_fm(
    snapshot: dict[str, Any],
) -> None:
    dead: list[WebSocket] = []

    for websocket in list(
        _ws_clients
    ):
        try:
            await websocket.send_json(
                {
                    "event":
                        "fm-funknetz.state",
                    "data":
                        snapshot,
                }
            )
        except Exception:
            dead.append(
                websocket
            )

    for websocket in dead:
        _ws_clients.discard(
            websocket
        )


def _mqtt_updated(
    snapshot: dict[str, Any],
) -> None:
    loop = _app_loop

    if (
        loop is None
        or not loop.is_running()
    ):
        return

    loop.call_soon_threadsafe(
        lambda:
            asyncio.create_task(
                _broadcast_fm(
                    snapshot
                )
            )
    )



fm_nodes = FMNodeDirectory(
    FM_NODES_HOST,
    FM_NODES_PORT,
    bases=(
        (
            "1",
            "/server/state",
        ),
        (
            "2",
            "/server/m2/state",
        ),
    ),
    snapshots=(
        (
            "1",
            "https://dashboard.fm-funknetz.de/reflector1.json",
        ),
        (
            "2",
            "https://dashboard.fm-funknetz.de/reflector2.json",
        ),
    ),
)


@app.on_event("startup")
async def fm_nodes_startup():
    if FM_MQTT_ENABLED:
        fm_nodes.start()


@app.on_event("shutdown")
async def fm_nodes_shutdown():
    fm_nodes.stop()


@app.on_event("startup")
async def _startup() -> None:
    global _app_loop

    _app_loop = (
        asyncio.get_running_loop()
    )

    if FM_MQTT_ENABLED:
        fm_mqtt.start(
            _mqtt_updated
        )


@app.on_event("shutdown")
async def _shutdown() -> None:
    if FM_MQTT_ENABLED:
        fm_mqtt.stop()

NODE_KEYS = {"Location", "Locator", "LAT", "LONG", "TXFREQ", "RXFREQ", "Mode", "Type", "nodeLocation", "Verbund", "DefaultTG", "Callsign", "CALLSIGN"}
CONFIG_KEYS = {"LOGICS", "DEFAULT_TG", "CALLSIGN", "NODE_INFO_FILE", "LINKS", "SERVICES"}
LOG_TIMESTAMP = r"(?:\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?|\d{1,2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2}\.\d{3})"
JOIN_RE = re.compile(r"(?P<time>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+.*?Node (?P<event>joined|left):\s*(?P<callsign>[A-Za-z0-9/_-]+)", re.I)
SELECTING_TG_RE = re.compile(
    rf"(?P<time>{LOG_TIMESTAMP})(?::\s+|\s+).*?"
    r"ReflectorLogic: Selecting TG #(?P<tg>\d+)\s*$",
    re.I,
)
LOCAL_RF_RE = re.compile(
    rf"^(?P<time>{LOG_TIMESTAMP})(?::\s+|\s+).*?"
    r"(?:Rx1: The squelch is (?P<squelch>OPEN|CLOSED) \((?P<level>-?\d+(?:\.\d+)?)\)|"
    r"ReflectorLogic: Selecting TG #(?P<tg>\d+)|"
    r"ReflectorLogic: Talker (?P<talker_event>start|stop) on TG #(?P<talker_tg>\d+): (?P<callsign>[A-Za-z0-9/_-]+))$",
    re.I,
)


def normalize_log_timestamp(stamp: str) -> str:
    """Normalize the two supported SvxLink timestamp formats when valid."""
    try:
        if re.fullmatch(r"\d{1,2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2}\.\d{3}", stamp):
            return datetime.strptime(stamp, "%d %b %Y %H:%M:%S.%f").isoformat(timespec="milliseconds")
        parsed = datetime.fromisoformat(stamp.replace(" ", "T"))
        return parsed.isoformat(timespec="milliseconds" if parsed.microsecond else "seconds")
    except ValueError:
        return stamp.replace(" ", "T")


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
            if match:
                tg = match.group("tg")
                if tg.isdigit():
                    selections.append({
                        "talkgroup": tg,
                        "timestamp": normalize_log_timestamp(
                            match.group("time")
                        ),
                    })
    return selections[-limit:]


def local_log_rf_activity() -> dict[str, Any]:
    """Parse the small, confirmed read-only local RF log vocabulary."""
    result: dict[str, Any] = {
        "available": bool(log_files()), "source": "SvxLink-Log",
        "rx": {"squelch": None, "level": None, "timestamp": None},
        "talkgroup": None, "talker": None, "updated_at": None,
    }
    lines: list[tuple[str, re.Match[str]]] = []
    for path in log_files():
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                match = LOCAL_RF_RE.match(line.strip())
                if match:
                    lines.append((normalize_log_timestamp(match.group("time")), match))
        except OSError:
            continue
    for stamp, match in sorted(lines, key=lambda item: item[0]):
        timestamp = normalize_log_timestamp(stamp)
        if match.group("squelch"):
            result["rx"] = {"squelch": match.group("squelch").lower(),
                            "level": float(match.group("level")), "timestamp": timestamp}
        elif match.group("tg"):
            result["talkgroup"] = {"tg": match.group("tg"), "timestamp": timestamp}
        else:
            event = match.group("talker_event").lower()
            result["talker"] = None if event == "stop" else {
                "tg": match.group("talker_tg"), "callsign": match.group("callsign"),
                "timestamp": timestamp,
            }
        result["updated_at"] = timestamp
    return result


def _state_event(value: Any) -> tuple[str, dict[str, Any]] | None:
    """Validate collector-normalized JSONL without exposing raw input."""
    if not isinstance(value, dict):
        return None
    name = value.get("event")
    kind = "tx" if name == "Tx:state" else "rx" if name == "Rx:state" else ""
    if not kind:
        return None
    state = value.get("state")
    if not isinstance(state, (bool, list)):
        state = None
    if isinstance(state, list) and not all(isinstance(item, bool) for item in state):
        state = None
    result: dict[str, Any] = {"source": "STATE_PTY", "kind": kind, "state": state}
    timestamp = value.get("timestamp")
    if isinstance(timestamp, str) and len(timestamp) <= 64:
        result["timestamp"] = timestamp
    for key in ("sql_open", "active", "siglev"):
        field = value.get(key)
        values = field if isinstance(field, list) else [field]
        if values and all(isinstance(item, bool) for item in values):
            result[key] = field
        elif values and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in values):
            result[key] = field
    return kind, result


def local_rf_telemetry(limit: int = 100) -> dict[str, Any]:
    """Read only the collector's atomically replaced local JSONL snapshot."""
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
    """Return MQTT realtime state; HTTP remains fallback when MQTT is disabled."""
    if FM_MQTT_ENABLED:
        return fm_mqtt.snapshot()

    try:
        live, heard = _get_json(FM_LIVE_URL), _get_json(FM_LASTHEARD_URL)
        if not isinstance(live, list) or not isinstance(heard, list):
            raise ValueError("feed is not an array")
        return {"available": True, "source": "FM-Funknetz Dashboard-Livedaten",
                "active": live[0] if live else None, "live": live[:100], "last_heard": heard[:100],
                "client_count": None, "updated_at": datetime.now().astimezone().isoformat(),
                "mqtt": {"configured": False, "adapter_active": False, "connected": False, "topics": list(FM_MQTT_TOPICS)}}
    except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return {"available": False, "source": "FM-Funknetz Dashboard-Livedaten", "active": None,
                "live": [], "last_heard": [], "client_count": None,
                "reason": "FM-Funknetz-Livedaten momentan nicht erreichbar.",
                "mqtt": {"configured": False, "adapter_active": False, "connected": False, "topics": list(FM_MQTT_TOPICS)}}


def dashboard() -> dict[str, Any]:
    node = read_node_info(NODE_INFO_PATH)
    activity = reflector_activity()
    config = parse_ini(CONFIG_PATH)
    return {"node": node, "svxlink": service_status(), "reflector": activity,
            "rf": local_rf_telemetry(), "local_log": local_log_rf_activity(), "events": normalized_local_events(),
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


# --- TG CONTROL CONFIG ---

TG_CONTROL_ENABLED = (
    os.getenv(
        "TG_CONTROL_ENABLED",
        "false",
    ).lower()
    in {"1", "true", "yes", "on"}
)

TG_CONTROL_PTY = Path(
    os.getenv(
        "TG_CONTROL_PTY",
        "/var/lib/svxlink/control/simplex_ctrl",
    )
)


@app.get("/api/talkgroups")
def talkgroups():
    config = parse_ini(CONFIG_PATH)
    values = [value for section in config.values() for key, value in section.items() if key.upper() == "DEFAULT_TG"]
    confirmed = talkgroup_activity()
    external = fm_funknetz_live()
    default_tg = values[0] if values else None

    last_selection = (
        confirmed[-1]
        if confirmed
        else None
    )

    selected_tg = (
        last_selection["talkgroup"]
        if last_selection
        else None
    )

    # ReflectorLogic meldet TG 0, wenn eine temporäre
    # TG-Auswahl beendet wurde. Für die Oberfläche bedeutet
    # das: zurück zur konfigurierten DEFAULT_TG.
    using_default = (
        selected_tg in {None, "0"}
    )

    active_tg = (
        default_tg
        if using_default
        else selected_tg
    )

    return {
        "active": active_tg,
        "confirmed": bool(
            last_selection
            and selected_tg != "0"
        ),
        "using_default": using_default,
        "selected": selected_tg,
        "default": default_tg,
        "last_selection": last_selection,
        "allowlist_configured": bool(TG_ALLOWLIST),
        "external": {"available": external["available"], "source": "FM-Funknetz",
                     "active": external["active"], "client_count": external["client_count"],
                     "live": external["live"], "last_heard": external["last_heard"],
                     "mqtt": external.get("mqtt", {}),
                     "reason": external.get("reason", "FM-Funknetz-Status verfügbar.")},
        "control": {
            "enabled": TG_CONTROL_ENABLED,
            "reason": (
                "TG-Steuerung über SvxLink DTMF_CTRL_PTY aktiv."
                if TG_CONTROL_ENABLED
                else "TG-Steuerung ist serverseitig deaktiviert."
            ),
        },
    }


@app.get("/api/fm-funknetz/live")
def fm_funknetz():
    return fm_funknetz_live()


def _current_live_entries() -> list[dict[str, Any]]:
    try:
        data = fm_funknetz_live()

        live = data.get(
            "live",
            [],
        )

        return (
            live
            if isinstance(
                live,
                list,
            )
            else []
        )

    except Exception:
        return []


def _activity_for_tg(
    tg: str,
) -> dict[str, Any]:
    tg = str(
        tg
    ).strip()

    if not tg.isdigit():
        return {
            "found": False,
            "active": False,
            "tg": tg,
        }

    active = next(
        (
            item
            for item
            in _current_live_entries()
            if str(
                item.get(
                    "tg",
                    "",
                )
            )
            == tg
        ),
        None,
    )

    record = (
        activity_store
        .last_for_tg(
            tg
        )
    )

    if active:
        return {
            "found": True,
            "active": True,
            "call":
                str(
                    active.get(
                        "call",
                        "",
                    )
                ),

            "tg":
                tg,

            "talk":
                "start",

            "server":
                str(
                    active.get(
                        "server",
                        "",
                    )
                ),

            "source_time":
                str(
                    active.get(
                        "time",
                        "",
                    )
                ),

            "last_seen":
                active.get(
                    "received_at"
                ),

            "last_seen_epoch":
                active.get(
                    "received_at_epoch"
                ),
        }

    if record:
        return {
            "found": True,
            "active": False,
            **record,
        }

    return {
        "found": False,
        "active": False,
        "tg": tg,
    }


def _activity_for_call(
    call: str,
) -> dict[str, Any]:
    call = (
        str(call)
        .strip()
        .upper()
    )

    if not call:
        return {
            "found": False,
            "active": False,
            "call": call,
        }

    active = next(
        (
            item
            for item
            in _current_live_entries()
            if str(
                item.get(
                    "call",
                    "",
                )
            ).upper()
            == call
        ),
        None,
    )

    record = (
        activity_store
        .last_for_call(
            call
        )
    )

    if active:
        return {
            "found": True,
            "active": True,

            "call":
                call,

            "tg":
                str(
                    active.get(
                        "tg",
                        "",
                    )
                ),

            "talk":
                "start",

            "server":
                str(
                    active.get(
                        "server",
                        "",
                    )
                ),

            "source_time":
                str(
                    active.get(
                        "time",
                        "",
                    )
                ),

            "last_seen":
                active.get(
                    "received_at"
                ),

            "last_seen_epoch":
                active.get(
                    "received_at_epoch"
                ),
        }

    if record:
        return {
            "found": True,
            "active": False,
            **record,
        }

    return {
        "found": False,
        "active": False,
        "call": call,
    }


@app.get("/api/activity/talkgroup/{tg}")
def activity_talkgroup(
    tg: str,
):
    return _activity_for_tg(
        tg
    )


@app.get("/api/activity/talkgroups")
def activity_talkgroups(
    tg: str = "",
):
    values = []

    for item in tg.split(","):
        item = item.strip()

        if (
            item.isdigit()
            and item not in values
        ):
            values.append(
                item
            )

    return {
        "items": [
            _activity_for_tg(
                item
            )
            for item in values
        ]
    }


@app.get("/api/activity/callsign/{call}")
def activity_callsign(
    call: str,
):
    return _activity_for_call(
        call
    )


@app.get("/api/activity/buddies")
def activity_buddies(
    call: str = "",
):
    values = []

    for item in call.split(","):
        item = (
            item
            .strip()
            .upper()
        )

        if (
            item
            and item not in values
        ):
            values.append(
                item
            )

    return {
        "items": [
            _activity_for_call(
                item
            )
            for item in values
        ]
    }


@app.get("/api/activity/search")
def activity_search(
    q: str = "",
    limit: int = 20,
):
    q = (
        str(q)
        .strip()
        .upper()
    )

    if not q:
        return {
            "items": []
        }

    records = (
        activity_store
        .search_calls(
            q,
            limit,
        )
    )

    items = []

    for record in records:
        items.append(
            _activity_for_call(
                record["call"]
            )
        )

    return {
        "items": items
    }


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




fm_tg_names = FMTalkgroupNames(
    "https://fm-funknetz.de/Download/tgdb_list.txt",
    cache_ttl=3600,
)


fm_stats = FMStatsDirectory(
    FM_STATS_URL,
    cache_ttl=FM_STATS_CACHE_TTL,
)


def _buddy_call_match(
    call: str,
    base: str,
) -> bool:
    return (
        FMNodeDirectory
        .belongs_to_base(
            call,
            base,
        )
    )


def _node_search_enriched(
    query: str,
) -> dict[str, Any]:
    #
    # 1. Node Directory:
    #    Metadaten + aktueller Onlinezustand.
    #
    directory = (
        fm_nodes.search(
            query
        )
    )

    #
    # 2. FM-Funknetz Statistik:
    #    Primärquelle für bekannte Gerätevarianten.
    #
    stats = (
        fm_stats.call_detail(
            query
        )
    )

    base = str(
        stats.get(
            "call"
        )
        or directory.get(
            "base_call"
        )
        or query
    ).strip().upper()

    nodes_by_call: dict[
        str,
        dict[str, Any],
    ] = {}

    #
    # Node-Verzeichnis übernehmen.
    #
    for item in (
        directory.get(
            "nodes",
            []
        )
    ):
        call = str(
            item.get(
                "call",
                "",
            )
        ).strip().upper()

        if not call:
            continue

        nodes_by_call[
            call
        ] = dict(
            item
        )

    #
    # Statistik ist die primäre Quelle
    # zum Entdecken von Gerätesuffixen.
    #
    for device in (
        stats.get(
            "devices",
            []
        )
    ):
        call = str(
            device.get(
                "call",
                "",
            )
        ).strip().upper()

        if not call:
            continue

        node = (
            nodes_by_call.setdefault(
                call,
                {
                    "call":
                        call,

                    "online":
                        False,

                    "online_servers":
                        [],

                    "known_servers":
                        [],

                    "tg":
                        "",

                    "monitored_tgs":
                        [],

                    "location":
                        "",

                    "sysop":
                        "",

                    "node_last_seen":
                        None,
                },
            )
        )

        node[
            "stats"
        ] = device

    #
    # Auch lokale Talker-Historie ergänzen,
    # falls ein Call weder im Snapshot noch
    # in der Statistik auftaucht.
    #
    if base:
        for history in (
            activity_store
            .search_calls(
                base,
                50,
            )
        ):
            call = str(
                history.get(
                    "call",
                    "",
                )
            ).strip().upper()

            if (
                not call
                or not _buddy_call_match(
                    call,
                    base,
                )
            ):
                continue

            nodes_by_call.setdefault(
                call,
                {
                    "call":
                        call,

                    "online":
                        False,

                    "online_servers":
                        [],

                    "known_servers":
                        [],

                    "tg":
                        "",

                    "monitored_tgs":
                        [],

                    "location":
                        "",

                    "sysop":
                        "",

                    "node_last_seen":
                        None,
                },
            )

    #
    # Aktuell sprechende Calls.
    #
    live_entries = (
        _current_live_entries()
    )

    live_by_call = {
        str(
            item.get(
                "call",
                "",
            )
        ).strip().upper():
            item

        for item in live_entries

        if item.get(
            "call"
        )
    }

    latest_record: (
        dict[str, Any]
        | None
    ) = None

    variants = []

    for call, node in (
        nodes_by_call.items()
    ):
        local_history = (
            activity_store
            .last_for_call(
                call
            )
        )

        stats_device = (
            node.get(
                "stats"
            )
            or {}
        )

        stats_epoch = (
            stats_device.get(
                "last_seen_epoch"
            )
        )

        local_epoch = (
            local_history.get(
                "last_seen_epoch"
            )
            if local_history
            else None
        )

        #
        # Für "Last Seen" nehmen wir die
        # neueste bekannte Quelle.
        #
        last_activity = None

        try:
            stats_epoch_number = float(
                stats_epoch
                or 0
            )
        except (
            TypeError,
            ValueError,
        ):
            stats_epoch_number = 0

        try:
            local_epoch_number = float(
                local_epoch
                or 0
            )
        except (
            TypeError,
            ValueError,
        ):
            local_epoch_number = 0

        if (
            local_history
            and local_epoch_number
            >= stats_epoch_number
        ):
            last_activity = {
                **local_history,
                "source":
                    "local-mqtt",
            }

        elif stats_epoch_number > 0:
            last_activity = {
                "call":
                    call,

                "tg":
                    "",

                "talk":
                    "stats",

                "server":
                    "",

                "source_time":
                    "",

                "last_seen":
                    None,

                "last_seen_epoch":
                    stats_epoch_number,

                "source":
                    "fm-funknetz-stats",
            }

        live = (
            live_by_call.get(
                call
            )
        )

        enriched = {
            **node,

            "talk_active":
                bool(
                    live
                ),

            "talk_tg":
                (
                    str(
                        live.get(
                            "tg",
                            "",
                        )
                    )
                    if live
                    else ""
                ),

            "last_activity":
                last_activity,
        }

        variants.append(
            enriched
        )

        if (
            last_activity
            and last_activity.get(
                "last_seen_epoch"
            )
        ):
            if (
                latest_record
                is None
                or float(
                    last_activity[
                        "last_seen_epoch"
                    ]
                )
                > float(
                    latest_record[
                        "last_seen_epoch"
                    ]
                )
            ):
                latest_record = {
                    **last_activity,

                    "call":
                        call,
                }

    variants.sort(
        key=lambda item: (
            0
            if item.get(
                "talk_active"
            )
            else 1,

            0
            if item.get(
                "online"
            )
            else 1,

            0
            if item.get(
                "call"
            )
            == base
            else 1,

            str(
                item.get(
                    "call",
                    "",
                )
            ),
        )
    )

    #
    # Ist irgendeine Variante gerade aktiv?
    #
    active = next(
        (
            item

            for item
            in live_entries

            if _buddy_call_match(
                str(
                    item.get(
                        "call",
                        "",
                    )
                ),
                base,
            )
        ),
        None,
    )

    online_variants = [
        item
        for item
        in variants
        if item.get(
            "online"
        )
    ]

    return {
        "query":
            query,

        "base_call":
            base,

        "call":
            base,

        "found":
            bool(
                variants
            ),

        "active":
            bool(
                active
            ),

        "online":
            bool(
                online_variants
            ),

        "active_call":
            (
                str(
                    active.get(
                        "call",
                        "",
                    )
                ).upper()
                if active
                else None
            ),

        "tg":
            (
                str(
                    active.get(
                        "tg",
                        "",
                    )
                )
                if active
                else (
                    str(
                        latest_record.get(
                            "tg",
                            "",
                        )
                    )
                    if (
                        latest_record
                        and latest_record.get(
                            "tg"
                        )
                    )
                    else ""
                )
            ),

        "last_call":
            (
                str(
                    latest_record.get(
                        "call",
                        "",
                    )
                )
                if latest_record
                else None
            ),

        "last_tg":
            (
                str(
                    latest_record.get(
                        "tg",
                        "",
                    )
                )
                if (
                    latest_record
                    and latest_record.get(
                        "tg"
                    )
                )
                else None
            ),

        "last_seen":
            (
                latest_record.get(
                    "last_seen"
                )
                if latest_record
                else None
            ),

        "last_seen_epoch":
            (
                latest_record.get(
                    "last_seen_epoch"
                )
                if latest_record
                else None
            ),

        "online_calls":
            [
                item[
                    "call"
                ]
                for item
                in online_variants
            ],

        "variants":
            variants,

        "stats":
            {
                "available":
                    stats.get(
                        "available",
                        False,
                    ),

                "matched_by":
                    stats.get(
                        "matched_by"
                    ),

                "summary":
                    stats.get(
                        "summary",
                        {},
                    ),

                "by_tg":
                    stats.get(
                        "by_tg",
                        [],
                    ),
            },

        "directory":
            {
                "connected":
                    directory.get(
                        "connected",
                        False,
                    ),

                "have_index":
                    directory.get(
                        "have_index",
                        [],
                    ),

                "updated_at":
                    directory.get(
                        "updated_at"
                    ),
            },
    }


@app.get("/api/talkgroups/names")
def talkgroup_names():
    return fm_tg_names.status()


@app.get("/api/nodes/search")
def nodes_search(
    q: str = "",
):
    return (
        _node_search_enriched(
            q
        )
    )


@app.get("/api/nodes/buddies")
def nodes_buddies(
    call: str = "",
):
    bases = []

    for item in (
        call.split(",")
    ):
        base = (
            item
            .strip()
            .upper()
        )

        if (
            base
            and base not in bases
        ):
            bases.append(
                base
            )

    return {
        "items": [
            _node_search_enriched(
                base
            )
            for base
            in bases
        ]
    }


@app.get("/api/nodes/status")
def nodes_status():
    return fm_nodes.status()


@app.websocket("/api/ws/live")
async def live(websocket: WebSocket):
    await websocket.accept()

    _ws_clients.add(
        websocket
    )

    await websocket.send_json(
        {
            "event":
                "node.status",
            "data":
                dashboard(),
        }
    )

    if FM_MQTT_ENABLED:
        await websocket.send_json(
            {
                "event":
                    "fm-funknetz.state",
                "data":
                    fm_mqtt.snapshot(),
            }
        )

    try:
        while True:
            await websocket.receive_text()

    except Exception:
        _ws_clients.discard(
            websocket
        )

        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/health")
def health():
    return {"ok": True, "version": VERSION}


# --- TG CONTROL ENDPOINT ---

@app.post("/api/talkgroups/select/{tg}")
def select_talkgroup(tg: str):
    if not TG_CONTROL_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="TG-Steuerung ist deaktiviert.",
        )

    tg = str(tg).strip()

    if (
        not tg.isdigit()
        or len(tg) > 9
    ):
        raise HTTPException(
            status_code=400,
            detail="Ungültige Talkgroup.",
        )

    if not TG_CONTROL_PTY.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "SvxLink Control-PTY ist "
                "nicht verfügbar."
            ),
        )

    #
    # SimplexLogic:9:thr,ReflectorLogic
    #
    # Reflector TG-Auswahl:
    #   91<TG>#
    #
    command = f"91{tg}#".encode("ascii")

    try:
        fd = os.open(
            str(TG_CONTROL_PTY),
            os.O_WRONLY | os.O_NONBLOCK,
        )

        try:
            written = os.write(
                fd,
                command,
            )
        finally:
            os.close(fd)

    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "SvxLink konnte nicht "
                f"gesteuert werden: {exc}"
            ),
        ) from exc

    if written != len(command):
        raise HTTPException(
            status_code=503,
            detail="DTMF-Kommando wurde nicht vollständig geschrieben.",
        )

    #
    # Wichtig:
    # accepted != confirmed.
    #
    # Die tatsächliche Bestätigung kommt anschließend
    # wieder aus dem SvxLink-Log über /api/talkgroups.
    #
    return {
        "accepted": True,
        "requested": tg,
        "confirmed": False,
    }



# --- TG STATE WEBSOCKET ---

@app.websocket("/api/ws/talkgroups")
async def talkgroups_live(websocket: WebSocket):
    import asyncio

    await websocket.accept()

    last_signature = None

    try:
        while True:
            state = talkgroups()

            data = {
                "active": state.get("active"),
                "confirmed": state.get("confirmed"),
                "using_default": state.get("using_default"),
                "selected": state.get("selected"),
                "default": state.get("default"),
                "last_selection": state.get("last_selection"),
                "control": state.get("control", {}),
            }

            signature = repr(data)

            if signature != last_signature:
                await websocket.send_json({
                    "type": "talkgroups.state",
                    "data": data,
                })

                last_signature = signature

            await asyncio.sleep(0.35)

    except Exception:
        return



# ============================================================
# FM-Funknetz Top Talkgroups
# ============================================================

@app.get("/api/fm-funknetz/top-talkgroups")
def fm_funknetz_top_talkgroups(
    range: str = "24h",
    limit: int = 5,
):
    from fastapi import HTTPException

    from .fm_top_tgs import (
        get_top_talkgroups,
    )

    try:
        return get_top_talkgroups(
            range,
            limit,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


# --- ECHOLINK WEBUI API V1 ---


@app.get("/api/echolink-webui/status")
def echolink_webui_status():

    from .echolink_webui import (
        status,
    )

    return status()


@app.get("/api/echolink-webui/history")
def echolink_webui_history(
    limit: int = 50,
):

    from .echolink_webui import (
        history,
    )

    return {
        "history":
            history(
                limit
            )
    }


@app.get("/api/echolink-webui/nodes")
def echolink_webui_nodes():

    from .echolink_webui import (
        list_nodes,
    )

    return {
        "nodes":
            list_nodes()
    }


@app.post("/api/echolink-webui/nodes")
def echolink_webui_save_node(
    payload: dict,
):

    from fastapi import (
        HTTPException,
    )

    from .echolink_webui import (
        save_node,
    )

    try:

        return save_node(
            payload.get(
                "node_id",
                "",
            ),
            payload.get(
                "callsign",
                "",
            ),
            payload.get(
                "label",
                "",
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@app.delete("/api/echolink-webui/nodes/{node_id}")
def echolink_webui_delete_node(
    node_id: str,
):

    from .echolink_webui import (
        delete_node,
    )

    return delete_node(
        node_id
    )


@app.post("/api/echolink-webui/control/activate")
def echolink_webui_activate():

    from fastapi import (
        HTTPException,
    )

    from .echolink_webui import (
        activate_module,
    )

    try:

        return activate_module()

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@app.post("/api/echolink-webui/control/deactivate")
def echolink_webui_deactivate():

    from fastapi import (
        HTTPException,
    )

    from .echolink_webui import (
        deactivate_module,
    )

    try:

        return deactivate_module()

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@app.post("/api/echolink-webui/control/connect/{node_id}")
def echolink_webui_connect(
    node_id: str,
):

    from fastapi import (
        HTTPException,
    )

    from .echolink_webui import (
        connect_node,
    )

    try:

        return connect_node(
            node_id
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


@app.post("/api/echolink-webui/control/disconnect")
def echolink_webui_disconnect():

    from fastapi import (
        HTTPException,
    )

    from .echolink_webui import (
        disconnect,
    )

    try:

        return disconnect()

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc



# --- ECHOLINK DIRECTORY SEARCH V2 ---


@app.get("/api/echolink-webui/search")
def echolink_webui_search(
    q: str = "",
):

    from fastapi import (
        HTTPException,
    )

    from .echolink_webui import (
        directory_search,
    )


    try:

        return directory_search(
            q
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
