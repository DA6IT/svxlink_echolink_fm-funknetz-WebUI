# Installation

## Status and scope

`install.sh` is an interactive pre-release installer at version `1.0.0-pre2`. A working reference installation is running in production. Clean installations on further fresh Debian/Ubuntu systems are not yet complete, so this is not a general compatibility guarantee.

Debian/Ubuntu-based systems with systemd are supported. The installer detects an existing SvxLink installation or offers to install `svxlink-server` and calibration tools. It needs network access for package, Python, and Node dependencies.

## Quick start

Clone as an unprivileged user and run the installer once with root privileges:

```bash
git clone https://github.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI.git
cd svxlink_echolink_fm-funknetz-WebUI
sudo ./install.sh
```

Or run it from an already-open root shell:

```bash
./install.sh
```

`install.sh` checks `EUID=0`; it deliberately does not use `sudo` internally. The script is interactive: review values, enter site-specific information, and only then confirm the displayed installation plan. Never copy passwords, AUTH_KEYs, real callsigns, or Node IDs into tickets, documentation, or public logs.

## Requested values and defaults

The installer preserves detected values where possible, otherwise it prompts for them.

| Area | Default / behaviour |
| --- | --- |
| WebUI source installation | `/opt/svxlink-webui` |
| Apache document root | `/var/www/svxlink-webui` |
| Service account | `svxlink-webui` (never `root`) |
| WebUI port | `80` |
| Internal API | `127.0.0.1:12346` |
| SvxLink control PTY | `/var/lib/svxlink/control/simplex_ctrl` |
| SvxLink state PTY | `/var/lib/svxlink/state/webui_state` |
| FM-Funknetz | callsign, AUTH_KEY, default TG, locator, frequency, power, antenna, audio, and PTT |
| EchoLink | callsign, password, module ID (default `2`), optional Node ID, sysop, and location |

The UI and API ports must differ. Used ports cause a warning and confirmation prompt. A hostname is optional; without one, IP access is intended.

## What the installer sets up

After confirmation, the installer installs or checks Apache, Python/venv/pip, Node.js/npm, rsync, curl, CA certificates, and audio/USB utilities. Node.js must be at least version 18. It creates a Python venv, installs backend dependencies, runs frontend lint and build, and copies `frontend/dist/` to the selected document root.

It creates the service account and the `svxlink-state-reader` and `svxlink-control` groups, installs the WebUI and state-collector services, and configures Apache as a reverse proxy including a WebSocket proxy. The backend binds only to `127.0.0.1`; Apache serves the WebUI on the chosen UI port.

For SvxLink, the installer sets or updates `DTMF_CTRL_PTY` and `STATE_PTY`. The state collector writes normalised data to `/run/svxlink-webui/state.jsonl`. PTY permissions are set through watched systemd units; do not assume a fixed `/dev/pts/N` number because its target may change after SvxLink restarts.

When FM-Funknetz configuration is selected, the installer configures `ReflectorLogic` and `NetLink`. Direct FM talkgroup selection and leaving a talkgroup or returning to the default TG are performed by the WebUI through SvxLink. When EchoLink configuration is selected, it writes `ModuleEchoLink.conf` and installs the local event bridge `/usr/share/svxlink/events.d/local/EchoLinkWebUI.tcl`; the original EchoLink event file is not modified. The WebUI can control the EchoLink module, connect directly to callsigns or nodes, and disconnect calls.

## Backup, validation, and rollback

Before changing anything, the installer backs up affected configuration, systemd, and Apache files in a timestamped directory below `/var/backups/svxlink-webui/`. On failure it rolls back those files, Apache enablement, and services where possible. Installed packages, users, and groups are deliberately not removed.

Before restart, the installer checks Python files, runs `pytest backend/app/test_api.py -q`, and tests the Apache configuration. It then restarts SvxLink, the WebUI services, and Apache, and checks both `/health` on the loopback API and the WebUI through Apache.

## Security and operational limits

- The WebUI can send real control commands. The installer asks for a WebUI username and an at-least-eight-character password, then protects the complete Apache site with Basic Auth. The bcrypt hash is stored only in `/etc/apache2/svxlink-webui.htpasswd` (owner `root`, group `www-data`, mode `0640`); neither plaintext passwords nor hashes belong in the repository. Use HTTPS or a VPN as additional protection on untrusted networks.
- SvxLink and EchoLink configurations containing credentials are restricted to `root:svxlink` and mode `0640` when that group exists. The runtime environment is written as `root:<WebUI group>` with mode `0640`.
- Depending on the network and router, EchoLink may still need inbound UDP ports `5198/5199`.
- The script selectively updates existing configuration but is not a complete upgrade or uninstall workflow. Review backups and interactive input carefully before production changes.

Further reading: [Configuration](CONFIGURATION.en.md), [Architecture](ARCHITECTURE.en.md), [Security](SECURITY.en.md).
