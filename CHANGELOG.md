# Changelog

## 0.8.0-dev.1 — Rootless updater validation

- Vollständiger rootloser Updatepfad live validiert.


Alle wesentlichen Änderungen der SvxLink WebUI werden hier dokumentiert.

## 0.8.0-dev — Unreleased

### Neu

- Sicherer Update-Workflow mit getrenntem Staging.
- Automatische Backend-, Security- und Frontend-Tests vor Aktivierung.
- Versionierte Python-Runtimes über `.venv-current`.
- Kontrollierter Backend-Selbstrestart ohne sudo/root.
- Frontend-Backup, Healthcheck und automatischer Rollback.

- Browserbasiertes Update-Center im Bereich System.
- Anzeige der installierten Version und Git-Revision.
- Prüfung des konfigurierten Update-Kanals.
- Vorbereitung für vollständig rootlose WebUI-Updates.
- Prüfung, ob Anwendung, Git-Checkout, Datenverzeichnis und Frontend-Deployment durch den WebUI-Benutzer aktualisiert werden können.

### Geändert

- Die Anwendungsversion wird künftig zentral aus der Datei `VERSION` gelesen.
- Normale WebUI-Updates sollen ohne SSH und ohne Root-Rechte möglich sein.
- Systemänderungen an Apache, systemd, `/etc`, Betriebssystempaketen oder Hardwareberechtigungen bleiben ausdrücklich außerhalb des Web-Updaters.

### Sicherheit

- Der Browser-Updater erhält keine sudo- oder Root-Rechte.
- Die eigentliche Update-Installation bleibt während der ersten Entwicklungsstufe deaktiviert.
