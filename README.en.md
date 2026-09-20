# SvxLink WebUI

A modern responsive web interface for **SvxLink**, **SHARI**, **FM-Funknetz**, and **EchoLink**.

The application combines a FastAPI backend with a React/Vite frontend and provides live data, operational status, and selected control functions in a browser.

> **Status:** Pre-release / active development.  
> The WebUI is already running on a real SvxLink/SHARI installation. The generic public installer is still being prepared.

[German version](README.md)

## Features

### Overview
- responsive desktop, tablet and mobile UI
- live FM-Funknetz and EchoLink status
- direct navigation to operation pages
- no invented production radio data

### FM-Funknetz
- currently selected local talkgroup
- active talkgroups in real time
- MQTT-based live activity
- current callsign
- talkgroup names
- favourite talkgroups
- direct talkgroup selection through SvxLink
- leave talkgroup / restore default TG
- Top Talkgroups for 24 hours, 7 days and 30 days
- node and activity information
- buddy and last-seen functions
- WebSocket-based state updates

Details: [docs/FM-FUNKNETZ.en.md](docs/FM-FUNKNETZ.en.md)

### EchoLink
- local EchoLink callsign and Node ID
- EchoLink directory status
- activate/deactivate EchoLink module
- current incoming and outgoing connections
- connection duration and disconnect
- search by callsign or Node ID
- ONLINE / BUSY / OFFLINE
- registered nodes can be found while offline
- save EchoLink favourites
- directly connect to favourites
- live status for saved nodes
- persistent connection history

Details: [docs/ECHOLINK.en.md](docs/ECHOLINK.en.md)

## Architecture

```text
Browser
   │
   ▼
Apache :12345
   │
   ├── React/Vite frontend
   ├── /api/    ─────────► FastAPI/Uvicorn 127.0.0.1:12346
   └── /api/ws/ ─────────► WebSockets
```

The backend binds to loopback only. Apache serves the frontend and provides the reverse proxy and WebSocket proxy.

Details: [docs/ARCHITECTURE.en.md](docs/ARCHITECTURE.en.md)

## Reference paths

```text
/opt/svxlink-webui              application
/opt/svxlink-webui/backend      backend
/opt/svxlink-webui/frontend     frontend
/var/www/new.shart              current document root
/var/lib/svxlink-webui          persistent WebUI data
/etc/svxlink-webui/environment  runtime configuration
```

These paths describe the current reference installation. The future installer should detect or configure paths where appropriate.

## Installation

The generic public installer is not finished yet.

Current layout: [docs/INSTALLATION.en.md](docs/INSTALLATION.en.md)

## Configuration

[docs/CONFIGURATION.en.md](docs/CONFIGURATION.en.md)

## Security

The WebUI is **not read-only**. It can issue real SvxLink control commands.

It should not be exposed publicly without suitable protection. Recommended options include VPN, firewall/IP allowlist, reverse-proxy authentication, or SSO.

Details: [docs/SECURITY.en.md](docs/SECURITY.en.md)

## Privacy and public examples

Live data may be displayed during actual operation. README files, screenshots, demo data, and static UI placeholders should not permanently contain randomly observed third-party callsigns or EchoLink Node IDs.

Suitable static examples:

```text
DA6IT
DA6IT-L
DB0XYZ-R
<CALLSIGN>
<NODE_ID>
<TALKGROUP>
```

Details: [docs/PRIVACY.en.md](docs/PRIVACY.en.md)

## Development

Backend:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

PYTHONPATH=backend .venv/bin/uvicorn app.main:app   --host 127.0.0.1   --port 12346
```

Frontend:

```bash
cd frontend
npm install
npm run build
npm run lint
```

## Project status

Successfully tested:
- FM-Funknetz MQTT and live activity
- talkgroup selection and favourites
- Top Talkgroups
- EchoLink directory status and search
- EchoLink ONLINE/BUSY/OFFLINE
- EchoLink favourites
- EchoLink connect/disconnect
- EchoLink history
- FastAPI REST API and WebSockets
- responsive UI

Before the first public release:
- finish the generic installer
- upgrade and uninstall workflow
- complete automatic SvxLink detection
- authentication/authorization
- clean-install testing
- anonymize public UI examples/screenshots
- finalize licensing and release information

## Known pre-release limitations

The current EchoLink control path still uses module ID `2` when activating EchoLink. Before public release, this must be read entirely from `ModuleEchoLink.conf`.

EchoLink search uses public EchoLink web sources. Changes to their HTML structure may require updates to the backend provider.

## Documentation

- [Installation](docs/INSTALLATION.en.md)
- [Configuration](docs/CONFIGURATION.en.md)
- [Architecture](docs/ARCHITECTURE.en.md)
- [FM-Funknetz](docs/FM-FUNKNETZ.en.md)
- [EchoLink](docs/ECHOLINK.en.md)
- [Security](docs/SECURITY.en.md)
- [Privacy / public examples](docs/PRIVACY.en.md)
