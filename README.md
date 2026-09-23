# SvxLink WebUI

Eine moderne Weboberfläche für **SvxLink**, **SHARI**, **FM-Funknetz** und **EchoLink**.

Die WebUI bringt die wichtigsten Funktionen deines SvxLink-Systems in den Browser: aktuelle Talkgroups, Favoriten, Buddys, EchoLink-Verbindungen, SHARI-Status und Systeminformationen.

Die Oberfläche ist für Desktop, Tablet und Smartphone ausgelegt.

[English version](README.en.md)

## Was kann die WebUI?

### FM-Funknetz

- aktuell verbundene Talkgroup anzeigen
- aktive Talkgroups live verfolgen
- Talkgroups direkt verbinden
- Talkgroups als Favoriten speichern
- Favoriten direkt von der Startseite aus verwenden
- Buddy-Liste mit Online- und Last-Seen-Status
- bei Online-Buddys direkt auf deren Talkgroup wechseln
- Talkgroup verlassen und zur Standard-TG zurückkehren
- Top-Talkgroups für 24 Stunden, 7 Tage und 30 Tage anzeigen

### EchoLink

- eigenen EchoLink-Node anzeigen
- EchoLink aktivieren und deaktivieren
- aktuelle Verbindungen sehen
- Verbindungen trennen
- nach Rufzeichen oder Node-ID suchen
- ONLINE-, BUSY- und OFFLINE-Status anzeigen
- EchoLink-Nodes als Favoriten speichern
- Favoriten direkt verbinden
- Verbindungshistorie anzeigen

### SHARI und SvxLink

- SvxLink-Status anzeigen
- SHARI-/SA818-Hardware auslesen
- RX- und TX-Frequenz anzeigen
- CTCSS, Squelch und Kanalraster anzeigen
- Audio-, PTT- und PTY-Status prüfen
- Systemzustand in der WebUI anzeigen

Die SHARI-Hardware wird aktuell nur ausgelesen. Funkparameter werden nicht verändert.

## Schnellinstallation

Voraussetzung auf einem frischen Debian-, Ubuntu- oder Raspberry-Pi-OS-System ist `curl`.

Als root:

    apt update
    apt install -y curl

Danach:

    curl -fsSL https://raw.githubusercontent.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI/main/bootstrap.sh | bash

Der Installer führt dich anschließend durch die Einrichtung.

## Was fragt der Installer?

Der Installer erkennt vorhandene Einstellungen soweit möglich und schlägt passende Werte vor.

Abgefragt werden unter anderem:

- Installationspfad
- Port der WebUI
- optionaler Hostname
- Benutzername und Passwort für die WebUI
- Rufzeichen
- FM-Funknetz-Zugangsdaten
- Standard-Talkgroup
- Audio- und PTT-Gerät
- EchoLink-Daten
- SHARI-Schnittstelle

Wenn SvxLink noch nicht installiert ist, kann der Installer die benötigten Pakete ebenfalls installieren.

Eine ausführliche Anleitung findest du unter:

[Installation](docs/INSTALLATION.md)

## Nach der Installation

Am Ende zeigt der Installer die Adresse der WebUI an.

Bei Port 80 zum Beispiel:

    http://192.168.1.100/

oder bei einem konfigurierten Hostnamen:

    http://shari.example.local/

Die WebUI ist mit Benutzername und Passwort geschützt.

## Updates

Updates können direkt in der WebUI installiert werden:

    System → Updates

Öffentliche Installationen verwenden GitHub `main` als Updatequelle.

Ein erneuter manueller Download ist für normale Updates nicht notwendig.

## Sicherheit

Die WebUI kann echte SvxLink-Funktionen steuern.

Sie sollte deshalb nicht ungeschützt aus dem Internet erreichbar sein.

Für externen Zugriff empfehlen sich zum Beispiel:

- VPN
- Firewall oder IP-Allowlist
- Reverse Proxy mit HTTPS
- vorgeschaltetes SSO

Mehr dazu:

[Sicherheit](docs/SECURITY.md)

## Dokumentation

- [Installation](docs/INSTALLATION.md)
- [Konfiguration](docs/CONFIGURATION.md)
- [FM-Funknetz](docs/FM-FUNKNETZ.md)
- [EchoLink](docs/ECHOLINK.md)
- [SHARI](docs/SHARI.md)
- [Sicherheit](docs/SECURITY.md)
- [Datenschutz](docs/PRIVACY.md)

Technische Informationen für Entwickler und Administratoren:

- [Architektur](docs/ARCHITECTURE.md)
- [Changelog](CHANGELOG.md)

## Projektstatus

Die WebUI läuft produktiv auf einem realen SHARI-/SvxLink-System.

Der öffentliche Installer wurde erfolgreich auf einem frischen System getestet.
