# SvxLink WebUI

Eine moderne, responsive Weboberfläche für **SvxLink**, **SHARI**, **FM-Funknetz** und **EchoLink**.

Die Anwendung kombiniert ein FastAPI-Backend mit einem React/Vite-Frontend und stellt Live-Daten, Statusinformationen und ausgewählte Steuerfunktionen im Browser bereit.

> **Status:** Pre-Release / aktive Entwicklung.
> Die WebUI läuft bereits produktiv auf einem realen SvxLink-/SHARI-System. Ein öffentlicher Pre-Release-Installer ist bereits vorhanden und wird weiter getestet.

[English version](README.en.md)

## Funktionen

### Übersicht
- responsive Oberfläche für Desktop, Tablet und Smartphone
- Live-Status für FM-Funknetz und EchoLink
- direkte Navigation zu den Betriebsbereichen
- keine erfundenen Betriebsdaten im Produktionsmodus

### FM-Funknetz
- aktuelle lokale Talkgroup
- aktive Talkgroups in Echtzeit
- MQTT-basierte Live-Aktivität
- Anzeige des aktuellen Rufzeichens
- Talkgroup-Namen
- eigene Talkgroup-Favoriten
- direkte Talkgroup-Auswahl über SvxLink
- Talkgroup verlassen / Standard-TG wiederherstellen
- Top-Talkgroups für 24 Stunden, 7 Tage und 30 Tage
- Node- und Aktivitätsinformationen
- Buddy-/Last-Seen-Funktionen
- WebSocket-basierte Statusaktualisierung

Details: [docs/FM-FUNKNETZ.md](docs/FM-FUNKNETZ.md)

### EchoLink
- eigenes EchoLink-Rufzeichen und eigene Node-ID
- EchoLink Directory Status
- EchoLink-Modul aktivieren/deaktivieren
- aktuelle eingehende und ausgehende Verbindungen
- Verbindungsdauer und Trennen
- Suche nach Rufzeichen oder Node-ID
- ONLINE / BUSY / OFFLINE
- registrierte, aber aktuell nicht eingeloggte Nodes werden erkannt
- EchoLink-Nodes als Favoriten speichern
- Favoriten direkt verbinden
- Live-Status gespeicherter Nodes
- persistente Verbindungshistorie

Details: [docs/ECHOLINK.md](docs/ECHOLINK.md)

## Architektur

```text
Browser
   │
   ▼
Apache :12345
   │
   ├── React/Vite Frontend
   ├── /api/    ─────────► FastAPI/Uvicorn 127.0.0.1:12346
   └── /api/ws/ ─────────► WebSockets
```

Das Backend bindet nur an Loopback. Apache liefert das Frontend aus und übernimmt Reverse Proxy und WebSocket Proxy.

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Referenzpfade

```text
/opt/svxlink-webui              Anwendung
/opt/svxlink-webui/backend      Backend
/opt/svxlink-webui/frontend     Frontend
/var/www/new.shart              aktuelles DocumentRoot
/var/lib/svxlink-webui          persistente WebUI-Daten
/etc/svxlink-webui/environment  Laufzeitkonfiguration
```

Diese Pfade entsprechen der aktuellen Referenzinstallation. Der spätere Installer soll Pfade soweit möglich erkennen oder konfigurierbar machen.

## Installation

Der generische öffentliche Installer ist noch nicht fertig.

Aktueller Aufbau: [docs/INSTALLATION.md](docs/INSTALLATION.md)

## Konfiguration

[docs/CONFIGURATION.md](docs/CONFIGURATION.md)

## Sicherheit

Die WebUI ist **nicht read-only**. Sie kann reale SvxLink-Steuerbefehle auslösen.

Sie sollte daher nicht ungeschützt öffentlich erreichbar sein. Empfohlen werden z. B. VPN, Firewall/IP-Allowlist, Reverse-Proxy-Authentifizierung oder SSO.

Details: [docs/SECURITY.md](docs/SECURITY.md)

## Datenschutz und öffentliche Beispiele

Live-Daten dürfen im Betrieb angezeigt werden. In README, Screenshots, Demo-Daten und festen UI-Platzhaltern sollen jedoch keine zufällig beobachteten fremden Rufzeichen oder fremden EchoLink Node-IDs dauerhaft eingebaut werden.

Geeignete statische Beispiele:

```text
DA6IT
DA6IT-L
DB0XYZ-R
<CALLSIGN>
<NODE_ID>
<TALKGROUP>
```

Details: [docs/PRIVACY.md](docs/PRIVACY.md)

## Entwicklung

Backend:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

PYTHONPATH=backend .venv/bin/uvicorn app.main:app   --host 127.0.0.1   --port 12346
```

Frontend:

```bash
cd frontend
npm install
npm run build
npm run lint
```

## Projektstatus

Bereits produktiv getestet:
- FM-Funknetz MQTT und Live-Aktivität
- Talkgroup-Auswahl und Favoriten
- Top-Talkgroups
- EchoLink Directory Status und Suche
- EchoLink ONLINE/BUSY/OFFLINE
- EchoLink Favoriten
- EchoLink Connect/Disconnect
- EchoLink History
- FastAPI REST API und WebSockets
- responsive Oberfläche

Vor dem ersten öffentlichen Release:
- generischen Installer fertigstellen
- Upgrade- und Uninstall-Workflow
- automatische SvxLink-Erkennung vervollständigen
- Authentifizierung/Autorisierung
- Tests auf frischen Systemen
- öffentliche UI-Beispiele/Screenshots anonymisieren
- Lizenz/Release-Informationen finalisieren

## Bekannte Pre-Release-Einschränkungen

Die EchoLink-Modulaktivierung verwendet im aktuellen Steuerpfad noch die Modul-ID `2`. Vor dem öffentlichen Release muss diese vollständig aus `ModuleEchoLink.conf` übernommen werden.

Die EchoLink-Suche verwendet öffentliche EchoLink-Webquellen. Änderungen an deren HTML-Struktur können eine Anpassung des Backend-Providers erfordern.

## Dokumentation

- [Installation](docs/INSTALLATION.md)
- [Konfiguration](docs/CONFIGURATION.md)
- [Architektur](docs/ARCHITECTURE.md)
- [FM-Funknetz](docs/FM-FUNKNETZ.md)
- [EchoLink](docs/ECHOLINK.md)
- [Sicherheit](docs/SECURITY.md)
- [Datenschutz / öffentliche Beispiele](docs/PRIVACY.md)
