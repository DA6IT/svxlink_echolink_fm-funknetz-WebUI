# Installation und Deployment

## Voraussetzungen

Die Installationsroutine ist für Debian/Ubuntu-artige Hosts geschrieben und verlangt root sowie verfügbare Befehle `python3`, `npm` und `apache2ctl`. SvxLink muss vorhanden sein, wenn reale lokale Statusdaten genutzt werden sollen. Das Skript prüft nicht die Installation aller Betriebssystempakete; diese müssen vorab bereitgestellt werden. Port `12345` muss frei sein.

Vor dem Start ist ein Review erforderlich: Zielhost, Apache-Exposition, TLS-/Netzgrenze, Zugriffsrechte auf lokale Eingabedateien sowie der gewünschte Stand der optionalen STATE_PTY-Telemetrie.

## Installation

```bash
git clone https://git.da6it.de/hermes/svxlink-webui.git
cd svxlink-webui
sudo ./install.sh
```

Das Skript erstellt, falls fehlend, `svxlink-webui`, die Gruppe `svxlink-state-reader` und `svxlink-state-collector`. Es legt `/opt/svxlink-webui`, `/etc/svxlink-webui`, `/var/lib/svxlink-webui/backups` und `/var/www/new.shart` an. Anschließend kopiert es Backend und Frontend-Artefakte, erstellt eine Python-Virtualenv, installiert Python-Abhängigkeiten, führt `npm ci && npm run build` aus und installiert die Unit- und Apache-Dateien.

Es aktiviert Apache-Module `proxy`, `proxy_http`, `proxy_wstunnel`, `headers` und `rewrite`, aktiviert den Site-Namen `svxlink-webui`, führt `apache2ctl configtest` aus, aktiviert/startet das Backend und lädt Apache neu. Es aktiviert den Berechtigungs-Binder, aber nicht den optionalen Collector. Bestehende SvxLink-Konfigurationen oder andere vHosts werden durch das Skript nicht editiert.

Der statische DocumentRoot ist derzeit `/var/www/new.shart`; dies ist der tatsächliche deklarierte Wert und kein Platzhalter.

## Konfiguration per Environment

Die Unit lädt optional `/etc/svxlink-webui/environment`. Der Installer kopiert `.env.example` dorthin mit Modus `0644`. Da diese Datei nur nicht geheime, read-only Pfade und Flags enthalten soll, gehören keine Credentials hinein. Bei lokalen Anforderungen kann der Betreiber die Dateirechte zusätzlich begrenzen, sofern der Dienstnutzer weiterhin lesen kann.

| Variable | Standard / Bedeutung |
|---|---|
| `SVXLINK_WEBUI_DEMO` | `false`; nur für klar gelabelte lokale Demo. |
| `SVXLINK_CONFIG_PATH`, `SVXLINK_NODE_INFO_PATH`, `SVXLINK_LOG_PATH`, `SVXLINK_PID_PATH`, `SVXLINK_SERVICE_NAME` | Lokale read-only Quellen bzw. Dienstname. |
| `SVXLINK_TG_ALLOWLIST` | Kommagetrennte numerische TGs; leer bedeutet keine lokale TG-Bestätigung. |
| `SVXLINK_STATE_PTY_ENABLED` | `false`; schaltet nur das Lesen des normalisierten Snapshots frei. |
| `SVXLINK_STATE_PTY_PATH` | Standard `/run/svxlink-webui/state.jsonl`. |
| `SVXLINK_STATE_PTY_RAW_PATH` | Host-spezifischer Eingabepfad für Binder und Collector. |
| `SVXLINK_LOCAL_EVENT_INPUT_ENABLED` | `false`; erlaubt keine HTTP-Eingaben. |
| `FM_FUNKNETZ_LIVE_URL`, `FM_FUNKNETZ_LASTHEARD_URL` | Nur die in der Anwendung allowlist-konformen Dashboard-URLs. |
| `FM_FUNKNETZ_MQTT_ENABLED`, `FM_FUNKNETZ_MQTT_WS_URL` | Dokumentierte Adapterabsicht; kein MQTT-Client wird aktiv. |
| `SVXLINK_CONTROL_ENABLED` | `false`; im aktuellen Code ohne Aktivierungswirkung, Steuerung bleibt deaktiviert. |

Nach Änderungen an der Environment-Datei:

```bash
sudo systemctl restart svxlink-webui
```

## Optional: STATE_PTY-Collector

Nur nach Prüfung des konkreten SvxLink-STATE_PTY-Pfads in der Environment-Datei:

```bash
sudo systemctl enable --now svxlink-state-collector
sudo systemctl status svxlink-state-pty-permissions svxlink-state-collector
```

Der Binder wird bei SvxLink-Start neu ausgeführt. Fehlt der erwartete PTY oder ist er kein erlaubtes Ziel, soll der Dienst fehlschlagen statt weiter gefasste Geräteberechtigungen zu setzen. Nicht `tty`-Gruppenmitgliedschaften oder globale PTY-Rechte als Workaround vergeben.

## Abnahme nach Installation

```bash
sudo apache2ctl configtest
curl --fail http://127.0.0.1:12346/health
curl --fail http://127.0.0.1:12345/health
sudo systemctl status svxlink-webui
```

Die zweite URL prüft den Reverse Proxy. Erst nach erfolgter Zugangssicherung die URL von einem zugelassenen Client testen. Prüfen Sie außerdem, dass API-Ausgaben weder Geheimnisse noch Rohkonfiguration enthalten.

Weiter: [Betrieb und Fehlerdiagnose](operations.md) · [Sicherheit](security.md)
