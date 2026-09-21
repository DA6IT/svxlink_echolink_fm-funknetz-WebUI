# Sicherheit

SvxLink WebUI ist keine reine Monitoring-Oberfläche. Sie kann reale Steuerbefehle an SvxLink senden.

## Backend

Referenz:

```text
127.0.0.1:12346
```

Der externe Zugriff erfolgt über Apache.

## Service-Benutzer

```text
svxlink-webui
```

Der systemd-Service verwendet u. a.:

```text
NoNewPrivileges=true
PrivateTmp=true
```

## Kein allgemeines Shell-Interface

Es gibt keinen HTTP-Endpunkt für beliebige Shell-Kommandos. Steuerung erfolgt ausschließlich über definierte SvxLink-Schnittstellen.

## PTY-Rechte

Nur die benötigte Control-PTY soll für den Service schreibbar sein.

Nicht empfohlen:

```text
chmod 666
```

## Eingabevalidierung

Talkgroups und EchoLink Node-IDs werden vor dem Senden validiert.

## Authentifizierung

Eine integrierte Anmeldung ist im Pre-Release noch nicht vorhanden.

Nicht ungeschützt öffentlich exponieren. Geeignete Maßnahmen:
- VPN
- Firewall/IP-Allowlist
- Reverse-Proxy-Authentifizierung
- SSO

## Secrets

Nicht in Git:
- Passwörter
- API-Tokens
- Auth Keys
- SSH/TLS Private Keys
- interne Zugangsdaten
