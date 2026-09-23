# Security

SvxLink WebUI is not monitoring-only. It can issue real control commands to SvxLink.

## Backend

Reference:

```text
127.0.0.1:12346
```

External access is provided through Apache.

## Service account

```text
svxlink-webui
```

The systemd service uses settings including:

```text
NoNewPrivileges=true
PrivateTmp=true
```

## No generic shell interface

There is no HTTP endpoint for arbitrary shell commands. Control is performed only through explicit SvxLink interfaces.

## PTY permissions

Only the required control PTY should be writable by the service.

Not recommended:

```text
chmod 666
```

## Input validation

Talkgroups and EchoLink Node IDs are validated before being sent.

## Authentication

The application still has no built-in user management. The public installer protects the complete WebUI with Apache Basic Auth by default.

The backend API listens on `127.0.0.1` only; external access is provided through the authenticated Apache reverse proxy.

Additional controls such as VPN, firewall/IP allowlists or SSO may still be placed in front of the WebUI.

## Browser updater

Browser-based updates use multiple protection layers:

- Apache Basic Auth in front of the WebUI and API
- same-origin validation for write requests
- an explicit CSRF guard header
- `ProxyPreserveHost On` to preserve the original host at the backend
- a separate rootless updater service without sudo or root privileges
- security, backend and frontend tests before activation
- a health check after activation
- automatic rollback when an update fails

The browser process does not execute privileged system commands. Administrative system migrations remain outside the web updater.

## Secrets

Never commit:
- passwords
- API tokens
- authentication keys
- SSH/TLS private keys
- internal credentials
