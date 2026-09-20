# Architektur

## Komponenten

```text
React/Vite Frontend
FastAPI Backend
SvxLink Integration
FM-Funknetz Datenquellen
EchoLink Datenquellen
```

## Frontend

Technologien:
- React 18
- TypeScript
- Vite

Das Frontend greift nicht direkt auf MQTT-Broker oder EchoLink-Verzeichnisdienste zu. Externe Provider werden im Backend gekapselt.

## Backend

Technologien:
- Python
- FastAPI
- Uvicorn
- SQLite
- MQTT
- WebSockets

Wichtige Module:

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

## Netzwerk

```text
Browser
   │
   ▼
Apache :12345
   │
   ├── Static Frontend
   ├── /api/    → 127.0.0.1:12346
   └── /api/ws/ → 127.0.0.1:12346
```

## SvxLink

Verwendete Schnittstellen:

```text
STATE_PTY
DTMF_CTRL_PTY
events.d/local
SvxLink Konfigurationsdateien
SvxLink Logdateien
```

Originale paketverwaltete Event-Dateien sollen nicht verändert werden.

## FM-Funknetz

```text
MQTT ────────┐
Statistik ───┼──► FastAPI ─► REST/WebSocket ─► React
TG-Namen ────┘
```

## EchoLink

```text
Node Lookup ──────┐
Current Logins ───┤
SvxLink Events ───┼──► EchoLink Backend ─► React
SQLite ───────────┘
```

## Persistenz

```text
/var/lib/svxlink-webui/echolink.sqlite3
/var/lib/svxlink/echolink-webui/events.tsv
```

## Designprinzipien

- keine erfundenen Produktionsdaten
- Original-SvxLink-Dateien möglichst nicht verändern
- lokale Erweiterungen getrennt halten
- Backend nur auf Loopback
- Steuerung nur über explizite Schnittstellen
- Eingaben validieren
- externe Provider im Backend kapseln
