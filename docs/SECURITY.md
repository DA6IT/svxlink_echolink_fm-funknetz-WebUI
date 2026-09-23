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

Die Anwendung besitzt weiterhin keine eigene Benutzerverwaltung. Der öffentliche Installer schützt die komplette WebUI jedoch standardmäßig mit Apache Basic Auth.

Die Backend-API lauscht ausschließlich auf `127.0.0.1`; externer Zugriff erfolgt über den authentifizierten Apache-Reverse-Proxy.

Zusätzliche Schutzmaßnahmen wie VPN, Firewall/IP-Allowlist oder SSO können weiterhin vorgeschaltet werden.

## Browser-Updater

Browserbasierte Updates verwenden mehrere Schutzebenen:

- Apache Basic Auth vor WebUI und API
- Same-Origin-Prüfung für schreibende Update-Anforderungen
- expliziter CSRF-Guard-Header
- `ProxyPreserveHost On`, damit der ursprüngliche Hostname am Backend erhalten bleibt
- separater rootloser Updater-Service ohne sudo- oder Root-Rechte
- Security-, Backend- und Frontend-Tests vor Aktivierung
- Healthcheck nach Aktivierung
- automatischer Rollback bei fehlgeschlagenem Update

Der Browserprozess führt keine privilegierten Systemkommandos aus. Administrative Systemmigrationen bleiben außerhalb des Web-Updaters.

## Secrets

Nicht in Git:
- Passwörter
- API-Tokens
- Auth Keys
- SSH/TLS Private Keys
- interne Zugangsdaten
