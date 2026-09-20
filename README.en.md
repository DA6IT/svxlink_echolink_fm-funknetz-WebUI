# SvxLink WebUI

A responsive web interface for **SvxLink**, **SHARI**, **FM-Funknetz**, and **EchoLink**. It combines a FastAPI backend with a React/Vite frontend and provides live data, operating status, and selected control functions.

> **Status:** Pre-release / active development. A working reference installation is running in production. The interactive installer exists and is version `1.0.0-pre1`; further clean installations on fresh Debian/Ubuntu systems are still pending.

[German version](README.md)

## Features

- responsive desktop, tablet, and mobile interface
- FM-Funknetz live status, MQTT activity, and talkgroup selection
- EchoLink directory status, search, favourites, and incoming/outgoing connections
- direct FM talkgroup control through SvxLink
- activate/deactivate the EchoLink module and directly connect to a callsign or node
- WebSocket-based state updates and persistent connection history

Details: [FM-Funknetz](docs/FM-FUNKNETZ.en.md) · [EchoLink](docs/ECHOLINK.en.md)

## Architecture and default ports

```text
Browser -> Apache :12345 -> frontend
                         -> /api/ and /api/ws/ -> FastAPI/Uvicorn 127.0.0.1:12346
```

The backend binds to loopback by default. The installer can change the ports; `12345` (WebUI) and `12346` (internal API) are the defaults.

## Installation

The interactive installer is available as `install.sh` in this repository. It is a pre-release (`1.0.0-pre1`), not a guarantee for arbitrary systems. A production reference installation exists; validation on further fresh Debian/Ubuntu systems is pending.

Quick start (when cloned as an unprivileged user):

```bash
git clone https://github.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI.git
cd svxlink_echolink_fm-funknetz-WebUI
sudo ./install.sh
```

Alternatively, from an already-open root shell:

```bash
./install.sh
```

The installer requires `EUID=0` and deliberately does not use `sudo` internally. It interactively prompts for all site-specific values. See the [installation guide](docs/INSTALLATION.en.md) for prerequisites, rollback behaviour, and limitations.

## Security

The WebUI is not read-only and can send real SvxLink control commands. The backend listens locally by default, but Apache can publish the UI on a network. Use appropriate access protection in production, such as a VPN, firewall/IP allowlist, or reverse-proxy authentication. Never copy credentials or keys into documentation or public examples.

Details: [Security](docs/SECURITY.en.md) · [Privacy](docs/PRIVACY.en.md)

## Project status and known limitations

FM-Funknetz live activity, talkgroup control, EchoLink status/search/connections, the REST API, WebSockets, and the responsive UI have been tested in production. Before a general release, further clean installations on fresh systems, an upgrade/uninstall workflow, complete authentication, and additional installer validation remain outstanding.

The current EchoLink activation path uses module ID `2`. EchoLink search uses public web sources; changes to their HTML structure may require provider changes.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 12346

cd frontend
npm install
npm run lint
npm run build
```

## Documentation

- [Installation](docs/INSTALLATION.en.md) · [Deutsch](docs/INSTALLATION.md)
- [Configuration](docs/CONFIGURATION.en.md) · [Architecture](docs/ARCHITECTURE.en.md)
- [FM-Funknetz](docs/FM-FUNKNETZ.en.md) · [EchoLink](docs/ECHOLINK.en.md)
