# SvxLink WebUI – Dokumentation

Diese Dokumentation beschreibt den im Repository belegten Stand von Release 0.2.0. Sie ist bewusst keine Betriebsfreigabe: Host-spezifische Pfade, Benutzer, Apache-Regeln und die Erreichbarkeit externer Feeds müssen vor einer Installation geprüft werden.

## Einstieg

- [Architektur und Datenflüsse](architecture.md)
- [API-Referenz](api.md)
- [Sicherheit und Berechtigungsgrenzen](security.md)
- [Installation und Deployment](installation.md)
- [Betrieb, Update, Backup und Rollback](operations.md)
- [FM-Funknetz-Feeds und MQTT](fm-funknetz-mqtt-sources.md)
- [SHARI-Referenzinstallation und Grenzen](shari-reference.md)

## Verbindliche Quellen im Repository

Die Dokumentation wird gegen diese Dateien gepflegt:

- `backend/app/main.py`: API, Allowlisten, Parser und Datenquellen
- `backend/app/state_pty_collector.py`: einwegiger STATE_PTY-Collector
- `backend/app/state_pty_permissions.py`: restriktiver Berechtigungs-Binder
- `.env.example`: deklarierte Konfigurationswerte
- `install.sh`: tatsächlich ausgeführte Installationsschritte
- `deploy/systemd/*.service`: Dienstabhängigkeiten und Sandboxing
- `deploy/apache/svxlink-webui.conf`: Apache-VHost und Proxy-Pfade
- `backend/tests/`: automatisierte Verhaltenstests

## Produktgrenzen in einem Satz

Die WebUI ist ein read-only Dashboard für lokale SvxLink-Statusdaten, lokale Log-Ereignisse, optional normalisierte STATE_PTY-Telemetrie und klar getrennte öffentliche FM-Funknetz-Livedaten. Es gibt keine Schreib-, PTT-, DTMF-, Service-Control-, MQTT- oder EchoLink-Steuerung; Talker-/EchoLink-Daten werden nicht erfunden.
