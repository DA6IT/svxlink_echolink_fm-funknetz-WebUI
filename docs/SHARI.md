# SHARI-Hardware

## Status

Die WebUI kann das SA818/SA818S-Funkmodul direkt über UART auslesen. Der aktuelle Stand ist bewusst **read-only** und verändert keine Funkparameter.

## Ausgelesene Werte

Verwendete Kommandos: `AT+DMOCONNECT`, `AT+VERSION` und `AT+DMOREADGROUP`.

Angezeigt werden Modul, Firmware, RX-/TX-Frequenz, Kanalraster, TX-/RX-CTCSS, Squelch, serieller Port und Verbindungsstatus.

## API

`GET /api/shari/hardware`

## Serielle Schnittstelle

Standard: `SHARI_SERIAL_PORT=/dev/ttyUSB0`, `SHARI_SERIAL_BAUD=9600`, `SHARI_SERIAL_TIMEOUT=0.8`.

Die Werte können über `/etc/svxlink-webui/environment` überschrieben werden.

## Berechtigungen

Der Dienst `svxlink-webui` benötigt Zugriff auf das serielle Gerät. Empfohlen ist eine eingeschränkte Gruppe wie `svxlink-control` mit Gerätemodus `0660`. `chmod 666` ist nicht erforderlich.

## Proxmox LXC

Bei Betrieb im LXC muss das Gerät vom Proxmox-Host in den Container durchgereicht werden, zum Beispiel mit `pct set <CTID> -dev0 path=/dev/ttyUSB0,gid=<GID>,mode=0660`.

## Nächster Schritt

Noch nicht implementiert sind Schreibzugriffe für Frequenzen, CTCSS, Squelch, Kanalraster, Lautstärke und Filter. Vor Schreibzugriffen sollen Validierung, Vorher/Nachher-Vergleich und Fehlerbehandlung ergänzt werden.
