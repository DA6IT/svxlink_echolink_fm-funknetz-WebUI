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

Built-in authentication is not yet included in the pre-release.

Do not expose the WebUI publicly without protection. Suitable controls include:
- VPN
- firewall/IP allowlist
- reverse-proxy authentication
- SSO

## Secrets

Never commit:
- passwords
- API tokens
- authentication keys
- SSH/TLS private keys
- internal credentials
