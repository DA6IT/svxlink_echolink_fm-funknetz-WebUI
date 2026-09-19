# Betrieb, Update, Backup und Rollback

## Regelbetrieb und Diagnose

| Symptom | Prüfschritte |
|---|---|
| Backend nicht erreichbar | `systemctl status svxlink-webui`; `journalctl -u svxlink-webui -b`; lokal `curl --fail http://127.0.0.1:12346/health`. |
| Apache liefert Fehler | `apache2ctl configtest`; Apache Error- und Access-Log des VHosts prüfen; anschließend `/health` über Port 12345 prüfen. |
| Lokale Daten fehlen | Leserechte des Dienstnutzers auf die konfigurierten Node-/Config-/Log-Dateien prüfen, nicht die Anwendung als root ausführen. Nicht vorhandene Quellen sind erwartungsgemäß „unavailable“. |
| STATE_PTY fehlt | `systemctl status svxlink-state-pty-permissions svxlink-state-collector`; Journal beider Dienste; Rohpfad prüfen. Keine globalen `tty`-Rechte setzen. |
| FM-Funknetz fehlt | API meldet Verfügbarkeit getrennt. DNS-/HTTPS-Erreichbarkeit und die unveränderten allowlist-konformen URLs prüfen. Redirects sind absichtlich nicht erlaubt. |
| Falsche lokale TG | `SVXLINK_TG_ALLOWLIST` und neue passende SvxLink-Logzeile prüfen. Ein `DEFAULT_TG` ist keine bestätigte Auswahl. |

Nützliche Befehle:

```bash
sudo journalctl -u svxlink-webui -u svxlink-state-collector -u svxlink-state-pty-permissions -b
curl --silent --show-error http://127.0.0.1:12346/api/status
curl --silent --show-error http://127.0.0.1:12346/api/rf/status
```

Die API liefert bei Ausfall lokaler oder externer Quellen eine kontrollierte Nichtverfügbarkeit. Das ist kein Anlass, Demo-Modus oder erfundene Daten in Produktion einzuschalten.

## Testen vor Auslieferung

Im Repository:

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests
(cd frontend && npm run lint && npm run build)
```

Falls keine bestehende Virtualenv vorhanden ist, zunächst die in der [Installation](installation.md) beziehungsweise README beschriebenen Abhängigkeiten installieren. Die Backend-Tests prüfen unter anderem Allowlisten, fehlende `/api/config`, Feed-URL-Validierung, Redirect-Verhalten, Logparser und die opt-in STATE_PTY-Verarbeitung. Die Frontend-Prüfung führt TypeScript-Check und Vite-Build aus.

## Update

1. Wartungsfenster und Rückfallstand bestimmen; lokale Environment-Datei und Apache-Ergänzungen sichern.
2. Arbeitsbaum prüfen und den gewünschten, überprüften Commit auschecken.
3. Backend-Abhängigkeiten und Frontend-Build reproduzierbar aktualisieren. Bei Nutzung des Lieferwegs wird `sudo ./install.sh` erneut ausgeführt; das kann die Environment-Datei aus `.env.example` überschreiben. Deshalb sie vorher sichern und nachher diffen.
4. `apache2ctl configtest`, Backend-Tests und Frontend-Build ausführen.
5. Dienste nacheinander neu starten und `/health` über Loopback und Apache prüfen.

Beispiel für eine Sicherung der Betreiberkonfiguration vor Neuinstallation:

```bash
sudo install -d -m 0750 /var/lib/svxlink-webui/backups/pre-update
sudo cp -a /etc/svxlink-webui/environment /var/lib/svxlink-webui/backups/pre-update/
sudo cp -a /etc/apache2/sites-available/svxlink-webui.conf /var/lib/svxlink-webui/backups/pre-update/
```

Nur erforderliche Dateien sichern; keine Secrets in Git, Tickets oder Logs kopieren. Eine zukünftige, nicht mitgelieferte `control.env` wäre separat und restriktiv zu behandeln.

## Rollback

1. Auf den zuvor getesteten Git-Commit oder ein vorheriges Paketartefakt zurückgehen.
2. Die gesicherte Environment- und ggf. Apache-Konfiguration wiederherstellen.
3. Bei einer Version mit geändertem Schema die Kompatibilität der STATE-Snapshot-Verarbeitung prüfen; das Snapshot ist Laufzeitstatus und kein langfristiges Datenarchiv.
4. `apache2ctl configtest` ausführen, dann `systemctl restart svxlink-webui` und bei Bedarf den Collector.
5. Mit `/health`, `/api/status` und Journal prüfen; erst danach Apache neu laden.

Rollback bedeutet nicht, alte Zugriffsrechte oder unsichere PTY-Workarounds zurückzuholen. Bei Berechtigungsproblemen bleibt der sichere Zustand „Telemetry unavailable“.

Weiter: [SHARI-Referenz und Grenzen](shari-reference.md) · [FM-Funknetz](fm-funknetz-mqtt-sources.md)
