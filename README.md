# SvxLink WebUI

Release 0.2.0 is a responsive FastAPI + React/Vite dashboard for a local SvxLink node. It starts in production-safe mode (`SVXLINK_WEBUI_DEMO=false`) and shows only data read from documented local, read-only sources.

## Live data and privacy

The dashboard reads these local sources, each configurable through its matching environment variable:

- `/etc/svxlink/node_info.json` (`SVXLINK_NODE_INFO_PATH`): only station/location, locator, coordinates, frequencies, mode/type, network, callsign and Default-TG fields are returned.
- `systemctl show svxlink` plus `/run/svxlink.pid` (`SVXLINK_SERVICE_NAME`, `SVXLINK_PID_PATH`): service state, substate and PID.
- `/var/log/svxlink` (`SVXLINK_LOG_PATH`): only parsed `ReflectorLogic: Node joined/left` events, event count and timestamp.
- `/etc/svxlink/svxlink.conf` (`SVXLINK_CONFIG_PATH`): only the explicit allowlist `LOGICS`, `DEFAULT_TG`, `CALLSIGN`, `NODE_INFO_FILE`, `LINKS`, and `SERVICES`.
- An optional normalized JSONL snapshot (`SVXLINK_STATE_PTY_PATH`) written by the separate `svxlink-state-collector` service. It contains only normalized documented `Tx:state` and `Rx:state` values. It is disabled unless `SVXLINK_STATE_PTY_ENABLED=true`.

There is deliberately no `/api/config` endpoint and no raw log or configuration output. The API has no write endpoint, shell command endpoint, service control, MQTT client, or radio/PTT control. The WebUI never opens the raw `STATE_PTY`; the dedicated collector has no shell/subprocess or PTY-write code, accepts only `Tx:state`/`Rx:state` input, and never accesses `COMMAND_PTY`, DTMF, or a PTT device.

## Local RF telemetry and future events

`/api/rf/status` and the dashboard label local TX/PTT and the full RX `sql_open`, `active`, and `siglev` arrays separately from FM-Funknetz activity. Without a readable, explicitly enabled snapshot, their state is unavailable rather than inferred from a network feed. `/api/events` is a disabled-by-default normalized input boundary (`SVXLINK_LOCAL_EVENT_INPUT_ENABLED`); it accepts no HTTP input and currently exposes only normalized read-only state events. Local talker/TG and EchoLink peers remain `unavailable` until a separately validated, one-way host-specific emitter produces actual events. Do not add Tcl, shell, or PTY command interpolation to this interface.

### STATE_PTY collector setup

`svxlink-state-collector.service` runs as the dedicated `svxlink-state-collector` account, with only group membership in `svxlink-state-reader`; the WebUI account has no raw-PTY access. Configure SvxLink's *read-only* `STATE_PTY` path at `SVXLINK_STATE_PTY_RAW_PATH` (a direct character-device/FIFO or SvxLink's direct symlink to `/dev/pts/<pty>`), and set `SVXLINK_STATE_PTY_ENABLED=true`. The installed root-owned `svxlink-state-pty-permissions.service` runs after every SvxLink start/restart, changes only the resolved PTY/FIFO to group `svxlink-state-reader` and mode `0640`, and grants the collector group read-only access (never write access). Do not grant either service account access to `COMMAND_PTY`.

The collector writes an atomically replaced, bounded 200-event JSONL snapshot to `/run/svxlink-webui/state.jsonl` (mode `0640`, owner `svxlink-state-collector:svxlink-webui`). It rejects malformed, oversized, and non-`Tx:state`/`Rx:state` lines; it logs and exits on a closed/unavailable raw PTY so systemd restarts it. The snapshot is replaced instead of appended, so history rotates on every update and cannot grow indefinitely. The binder resolves at most one symlink and accepts only a direct PTY target under `/dev/pts/`; escaping symlinks and regular-file targets fail closed.

After reviewing the host-specific PTY path in `/etc/svxlink-webui/environment`, run `sudo systemctl enable --now svxlink-state-collector`. The installer enables the permission binder as a `svxlink.service` dependency, so it is rerun on every SvxLink start/restart; it does not enable the optional collector. The collector does not use `PrivateDevices=true`: systemd cannot safely expand a deployment environment variable in a `BindReadOnlyPaths=` device mount. Its unprivileged account has no `tty` membership and can read only the configured PTY after the binder assigns its dedicated group. The binder fails closed for missing, escaping, or non-PTY paths; it never changes global `tty` permissions.

## FM-Funknetz live integration

The read-only `/api/fm-funknetz/live` endpoint consumes the confirmed CORS-enabled dashboard feeds `https://dashboard.fm-funknetz.de/data/live.json` and `lastheard.json`. It returns up to 100 current active talker/TG feed entries (not merely the first entry) and Last Heard entries under the explicit source label **FM-Funknetz Dashboard-Livedaten**. A transient feed failure is retried once and then reported as unavailable; no synthetic radio data is shown. The dashboard refreshes this data with its regular 15-second status cycle.

`FM_FUNKNETZ_LIVE_URL` and `FM_FUNKNETZ_LASTHEARD_URL` are deployment inputs but are accepted only when they exactly match the two confirmed HTTPS URLs (host `dashboard.fm-funknetz.de`, paths `/data/live.json` or `/data/lastheard.json`, no query/fragment). Redirects are not followed. Confirmed MQTT-over-WebSocket deployment values are `wss://status.thueringen.link/mqtt` and the read-only topics `/server/statethr`, `/server/statethr/1`, and `/server/state/logins`; they are represented by `FM_FUNKNETZ_MQTT_WS_URL` and `FM_FUNKNETZ_MQTT_ENABLED`. The API reports MQTT `configured` intent separately from `adapter_active`, which remains false because no server-side adapter is implemented. The browser does not connect to the public broker and this project never publishes or controls it. The current public feeds do not expose a reliable client count, so the API reports that field as unavailable rather than guessing.

## Future external active TG integration

The UI/API remains intentionally read-only. The confirmed FM-Funknetz dashboard feeds are used only for clearly labelled external telemetry; they never alter the local active TG. Local active TG display is based only on a new, numeric, allowlisted `ReflectorLogic: Selecting TG #<TG>` log line; a PTY write is never treated as confirmation. `SVXLINK_TG_ALLOWLIST` is the concrete deployment input for the server-side numeric allowlist.

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

The script creates the `svxlink-webui` service user plus a separate `svxlink-state-collector` user and `svxlink-state-reader` group, `/opt/svxlink-webui`, `/var/lib/svxlink-webui`, static root `/var/www/new.shart`, systemd units, and a new Apache site only. It refuses a busy port 12345 and runs `apache2ctl configtest` before reload. It does not edit existing Apache vHosts or SvxLink configuration, and it does not enable the optional raw-PTY collector; it enables only the restart-bound permission binder.

## Verification

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests
(cd frontend && npm run lint && npm run build)
```

No deployment actions are performed by this repository. Before deployment, verify source-file permissions for `svxlink-webui`, Apache access controls, and that the public API output contains no credentials or raw configuration.
