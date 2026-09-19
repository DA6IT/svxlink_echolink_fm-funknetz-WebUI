# SvxLink WebUI

Release 0.2.0 is a responsive FastAPI + React/Vite dashboard for a local SvxLink node. It starts in production-safe mode (`SVXLINK_WEBUI_DEMO=false`) and shows only data read from documented local, read-only sources.

## Live data and privacy

The dashboard reads these local sources, each configurable through its matching environment variable:

- `/etc/svxlink/node_info.json` (`SVXLINK_NODE_INFO_PATH`): only station/location, locator, coordinates, frequencies, mode/type, network, callsign and Default-TG fields are returned.
- `systemctl show svxlink` plus `/run/svxlink.pid` (`SVXLINK_SERVICE_NAME`, `SVXLINK_PID_PATH`): service state, substate and PID.
- `/var/log/svxlink` (`SVXLINK_LOG_PATH`): only parsed `ReflectorLogic: Node joined/left` events, event count and timestamp.
- `/etc/svxlink/svxlink.conf` (`SVXLINK_CONFIG_PATH`): only the explicit allowlist `LOGICS`, `DEFAULT_TG`, `CALLSIGN`, `NODE_INFO_FILE`, `LINKS`, and `SERVICES`.

There is deliberately no `/api/config` endpoint and no raw log or configuration output. The API has no write endpoint, shell command endpoint, service control, MQTT client, or radio/PTT control.

## Future external active TG integration

The UI/API is intentionally read-only. No verified public FM-Funknetz MQTT/telemetry source was found, so the UI explicitly reports “nicht verfügbar” and never simulates an external TG. Local active TG display is based only on a new, numeric, allowlisted `ReflectorLogic: Selecting TG #<TG>` log line; a PTY write is never treated as confirmation. `SVXLINK_TG_ALLOWLIST` is the concrete deployment input for the server-side numeric allowlist.

TG activation is intentionally disabled. Do not add an open control endpoint or proxy the legacy WebUI/PTY. A future implementation requires a deployment-provided TLS termination plus strong AuthN/AuthZ (prefer mTLS/VPN or OIDC/RBAC), and a least-privilege local broker identity with access to the configured DTMF PTY. This repository contains no credentials or default identity to use; the deployment operator must provide and document that identity before control can be enabled.

### Concrete secure control hand-off

The only designated configuration input for a future control deployment is the root-owned file `/etc/svxlink-webui/control.env` (mode `0600`, owner `root:svxlink-webui`). It is deliberately not created by this repository and must not be committed. Before any `POST /api/control/talkgroups/{tg}` route may be installed, its deployment review must record all of the following: `SVXLINK_CONTROL_ENABLED=true`; a numeric `SVXLINK_TG_ALLOWLIST`; the local, group-restricted DTMF PTY path; and the approved identity boundary (Apache/ingress mTLS client-CA or OIDC issuer, audience, and required operator role). The proxy must terminate TLS, deny every client without that identity, and pass only a verified principal/role to the loopback backend. The backend must construct only `9<TG>#`, write it through a least-privilege local broker, and return success only after a new correlated `ReflectorLogic: Selecting TG #<TG>` line. None of these prerequisites is present here, so no control route exists and no PTY is opened.

## Architecture

Browser → Apache `:12345` → static React files; `/api/` and `/api/ws/` proxy to Uvicorn at `127.0.0.1:12346`. The backend is read-only and binds to loopback. The dashboard refreshes its status every 15 seconds.

## Development / demo

```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 12346
cd frontend && npm install && npm run lint && npm run build
```

Set `SVXLINK_WEBUI_DEMO=true` only for a labelled local demonstration. Production source paths must be readable by the unprivileged service user; unavailable sources are reported as unavailable rather than fabricated.

## Installation

On a Debian/Ubuntu host with Python, Node/npm, Apache and SvxLink installed:

```bash
git clone https://git.da6it.de/hermes/svxlink-webui.git
cd svxlink-webui
sudo ./install.sh
```

The script creates user `svxlink-webui`, `/opt/svxlink-webui`, `/var/lib/svxlink-webui`, static root `/var/www/new.shart`, systemd service, and a new Apache site only. It refuses a busy port 12345 and runs `apache2ctl configtest` before reload. It does not edit existing Apache vHosts or SvxLink configuration.

## Verification

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests
(cd frontend && npm run lint && npm run build)
```

No deployment actions are performed by this repository. Before deployment, verify source-file permissions for `svxlink-webui`, Apache access controls, and that the public API output contains no credentials or raw configuration.
