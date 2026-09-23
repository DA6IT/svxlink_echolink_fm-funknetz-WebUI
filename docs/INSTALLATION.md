# Installation

Die SvxLink WebUI kann direkt aus dem öffentlichen GitHub-Repository installiert werden.

Der empfohlene Weg ist der Bootstrap-Installer. Er lädt automatisch den vollständigen aktuellen `main`-Stand herunter und startet anschließend den interaktiven Installer.

## Unterstützte Systeme

Der Installer ist aktuell für Debian- und Ubuntu-basierte Systeme vorgesehen.

Typische Einsatzsysteme sind:

- Debian
- Ubuntu
- Raspberry Pi OS auf Debian-Basis
- vergleichbare Debian-basierte Systeme

Die Installation benötigt Root-Rechte.

## Voraussetzungen

Für den Start des Bootstrap-Installers wird lediglich `curl` benötigt.

Auf einem frischen Debian-/Ubuntu-System:

    apt update
    apt install -y curl

Danach kann die eigentliche Installation gestartet werden.

Weitere benötigte Pakete werden vom Installer automatisch installiert.

Dazu gehören unter anderem:

- Apache
- Python 3
- Python venv und pip
- Node.js
- npm
- Git
- rsync
- curl
- ACL-Werkzeuge
- ALSA-Werkzeuge
- USB-Werkzeuge

Falls SvxLink noch nicht installiert ist, kann der Installer auch die benötigten SvxLink-Pakete installieren.

Der Installer führt vor der Paketinstallation selbst ein `apt-get update` aus.

## Schnellinstallation

Als `root`:

    curl -fsSL https://raw.githubusercontent.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI/main/bootstrap.sh | bash

Alternativ:

    sudo bash -c 'curl -fsSL https://raw.githubusercontent.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI/main/bootstrap.sh | bash'

Der Bootstrap lädt den vollständigen Projektstand temporär von GitHub herunter und startet anschließend `install.sh`.

Ein manuelles `git clone` ist für eine normale Installation nicht erforderlich.

## Was der Bootstrap macht

Der Bootstrap:

1. prüft, ob er mit Root-Rechten läuft
2. prüft die benötigten Bootstrap-Werkzeuge
3. lädt den aktuellen `main`-Stand von GitHub als Archiv
4. prüft das heruntergeladene Archiv
5. entpackt das Projekt in ein temporäres Verzeichnis
6. startet den interaktiven Installer
7. entfernt die temporären Installationsdateien anschließend wieder

Die eigentliche Installation erfolgt weiterhin durch `install.sh`.

## Interaktive Konfiguration

Während der Installation werden die für das jeweilige System benötigten Werte abgefragt.

Dazu können gehören:

- Installationspfad
- Apache DocumentRoot
- WebUI-Systembenutzer
- Hostname bzw. Zugriff über IP-Adresse
- WebUI-Port
- interner API-Port
- Benutzername und Passwort für die WebUI
- SvxLink-Rufzeichen
- FM-Funknetz-Zugangsdaten
- Standard-Talkgroup
- Locator und Stationsdaten
- Audio-Gerät
- PTT/HID-Gerät
- EchoLink-Konfiguration
- SHARI-UART

Bereits vorhandene Werte werden soweit möglich erkannt und als Vorgabe angeboten.

## WebUI-Zugriff

Standardmäßig läuft die WebUI über Apache.

Wenn Port 80 verwendet wird:

    http://SERVER-IP/

oder bei konfiguriertem Hostnamen:

    http://HOSTNAME/

Die WebUI ist mit Apache Basic Auth geschützt.

Benutzername und Passwort werden während der Installation festgelegt.

## Kein HTTPS durch den Installer

Der Installer richtet aktuell bewusst kein TLS/HTTPS ein.

Die WebUI läuft standardmäßig über HTTP.

Falls der Zugriff über ein nicht vertrauenswürdiges Netz erfolgen soll, sollte zusätzlich eine geeignete Schutzschicht verwendet werden, zum Beispiel:

- VPN
- Reverse Proxy mit HTTPS
- Firewall bzw. IP-Allowlist
- vorgeschaltetes SSO

## Installation von SvxLink

Wenn auf dem System noch kein SvxLink erkannt wird, bietet der Installer die Installation von SvxLink an.

Bei bereits vorhandenem SvxLink versucht der Installer bestehende Werte zu erkennen und weiterzuverwenden.

Der Installer verändert unter anderem die für die WebUI benötigten SvxLink-Einstellungen für:

- Control PTY
- State PTY
- FM-Funknetz
- EchoLink
- Audio/PTT-Anbindung

Vor Änderungen werden Sicherungen erstellt.

## Hardware-Erkennung

Der Installer versucht geeignete Hardware automatisch zu erkennen.

Dazu gehören insbesondere:

