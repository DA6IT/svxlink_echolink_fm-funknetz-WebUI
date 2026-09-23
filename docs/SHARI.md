# SHARI

Die WebUI kann Informationen direkt aus einem angeschlossenen SHARI-/SA818-Funkmodul auslesen.

## Angezeigte Informationen

Je nach Hardware werden unter anderem angezeigt:

- Modul
- Firmware
- RX-Frequenz
- TX-Frequenz
- Kanalraster
- TX-CTCSS
- RX-CTCSS
- Squelch
- serielle Schnittstelle
- Verbindungsstatus

## Nur Anzeige

Die SHARI-Konfiguration ist aktuell bewusst read-only.

Die WebUI verändert keine Frequenzen oder anderen Funkparameter.

Damit kann ein bereits eingerichteter SHARI sicher überwacht werden, ohne seine bestehende Konfiguration zu verändern.

## Serielle Verbindung

Der Installer versucht die serielle Schnittstelle automatisch zu erkennen.

Typische Geräte sind:

    /dev/ttyUSB0

oder ein Pfad unter:

    /dev/serial/by-id/

Wenn mehrere serielle Geräte vorhanden sind, kann eine manuelle Auswahl notwendig sein.

## Proxmox und LXC

Wenn die WebUI in einem LXC-Container läuft, muss die SHARI-Hardware vom Proxmox-Host in den Container durchgereicht werden.

Das betrifft je nach Aufbau:

- USB-Audio
- HID/PTT
- serielle Schnittstelle

Die Geräte müssen innerhalb des Containers sichtbar und für die benötigten Dienste zugreifbar sein.
