# SvxLink WebUI

Release 0.1.0 is a responsive FastAPI + React/Vite dashboard for SvxLink, SHARI and FM-Funknetz nodes. It runs safely in a clearly marked demo mode by default; production mode never invents radio data.

## Architecture
Browser → Apache `:12345` → static React files in `/var/www/new.shart`; `/api/` and `/api/ws/` proxy to Uvicorn at `127.0.0.1:12346`. The backend uses config-driven paths and exposes read-only status/config/system endpoints plus live WebSocket infrastructure.

## Development / demo
```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 12346
cd frontend && npm install && npm run build
```
`SVXLINK_WEBUI_DEMO=true` activates clearly labelled demo data. Set it to `false` for production; unavailable sources return `Nicht verfügbar` / empty data. Copy `.env.example` to `/etc/svxlink-webui/environment` and configure paths, without committing credentials.

## Installation
On a Debian/Ubuntu host with Python, Node/npm, Apache and SvxLink installed:
```bash
git clone https://git.da6it.de/DA6IT/svxlink-webui.git
cd svxlink-webui
sudo ./install.sh
```
The script creates user `svxlink-webui`, `/opt/svxlink-webui`, `/var/lib/svxlink-webui`, static root `/var/www/new.shart`, systemd service, and a new Apache site only. It refuses a busy port 12345 and runs `apache2ctl configtest` before reload. It does not edit existing Apache vHosts or SvxLink configuration.

## Security and limits
No shell-command endpoint, arbitrary path, service control, production FM-Funknetz API, or MQTT topic is exposed in 0.1.0. The service binds only to loopback and runs unprivileged. OIDC is configuration-ready (`AUTH_MODE`) but not implemented. Inspect and restrict Apache network access before exposing the un-authenticated initial release.

## CI
GitLab CI runs backend tests, TypeScript lint, and production frontend build.
