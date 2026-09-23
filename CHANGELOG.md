# Changelog

## 0.8.0-dev.3 — Browser updater ready

### Neu

- Browserbasierte Updates sind nach erfolgreicher Security- und Rootless-Validierung standardmäßig freigeschaltet.
- Clean-Install-Verifikation prüft Basic Auth, `ProxyPreserveHost On` und den CSRF-/Same-Origin-Guard.

### Sicherheit

- Browser-Updates bleiben durch Apache Basic Auth, Same-Origin-Prüfung und expliziten CSRF-Header geschützt.
- Die eigentliche Installation erfolgt weiterhin ausschließlich über den separaten rootlosen Updater-Service.
- Der vollständige Updatepfad inklusive Healthcheck und Rollback wurde live validiert.

### Installation

- Neue Installationen setzen `SVXLINK_WEBUI_UPDATE_ENABLED=true`.
- Apache erhält weiterhin `ProxyPreserveHost On`, damit die Same-Origin-Prüfung den ursprünglichen Hostnamen sieht.

## 0.8.0-dev.2 — Browser updater security

### Sicherheit

- Same-Origin-Prüfung für das Starten eines Browser-Updates.
- Schreibender Update-Request benötigt zusätzlich einen expliziten CSRF-Guard-Header.
- Browser-Updater bleibt bis zum Abschluss der Auth-/Security-Tests administrativ deaktiviert.

### Entwicklung

- Security-Hardening erfolgt getrennt auf `feature/browser-updater-security`.


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
