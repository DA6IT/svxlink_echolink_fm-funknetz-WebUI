# Architecture

## Components

```text
React/Vite frontend
FastAPI backend
SvxLink integration
FM-Funknetz data sources
EchoLink data sources
```

## Frontend

Technology:
- React 18
- TypeScript
- Vite

The frontend does not directly access MQTT brokers or EchoLink directory services. External providers are isolated in the backend.

## Backend

Technology:
- Python
- FastAPI
- Uvicorn
- SQLite
- MQTT
- WebSockets

Important modules:

```text
activity_store.py
echolink_webui.py
fm_mqtt.py
fm_nodes.py
fm_stats.py
fm_tg_names.py
fm_top_tgs.py
main.py
state_pty_collector.py
state_pty_permissions.py
```

## Network

```text
Browser
   │
   ▼
Apache :12345
   │
   ├── Static frontend
   ├── /api/    → 127.0.0.1:12346
   └── /api/ws/ → 127.0.0.1:12346
```

## SvxLink

Interfaces:

```text
STATE_PTY
DTMF_CTRL_PTY
events.d/local
SvxLink configuration files
SvxLink log files
```

Original package-managed event files should not be modified.

## FM-Funknetz

```text
MQTT ────────┐
Statistics ──┼──► FastAPI ─► REST/WebSocket ─► React
TG names ────┘
```

## EchoLink

```text
Node Lookup ──────┐
Current Logins ───┤
SvxLink Events ───┼──► EchoLink backend ─► React
SQLite ───────────┘
```

## Persistence

```text
/var/lib/svxlink-webui/echolink.sqlite3
/var/lib/svxlink/echolink-webui/events.tsv
```

## Design principles

- no invented production data
- avoid modifying original SvxLink files
- keep local extensions separate
- backend binds to loopback only
- control only through explicit interfaces
- validate inputs
- isolate external providers in the backend
