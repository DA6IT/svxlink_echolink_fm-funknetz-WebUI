# SvxLink WebUI

Eine responsive Weboberfläche für **SvxLink**, **SHARI**, **FM-Funknetz** und **EchoLink**. Sie kombiniert ein FastAPI-Backend mit einem React/Vite-Frontend und zeigt Live-Daten, Statusinformationen und ausgewählte Steuerfunktionen.

> **Status:** Pre-Release / aktive Entwicklung. Eine funktionierende Referenzinstallation läuft produktiv. Der interaktive Installer ist vorhanden und trägt die Version `1.0.0-pre1`; weitere saubere Installationen auf frischen Debian-/Ubuntu-Systemen stehen noch aus.

[English version](README.en.md)

## Funktionen

- responsive Oberfläche für Desktop, Tablet und Smartphone
- Live-Status, MQTT-Aktivität und Talkgroup-Auswahl für FM-Funknetz
- EchoLink-Verzeichnisstatus, Suche, Favoriten sowie eingehende und ausgehende Verbindungen
- direkte FM-Talkgroup-Steuerung über SvxLink
- EchoLink-Modul aktivieren/deaktivieren und direkte Verbindung zu einem Rufzeichen oder Node
- WebSocket-basierte Statusaktualisierung und persistente Verbindungshistorie

Details: [FM-Funknetz](docs/FM-FUNKNETZ.md) · [EchoLink](docs/ECHOLINK.md)

## Architektur und Standardports

```text
Browser -> Apache :12345 -> Frontend
                         -> /api/ und /api/ws/ -> FastAPI/Uvicorn 127.0.0.1:12346
```

Das Backend bindet standardmäßig nur an Loopback. Die Ports sind im Installer änderbar; `12345` (WebUI) und `12346` (interne API) sind die Vorgaben.

## Installation

Der interaktive Installer liegt als `install.sh` im Repository. Er ist ein Pre-Release (`1.0.0-pre1`), keine Zusicherung für beliebige Systeme. Eine produktive Referenzinstallation existiert; Validierung auf weiteren frischen Debian-/Ubuntu-Systemen steht noch aus.

Schnellstart (als normaler Benutzer geklont):

```bash
git clone https://github.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI.git
cd svxlink_echolink_fm-funknetz-WebUI
sudo ./install.sh
```

Alternativ in einer bereits geöffneten Root-Shell:

```bash
./install.sh
```

Der Installer verlangt `EUID=0` und verwendet innerhalb des Skripts absichtlich kein weiteres `sudo`. Er fragt interaktiv alle standortabhängigen Werte ab. Details, Voraussetzungen, Rückrollverhalten und Einschränkungen: [Installationsanleitung](docs/INSTALLATION.md).

## Sicherheit

Die WebUI ist nicht read-only und kann reale SvxLink-Steuerbefehle auslösen. Das Backend lauscht standardmäßig nur lokal, Apache kann die Oberfläche jedoch im Netz veröffentlichen. Für produktive Systeme geeigneten Zugriffsschutz einsetzen, etwa VPN, Firewall/IP-Allowlist oder Reverse-Proxy-Authentifizierung. Zugangsdaten und Schlüssel niemals in Dokumentation oder öffentliche Beispiele übernehmen.

Details: [Sicherheit](docs/SECURITY.md) · [Datenschutz](docs/PRIVACY.md)

## Projektstatus und bekannte Einschränkungen

FM-Funknetz-Live-Aktivität, Talkgroup-Steuerung, EchoLink-Status/Suche/Verbindungen, REST API, WebSockets und responsive Oberfläche wurden produktiv erprobt. Vor einem allgemeinen Release stehen insbesondere saubere Installationen auf weiteren frischen Systemen, Upgrade-/Uninstall-Workflow, vollständige Authentifizierung und weitere Installer-Erprobung aus.

Die EchoLink-Modulaktivierung verwendet im aktuellen Steuerpfad die Modul-ID `2`. EchoLink-Suche nutzt öffentliche Webquellen; Änderungen deren HTML-Struktur können Anpassungen erfordern.

## Entwicklung

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 12346

cd frontend
npm install
npm run lint
npm run build
```

## Dokumentation

- [Installation](docs/INSTALLATION.md) · [English](docs/INSTALLATION.en.md)
- [Konfiguration](docs/CONFIGURATION.md) · [Architektur](docs/ARCHITECTURE.md)
- [FM-Funknetz](docs/FM-FUNKNETZ.md) · [EchoLink](docs/ECHOLINK.md)
