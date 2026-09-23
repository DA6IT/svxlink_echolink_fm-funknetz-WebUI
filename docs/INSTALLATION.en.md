# Installation

## Status

The generic public installer is still under development. This document describes the current working reference installation.

## Target system

Currently intended for:
- Debian or Ubuntu
- existing SvxLink installation
- systemd
- Apache 2
- Python 3 / venv
- Node.js / npm

## Directories

```text
/opt/svxlink-webui              application
/opt/svxlink-webui/.venv        Python venv
/var/www/new.shart              frontend deployment
/var/lib/svxlink-webui          persistent data
/etc/svxlink-webui/environment  configuration
```

## Hardware detection

The installer does not assume Proxmox, LXC or any specific virtualization platform. Directly attached hardware is the normal installation case.

The installer detects or validates:

- ALSA sound devices for RX and TX
- preferably a directly attached USB sound card
- HID devices used for PTT
- an optional serial interface for SA818/SA818S
- SvxLink control and state PTYs after startup

Where possible, ALSA uses a stable card ID such as `plughw:CARD=Device,DEV=0` instead of relying on a numeric card index such as `plughw:0,0`.

During upgrades an existing `AUDIO_DEV` setting is preserved. Numeric configurations such as `plughw:0,0` are only reported with a warning and are not changed automatically.

The SA818/SA818S serial interface is optional. If it is unavailable, the rest of the WebUI remains operational and only the SHARI hardware view reports that serial access is unavailable.

### Virtualization and containers

When running inside a VM or container, the required USB, audio, HID and optional serial devices must be exposed by the virtualization platform. This is outside the normal installer path.

## Backend

```bash
cd /opt/svxlink-webui
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

Current systemd layout:

```ini
[Unit]
Description=SvxLink WebUI FastAPI backend
After=network.target

[Service]
Type=simple
User=svxlink-webui
Group=svxlink-webui
WorkingDirectory=/opt/svxlink-webui/backend
EnvironmentFile=-/etc/svxlink-webui/environment
ExecStart=/opt/svxlink-webui/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 12346
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

## Frontend

```bash
cd /opt/svxlink-webui/frontend
npm install
npm run build
```

The reference installation copies `frontend/dist/` to `/var/www/new.shart/`.

## Apache

Current layout:

```text
Frontend/API port: 12345
Backend:           127.0.0.1:12346
```

Example:

```apache
<VirtualHost *:12345>
    DocumentRoot /var/www/new.shart

    <Directory /var/www/new.shart>
        Require all granted
        Options -Indexes
    </Directory>

    <Location "/">
        AuthType Basic
        AuthName "SvxLink WebUI"
        AuthBasicProvider file
        AuthUserFile /etc/apache2/svxlink-webui.htpasswd
        Require valid-user
    </Location>

    ProxyPreserveHost On

    ProxyPass /api/ws/ ws://127.0.0.1:12346/api/ws/
    ProxyPassReverse /api/ws/ ws://127.0.0.1:12346/api/ws/

    ProxyPass /api/ http://127.0.0.1:12346/api/
    ProxyPassReverse /api/ http://127.0.0.1:12346/api/
</VirtualHost>
```

Before reload:

```bash
apache2ctl configtest
```

## SvxLink State PTY

Example:

```ini
STATE_PTY=/var/lib/svxlink/state/webui_state
```

## SvxLink Control PTY

Example:

```ini
DTMF_CTRL_PTY=/var/lib/svxlink/control/simplex_ctrl
```

The WebUI service needs write access to the resolved PTY target. Never assume a fixed `/dev/pts/X` path because it may change after restarting SvxLink.

## SvxLink health check

`systemctl is-active svxlink` alone is not considered a sufficient functional test. The SvxLink process can remain active even when `SimplexLogic` fails to initialize because of an audio or hardware problem.

The installer therefore also verifies that both `DTMF_CTRL_PTY` and `STATE_PTY` are actually created after SvxLink starts. If either is missing, installation stops and the latest SvxLink log messages are shown.

## EchoLink event bridge

Local handler:

```text
/usr/share/svxlink/events.d/local/EchoLinkWebUI.tcl
```

The original `/usr/share/svxlink/events.d/EchoLink.tcl` is not modified.

Raw events:

```text
/var/lib/svxlink/echolink-webui/events.tsv
```

## Public installer goals

The installer should:
1. check prerequisites
2. detect SvxLink configuration
3. detect State/Control PTYs
4. detect EchoLink configuration
5. create backups
6. create the service account
7. install the Python environment
8. build the frontend
9. configure Apache and systemd
10. safely configure PTY permissions
11. install the EchoLink event bridge
12. validate configuration
13. restart services in a controlled way
14. roll back on failure

It must not assume personal callsigns, Node IDs, hostnames, or fixed `/dev/pts/*` paths.

## Browser updater

The installer creates a separate `svxlink-webui-updater` account and a rootless update worker.

Browser updates are enabled by default after installation. The install request is protected by Apache Basic Auth, same-origin validation and a CSRF guard.

The updater may modify the application checkout, its versioned Python runtimes, the frontend deployment and the dedicated update data directories. It receives no general root or sudo privileges.

Before a new revision is activated, backend/security tests, dependency checks and the frontend build are executed. A health check follows the controlled backend restart. If activation fails, the Git revision, runtime and frontend are rolled back automatically.

Administrative changes to Apache, systemd, `/etc`, operating-system packages or hardware permissions are intentionally outside the browser updater.
