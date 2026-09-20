# Installation

## Status

Der automatische öffentliche Installer befindet sich noch in Entwicklung. Dieses Dokument beschreibt die aktuelle funktionierende Referenzinstallation.

## Zielsystem

Aktuell vorgesehen:
- Debian oder Ubuntu
- bestehende SvxLink-Installation
- systemd
- Apache 2
- Python 3 / venv
- Node.js / npm

## Verzeichnisse

```text
/opt/svxlink-webui              Anwendung
/opt/svxlink-webui/.venv        Python venv
/var/www/new.shart              Frontend-Deployment
/var/lib/svxlink-webui          persistente Daten
/etc/svxlink-webui/environment  Konfiguration
```

## Backend

```bash
cd /opt/svxlink-webui
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

Aktueller systemd-Aufbau:

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

`frontend/dist/` wird in der Referenzinstallation nach `/var/www/new.shart/` kopiert.

## Apache

Aktuell:

```text
Frontend/API-Port: 12345
Backend:           127.0.0.1:12346
```

Beispiel:

```apache
<VirtualHost *:12345>
    DocumentRoot /var/www/new.shart

    <Directory /var/www/new.shart>
        Require all granted
        Options -Indexes
    </Directory>

    ProxyPass /api/ws/ ws://127.0.0.1:12346/api/ws/
    ProxyPassReverse /api/ws/ ws://127.0.0.1:12346/api/ws/

    ProxyPass /api/ http://127.0.0.1:12346/api/
    ProxyPassReverse /api/ http://127.0.0.1:12346/api/
</VirtualHost>
```

Vor Reload:

```bash
apache2ctl configtest
```

## SvxLink State PTY

Beispiel:

```ini
STATE_PTY=/var/lib/svxlink/state/webui_state
```

## SvxLink Control PTY

Beispiel:

```ini
DTMF_CTRL_PTY=/var/lib/svxlink/control/simplex_ctrl
```

Der WebUI-Service benötigt Schreibzugriff auf das tatsächliche PTY-Ziel. Keine feste `/dev/pts/X`-Nummer verwenden; sie kann sich nach einem SvxLink-Neustart ändern.

## EchoLink Event Bridge

Lokaler Handler:

```text
/usr/share/svxlink/events.d/local/EchoLinkWebUI.tcl
```

Die originale `/usr/share/svxlink/events.d/EchoLink.tcl` wird nicht verändert.

Roh-Events:

```text
/var/lib/svxlink/echolink-webui/events.tsv
```

## Ziel des öffentlichen Installers

Der Installer soll:
1. Voraussetzungen prüfen
2. SvxLink-Konfiguration erkennen
3. State-/Control-PTY erkennen
4. EchoLink-Konfiguration erkennen
5. Backups erstellen
6. Service-Benutzer einrichten
7. Python-Umgebung installieren
8. Frontend bauen
9. Apache und systemd konfigurieren
10. PTY-Berechtigungen sicher setzen
11. EchoLink Event Bridge installieren
12. Konfiguration testen
13. Dienste kontrolliert neu starten
14. bei Fehlern zurückrollen

Keine persönlichen Rufzeichen, Node-IDs, Hostnamen oder festen `/dev/pts/*`-Pfade voraussetzen.
