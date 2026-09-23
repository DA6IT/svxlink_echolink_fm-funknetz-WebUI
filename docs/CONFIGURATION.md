# Konfiguration

Die meisten Einstellungen werden bereits während der Installation abgefragt.

Für einen normalen Betrieb musst du nach einer erfolgreichen Installation in der Regel keine Dateien von Hand bearbeiten.

## WebUI

Während der Installation legst du fest:

- Port
- optionalen Hostnamen
- Benutzername
- Passwort

Diese Werte bestimmen, wie du die WebUI später im Browser erreichst.

## FM-Funknetz

Für FM-Funknetz werden unter anderem benötigt:

- Rufzeichen
- Zugangsdaten
- Standard-Talkgroup

Die aktuell verbundene Talkgroup kann später direkt über die WebUI geändert werden.

## EchoLink

Für EchoLink können folgende Werte eingerichtet werden:

- EchoLink-Rufzeichen
- Passwort
- Node-ID
- Name des Sysops
- Standort

Bereits vorhandene EchoLink-Einstellungen werden soweit möglich erkannt.

## Audio und PTT

Der Installer versucht geeignete Audio- und PTT-Geräte automatisch zu erkennen.

Bei mehreren Geräten solltest du kontrollieren, ob das richtige Gerät ausgewählt wurde.

## SHARI

Der serielle Anschluss des SHARI-/SA818-Moduls wird ebenfalls automatisch gesucht.

Typische Geräte sind:

    /dev/ttyUSB0

oder ein stabiler Pfad unter:

    /dev/serial/by-id/

Wenn möglich, ist ein `/dev/serial/by-id/`-Pfad robuster als eine wechselnde `ttyUSB`-Nummer.

## Erweiterte Einstellungen

Die Laufzeitkonfiguration befindet sich unter:

    /etc/svxlink-webui/environment

Diese Datei ist hauptsächlich für fortgeschrittene Anpassungen gedacht.

Für einen normalen Betrieb solltest du sie nur ändern, wenn du genau weißt, welche Einstellung du anpassen möchtest.

## Änderungen nach der Installation

Viele alltägliche Funktionen werden direkt über die WebUI gesteuert, zum Beispiel:

- Talkgroup wechseln
- Talkgroup verlassen
- EchoLink aktivieren
- EchoLink verbinden oder trennen
- Favoriten verwalten
- Buddys verwalten

Für diese Funktionen ist keine manuelle Dateibearbeitung notwendig.

## Weitere Hilfe

- [Installation](INSTALLATION.md)
- [FM-Funknetz](FM-FUNKNETZ.md)
- [EchoLink](ECHOLINK.md)
- [SHARI](SHARI.md)
