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

Der Installer schützt die gesamte Apache-Site mit Basic Auth. Er fragt einen WebUI-Benutzer und ein mindestens achtstelliges Passwort ab, erzeugt mit `htpasswd -B` einen bcrypt-Hash und schreibt ausschließlich diesen nach `/etc/apache2/svxlink-webui.htpasswd`. Die Datei gehört `root:www-data` und hat Modus `0640`; sie wird gesichert und bei einem Installer-Fehler zurückgerollt. Sie darf niemals ins Repository, in Tickets oder in Logs gelangen.

Basic Auth schützt nicht den Netzwerktransport. Für nicht vertrauenswürdige Netze zusätzlich HTTPS oder VPN einsetzen; Firewall/IP-Allowlist und SSO bleiben mögliche ergänzende Schutzmaßnahmen.

## Secrets

Nicht in Git:
- Passwörter
- API-Tokens
- Auth Keys
- SSH/TLS Private Keys
- interne Zugangsdaten
