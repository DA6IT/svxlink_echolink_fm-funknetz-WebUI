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

The installer protects the complete Apache site with Basic Auth. It asks for a WebUI username and an at-least-eight-character password, creates a bcrypt hash with `htpasswd -B`, and writes only that hash to `/etc/apache2/svxlink-webui.htpasswd`. The file is owned by `root:www-data` and has mode `0640`; it is backed up and rolled back if the installer fails. It must never enter the repository, tickets, or logs.

Basic Auth does not protect network transport. Use HTTPS or a VPN on untrusted networks; a firewall/IP allowlist and SSO remain possible additional controls.

## Secrets

Never commit:
- passwords
- API tokens
- authentication keys
- SSH/TLS private keys
- internal credentials