- ALSA-Audio-Geräte
- HID/PTT-Geräte
- SHARI-/SA818-UART
- vorhandene SvxLink-Konfiguration

Bei mehreren oder nicht eindeutig erkennbaren Geräten kann eine manuelle Auswahl bzw. Anpassung erforderlich sein.

## Installierte Komponenten

Typische Installationspfade:

    /opt/svxlink-webui
    /etc/svxlink-webui
    /var/lib/svxlink-webui
    /var/lib/svxlink-webui-update
    /var/lib/svxlink-webui-updater

Zusätzlich werden systemd-Units für die WebUI, den State-Collector und den Updater eingerichtet.

Apache übernimmt:

- Auslieferung des Frontends
- Reverse Proxy zum FastAPI-Backend
- WebSocket Proxy
- Basic Authentication

Das FastAPI-Backend bindet nur lokal auf `127.0.0.1`.

## Automatische Updates über die WebUI

Eine Installation über den öffentlichen Bootstrap verwendet GitHub als Updatequelle:

    https://github.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI.git

Der Update-Kanal ist standardmäßig:

    main

Neue Stände können dadurch direkt in der WebUI erkannt und installiert werden.

Der Updater läuft getrennt vom eigentlichen WebUI-Prozess und verwendet einen eingeschränkten Update-Benutzer.

## Updates

Nach einem veröffentlichten neuen Stand muss auf dem Zielsystem normalerweise kein neuer `curl`-Installer ausgeführt werden.

Updates erfolgen über:

    WebUI -> System -> Updates

Der Updater prüft den konfigurierten `main`-Stand und installiert neue Versionen kontrolliert.

## Backups und Rollback

Vor relevanten Änderungen legt der Installer Sicherungen unter folgendem Pfad an:

    /var/backups/svxlink-webui/

Wenn die Installation nach Aktivierung der Änderungen fehlschlägt, versucht der Installer die zuvor gesicherten Konfigurationsdateien wiederherzustellen.

Installierte Pakete, Benutzer und Gruppen werden bei einem Rollback absichtlich nicht automatisch entfernt.

## Installer-Werte

Die während der Installation gewählten Werte werden für spätere Installations- bzw. Upgrade-Läufe gespeichert.

Datei:

    /root/.svxlink-webui-installer.env

Die Datei gehört `root` und wird mit Modus `0600` gespeichert.

Dadurch können erkannte bzw. bereits eingegebene Werte bei späteren Installer-Läufen wieder vorgeschlagen werden.

## Wichtige Dienste

Nach erfolgreicher Installation sollten insbesondere folgende Dienste aktiv sein:

    systemctl status svxlink
    systemctl status svxlink-webui
    systemctl status svxlink-webui-updater
    systemctl status apache2

Je nach Hardwarezustand zusätzlich:

    systemctl status svxlink-webui-state-collector

## Schnelle Diagnose

Backend prüfen:

    curl -s http://127.0.0.1:12346/health

WebUI über Apache prüfen:

    curl -I http://127.0.0.1/

Ohne Zugangsdaten ist hier bei aktivierter Basic Authentication ein HTTP-Status `401 Unauthorized` korrekt.

SvxLink prüfen:

    systemctl --no-pager --full status svxlink

WebUI prüfen:

    systemctl --no-pager --full status svxlink-webui

Updater prüfen:

    systemctl --no-pager --full status svxlink-webui-updater

## Logs

WebUI:

    journalctl -u svxlink-webui -n 100 --no-pager

Updater:

    journalctl -u svxlink-webui-updater -n 100 --no-pager

State Collector:

    journalctl -u svxlink-webui-state-collector -n 100 --no-pager

SvxLink:

    journalctl -u svxlink -n 100 --no-pager

Apache:

    tail -100 /var/log/apache2/svxlink-webui-error.log

## Neuinstallation / erneuter Installer-Lauf

Der Bootstrap kann grundsätzlich erneut gestartet werden:

    curl -fsSL https://raw.githubusercontent.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI/main/bootstrap.sh | bash

Für reguläre Updates sollte jedoch die integrierte Updatefunktion der WebUI verwendet werden.

## Entwicklung vs. öffentliche Installation

Der Entwicklungsworkflow des Projekts ist getrennt von der öffentlichen Installation.

Öffentliche Systeme beziehen Installation und Updates aus GitHub.

Der Entwicklungsstand wird zunächst im führenden Entwicklungsrepository gepflegt und anschließend nach GitHub gespiegelt.

Dadurch benötigt ein öffentlich installiertes System keinen Zugriff auf interne Entwicklungsinfrastruktur.

## Sicherheitshinweis

Die WebUI kann reale SvxLink-Funktionen steuern und ist daher keine reine Statusseite.

Sie sollte nicht ohne Schutz öffentlich ins Internet gestellt werden.

Weitere Informationen:

- [SECURITY.md](SECURITY.md)
- [CONFIGURATION.md](CONFIGURATION.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
