# Installation

Die SvxLink WebUI lässt sich direkt von GitHub installieren.

## Voraussetzungen

Unterstützt werden aktuell Debian- und Ubuntu-basierte Systeme, zum Beispiel:

- Debian
- Ubuntu
- Raspberry Pi OS

Die Installation benötigt Root-Rechte.

Auf einem frischen System muss zunächst `curl` vorhanden sein:

    apt update
    apt install -y curl

Alle weiteren benötigten Pakete installiert der Installer selbst.

## Installation starten

Als root:

    curl -fsSL https://raw.githubusercontent.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI/main/bootstrap.sh | bash

Der Installer lädt den aktuellen Stand herunter und führt dich anschließend Schritt für Schritt durch die Einrichtung.

Ein manuelles `git clone` ist nicht notwendig.

## Einrichtung

Bereits vorhandene Einstellungen werden soweit möglich erkannt und vorgeschlagen.

Der Installer fragt unter anderem nach folgenden Punkten.

### WebUI

- Installationspfad
- Port der WebUI
- optionaler Hostname
- Benutzername
- Passwort

Port 80 eignet sich für einen normalen Zugriff ohne Portangabe im Browser.

Alternativ kann auch ein anderer freier Port verwendet werden.

### Station und SvxLink

- Rufzeichen
- Standard-Talkgroup
- Locator und Stationsinformationen
- Audio-Gerät
- PTT-Gerät

### FM-Funknetz

Falls FM-Funknetz verwendet werden soll, werden die benötigten Zugangsdaten und die Standard-Talkgroup abgefragt.

### EchoLink

Falls EchoLink verwendet werden soll, können Rufzeichen, Passwort, Node-ID und weitere Stationsinformationen eingetragen werden.

### SHARI

Der Installer versucht Audio-, HID-/PTT- und serielle Geräte automatisch zu erkennen.

Wenn mehrere Geräte vorhanden sind, kann eine manuelle Auswahl notwendig sein.

## Falls SvxLink noch nicht installiert ist

Wird SvxLink nicht gefunden, bietet der Installer die Installation der benötigten Pakete an.

Danach wird eine passende Grundkonfiguration erstellt.

## Nach der Installation

Am Ende zeigt der Installer die Adresse der WebUI an.

Bei Port 80 zum Beispiel:

    http://192.168.1.100/

Bei einem anderen Port beispielsweise:

    http://192.168.1.100:8080/

Die WebUI ist durch den während der Installation vergebenen Benutzernamen und das Passwort geschützt.

## Updates

Neue Versionen können direkt in der WebUI installiert werden:

    System → Updates

Der öffentliche Installer verwendet GitHub `main` als Updatequelle.

Für normale Updates muss der Curl-Installer nicht erneut gestartet werden.

## HTTPS

Der Installer richtet kein HTTPS-Zertifikat ein.

Im lokalen Netzwerk kann die WebUI direkt über HTTP verwendet werden.

Für Zugriff über das Internet solltest du eine zusätzliche Schutzschicht einsetzen, zum Beispiel:

- VPN
- Reverse Proxy mit HTTPS
- Firewall oder IP-Allowlist
- SSO

## Backup und Wiederherstellung

Vor wichtigen Änderungen legt der Installer Sicherungen an.

Diese befinden sich unter:

    /var/backups/svxlink-webui/

Schlägt eine Installation fehl, versucht der Installer die vorherige Konfiguration automatisch wiederherzustellen.

## Erneuter Installer-Lauf

Der Installer kann erneut gestartet werden:

    curl -fsSL https://raw.githubusercontent.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI/main/bootstrap.sh | bash

Bereits bekannte Werte werden soweit möglich wieder vorgeschlagen.

## Wenn etwas nicht funktioniert

WebUI prüfen:

    systemctl status svxlink-webui

SvxLink prüfen:

    systemctl status svxlink

Updater prüfen:

    systemctl status svxlink-webui-updater

Backend prüfen:

    curl -s http://127.0.0.1:12346/health

Logs der WebUI:

    journalctl -u svxlink-webui -n 100 --no-pager

Logs von SvxLink:

    journalctl -u svxlink -n 100 --no-pager

Weitere Informationen findest du unter:

- [Konfiguration](CONFIGURATION.md)
- [Sicherheit](SECURITY.md)
