# Installation

## Status und Geltungsbereich

`install.sh` ist ein interaktiver Pre-Release-Installer in Version `1.0.0-pre2`. Eine funktionierende Referenzinstallation läuft produktiv. Saubere Installationen auf weiteren frischen Debian-/Ubuntu-Systemen sind noch nicht abgeschlossen; daher keine allgemeine Kompatibilitätszusage ableiten.

Unterstützt werden Debian-/Ubuntu-basierte Systeme mit systemd. Der Installer erkennt vorhandenes SvxLink oder bietet an, `svxlink-server` und Kalibrierwerkzeuge zu installieren. Er benötigt Netzwerkzugriff für Paket-, Python- und Node-Abhängigkeiten.

## Schnellstart

Als normaler Benutzer klonen und den Installer einmal mit Root-Rechten starten:

```bash
git clone https://github.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI.git
cd svxlink_echolink_fm-funknetz-WebUI
sudo ./install.sh
```

Oder aus einer bereits geöffneten Root-Shell:

```bash
./install.sh
```

`install.sh` prüft `EUID=0`; innerhalb des Skripts wird absichtlich kein `sudo` verwendet. Das Skript ist interaktiv: Werte prüfen, Eingaben vornehmen und den angezeigten Installationsplan erst dann bestätigen. Niemals Passwörter, AUTH_KEYs, reale Rufzeichen oder Node-IDs in Tickets, Dokumentation oder öffentliche Logs kopieren.

## Abgefragte Werte und Standardwerte

Der Installer übernimmt vorhandene Werte, wenn sie erkannt werden, oder fragt sie ab.

| Bereich | Standard / Verhalten |
| --- | --- |
| WebUI-Quellinstallation | `/opt/svxlink-webui` |
| Apache DocumentRoot | `/var/www/svxlink-webui` |
| Service-Benutzer | `svxlink-webui` (nie `root`) |
| WebUI-Port | `80` |
| Interne API | `127.0.0.1:12346` |
| SvxLink Control PTY | `/var/lib/svxlink/control/simplex_ctrl` |
| SvxLink State PTY | `/var/lib/svxlink/state/webui_state` |
| FM-Funknetz | Rufzeichen, AUTH_KEY, Standard-TG, Locator, Frequenz, Leistung, Antenne, Audio und PTT |
| EchoLink | Rufzeichen, Passwort, Modul-ID (Vorgabe `2`), optionale Node-ID, SYSOP und Standort |

Die UI- und API-Ports müssen unterschiedlich sein. Belegte Ports lösen eine Warnung und Rückfrage aus. Ein Hostname ist optional; ohne Hostname ist Zugriff per IP vorgesehen.

## Was der Installer einrichtet

Nach Bestätigung installiert bzw. prüft der Installer Apache, Python/venv/pip, Node.js/npm, rsync, curl, CA-Zertifikate sowie Audio-/USB-Werkzeuge. Node.js muss mindestens Version 18 sein. Er erzeugt eine Python-venv, installiert Backend-Abhängigkeiten, führt Frontend-Lint und -Build aus und kopiert `frontend/dist/` in den gewählten DocumentRoot.

Er legt den Service-Benutzer und die Gruppen `svxlink-state-reader` und `svxlink-control` an, richtet die WebUI- und State-Collector-Dienste ein und konfiguriert Apache als Reverse Proxy einschließlich WebSocket-Proxy. Das Backend bindet nur an `127.0.0.1`; Apache bedient die WebUI auf dem gewählten UI-Port.

Für SvxLink setzt bzw. ergänzt der Installer `DTMF_CTRL_PTY` und `STATE_PTY`. Der State-Collector schreibt normalisierte Daten nach `/run/svxlink-webui/state.jsonl`. Die PTY-Berechtigungen werden über überwachte systemd-Units gesetzt; keine feste `/dev/pts/N`-Nummer annehmen, weil sich das Ziel nach SvxLink-Neustarts ändern kann.

Bei gewünschter FM-Funknetz-Konfiguration richtet der Installer `ReflectorLogic` und `NetLink` ein. Direkte FM-Talkgroup-Auswahl und das Verlassen einer Talkgroup bzw. die Rückkehr zur Standard-TG erfolgen in der WebUI über SvxLink. Bei gewünschter EchoLink-Konfiguration schreibt er `ModuleEchoLink.conf` und installiert die lokale Event-Bridge `/usr/share/svxlink/events.d/local/EchoLinkWebUI.tcl`; die originale EchoLink-Eventdatei wird nicht verändert. Die WebUI kann das EchoLink-Modul steuern sowie direkt zu Rufzeichen oder Nodes verbinden und Verbindungen trennen.

## Sicherung, Prüfung und Rückrollen

Vor Änderungen sichert der Installer die betroffenen Konfigurations-, systemd- und Apache-Dateien in einem zeitgestempelten Verzeichnis unter `/var/backups/svxlink-webui/`. Bei einem Fehler werden diese Dateien, Apache-Aktivierungen und Dienste soweit möglich zurückgerollt. Bereits installierte Pakete, Benutzer und Gruppen werden absichtlich nicht entfernt.

Vor dem Neustart prüft der Installer Python-Dateien, führt `pytest backend/app/test_api.py -q` aus und testet die Apache-Konfiguration. Danach startet er SvxLink, die WebUI-Dienste und Apache neu und prüft sowohl `/health` auf der Loopback-API als auch die WebUI über Apache.

## Sicherheits- und Betriebsgrenzen

- Die WebUI kann reale Steuerbefehle senden. Der Installer fragt einen WebUI-Benutzer und ein mindestens achtstelliges Passwort ab und schützt die gesamte Apache-Site mit Basic Auth. Der bcrypt-Hash liegt ausschließlich in `/etc/apache2/svxlink-webui.htpasswd` (Owner `root`, Gruppe `www-data`, Modus `0640`); weder Klartextpasswort noch Hash gehören ins Repository. Für nicht vertrauenswürdige Netze zusätzlich HTTPS oder VPN einsetzen.
- SvxLink- und EchoLink-Konfigurationen mit Zugangsdaten werden auf `root:svxlink` und Modus `0640` eingeschränkt, sofern die Gruppe existiert. Die Laufzeitumgebung wird als `root:<WebUI-Gruppe>` mit `0640` geschrieben.
- EchoLink kann abhängig von Netzwerk und Router weiterhin eingehende UDP-Ports `5198/5199` benötigen.
- Das Skript aktualisiert vorhandene Konfigurationen gezielt, ist aber kein vollständiger Upgrade- oder Uninstall-Workflow. Vor produktiven Änderungen Backups prüfen und die interaktiven Angaben sorgfältig kontrollieren.

Weitere Themen: [Konfiguration](CONFIGURATION.md), [Architektur](ARCHITECTURE.md), [Sicherheit](SECURITY.md).
