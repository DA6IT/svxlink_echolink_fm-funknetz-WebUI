# Installation

## Status

Der öffentliche Installer steht als Pre-Release zur Verfügung. Primärer Zielbetrieb ist ein direkt installiertes Debian-/Ubuntu-System, insbesondere Raspberry Pi und vergleichbare Kleinrechner.

## Zielsystem

Aktuell vorgesehen:
- Raspberry Pi oder vergleichbarer Kleinrechner
- Debian oder Ubuntu
- SHARI bzw. kompatible USB-Audio-/PTT-Hardware direkt am System
- bestehende oder durch den Installer eingerichtete SvxLink-Installation
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

## Hardware-Erkennung

Der Installer geht nicht von Proxmox, LXC oder einer bestimmten Virtualisierung aus. Der Standardfall ist direkt angeschlossene Hardware.

Automatisch geprüft bzw. erkannt werden:

- ALSA-Soundkarten für RX und TX
- bevorzugt eine direkt angeschlossene USB-Soundkarte
- HID-Geräte für PTT
- optional eine serielle Schnittstelle für SA818/SA818S
- SvxLink Control- und State-PTY nach dem Start

Für ALSA wird nach Möglichkeit eine stabile Karten-ID wie `plughw:CARD=Device,DEV=0` verwendet, statt eine feste Kartennummer wie `plughw:0,0` vorauszusetzen.

Bei einem Upgrade wird eine bereits vorhandene `AUDIO_DEV`-Konfiguration nicht automatisch verändert. Numerische Konfigurationen wie `plughw:0,0` werden lediglich mit einem Hinweis versehen.

Die serielle SA818/SA818S-Schnittstelle ist optional. Fehlt sie, bleibt die übrige WebUI vollständig nutzbar; lediglich die SHARI-Hardwareanzeige meldet die serielle Schnittstelle als nicht verfügbar.

### Virtualisierung und Container

Bei Betrieb in einer VM oder einem Container müssen die benötigten USB-, Audio-, HID- und gegebenenfalls seriellen Geräte durch die jeweilige Virtualisierungsplattform bereitgestellt werden. Dies ist kein Bestandteil des normalen Installationspfads.

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

## SvxLink Healthcheck

`systemctl is-active svxlink` allein gilt nicht als ausreichender Funktionstest. SvxLink kann als Prozess laufen, obwohl `SimplexLogic` wegen eines Audio- oder Hardwarefehlers nicht initialisiert wurde.

Der Installer prüft deshalb zusätzlich, ob nach dem SvxLink-Start sowohl `DTMF_CTRL_PTY` als auch `STATE_PTY` tatsächlich erzeugt wurden. Fehlen diese, wird die Installation mit den letzten SvxLink-Logmeldungen abgebrochen.

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
