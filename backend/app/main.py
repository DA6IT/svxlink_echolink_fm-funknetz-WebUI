"""SvxLink WebUI API."""
from __future__ import annotations
import configparser, json, os, platform, time
from pathlib import Path
from typing import Any
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

VERSION = "0.1.0"
DEMO = os.getenv("SVXLINK_WEBUI_DEMO", "true").lower() in {"1", "true", "yes"}
CONFIG_PATH = Path(os.getenv("SVXLINK_CONFIG_PATH", "/etc/svxlink/svxlink.conf"))
NODE_INFO_PATH = Path(os.getenv("SVXLINK_NODE_INFO_PATH", "/var/lib/svxlink/node_info.json"))
SERVICE_NAME = os.getenv("SVXLINK_SERVICE_NAME", "svxlink")

app = FastAPI(title="SvxLink WebUI", version=VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def parse_ini(path: Path) -> dict[str, dict[str, str]]:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    if not path.is_file(): return {}
    parser.read(path, encoding="utf-8")
    return {section: dict(parser.items(section)) for section in parser.sections()}


def read_node_info(path: Path) -> dict[str, Any]:
    if not path.is_file(): return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError): return {}


def service_status() -> dict[str, Any]:
    if DEMO: return {"running": True, "status": "online", "service": SERVICE_NAME, "pid": 1234}
    return {"running": False, "status": "unavailable", "service": SERVICE_NAME, "pid": None}


def dashboard() -> dict[str, Any]:
    node = {"name": os.getenv("SVXLINK_NODE_NAME", "SvxLink Node"), "callsign": os.getenv("SVXLINK_CALLSIGN", ""), "location": os.getenv("SVXLINK_LOCATION", "")}
    if DEMO:
        node.update({"name": "DA6IT-L", "callsign": "DA6IT-L", "location": "Wachtendonk · JO31EJ", "frequency": "430.025 MHz"})
    return {"node": node, "svxlink": service_status(), "radio": {"rx": DEMO, "tx": False, "talkgroup": 26298 if DEMO else None, "talker": "DL1ABC" if DEMO else None}, "fm": {"status": "connected" if DEMO else "unavailable"}, "echolink": {"status": "connected" if DEMO else "unavailable"}, "demo": DEMO, "version": VERSION}

@app.get("/api/status")
def status(): return dashboard()

@app.get("/api/svxlink/status")
def svxlink_status(): return service_status()

@app.get("/api/system")
def system(): return {"hostname": platform.node(), "os": platform.platform(), "python": platform.python_version(), "uptime": int(time.monotonic()), "version": VERSION}

@app.get("/api/config")
def config(): return {"path": str(CONFIG_PATH), "sections": parse_ini(CONFIG_PATH), "available": CONFIG_PATH.is_file()}

@app.get("/api/node-info")
def node_info(): return {"path": str(NODE_INFO_PATH), "data": read_node_info(NODE_INFO_PATH), "available": NODE_INFO_PATH.is_file()}

@app.get("/api/last-heard")
def last_heard(): return [{"callsign": "DL1ABC", "talkgroup": 26298, "name": "DL", "duration": 18, "source": "demo"}] if DEMO else []

@app.get("/api/talkgroups")
def talkgroups(): return {"active": 26298 if DEMO else None, "favorites": [26298, 26299] if DEMO else [], "available": DEMO}

@app.get("/api/echolink/status")
def echolink(): return {"status": "connected" if DEMO else "unavailable", "callsign": "" if not DEMO else "DEMO-L"}

@app.get("/api/svxlink/logs")
def logs(): return {"lines": ["Demo mode: no production journal connected."] if DEMO else [], "available": DEMO}

@app.websocket("/api/ws/live")
async def live(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"event": "node.status", "data": dashboard()})
    try:
        while True: await websocket.receive_text()
    except Exception: await websocket.close()

@app.get("/health")
def health(): return {"ok": True, "version": VERSION}
