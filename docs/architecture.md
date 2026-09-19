# Architektur und Datenflüsse

## Komponenten

Die Anwendung besteht aus einer React/Vite-Einseite im Apache-DocumentRoot und einem FastAPI/Uvicorn-Backend. Apache lauscht auf Port `12345`; Uvicorn wird durch `svxlink-webui.service` ausschließlich an `127.0.0.1:12346` gebunden. Apache liefert statische Dateien aus und leitet ausschließlich `/api/` sowie `/api/ws/` an das Loopback-Backend weiter.

```mermaid
flowchart LR
  B[Browser] -->|HTTP :12345| A[Apache]
  A -->|statische React/Vite-Dateien| F[/var/www/new.shart]
  A -->|/api/ und /api/ws/| U[Uvicorn 127.0.0.1:12346]
  U --> API[FastAPI read-only API]
  API --> N[node_info.json Allowlist]
  API --> C[svxlink.conf Allowlist]
  API --> L[SvxLink-Logs: bekannte Muster]
  API --> S[systemctl show + PID-Datei]
  API --> J[normalisiertes JSONL-Snapshot]
  API --> FM[FM-Funknetz HTTPS-Feeds]
```

`FallbackResource /index.html` ermöglicht das clientseitige Routing. Der VHost legt keine TLS-Konfiguration fest; er stellt daher keine transportgesicherte Veröffentlichung selbst her.

## Lokale Datenquellen

FastAPI liest nur die folgenden konfigurierbaren Quellen:

| Quelle | Standardwert | Verwendung / Begrenzung |
|---|---|---|
| Node-Information | `/etc/svxlink/node_info.json` | Nur definierte Stations-, Standort-, Frequenz-, Modus-, Netzwerk-, Rufzeichen- und Default-TG-Schlüssel. |
| SvxLink-Konfiguration | `/etc/svxlink/svxlink.conf` | Nur `LOGICS`, `DEFAULT_TG`, `CALLSIGN`, `NODE_INFO_FILE`, `LINKS`, `SERVICES`. Keine Rohkonfiguration. |
| Dienststatus | `systemctl show svxlink` und `/run/svxlink.pid` | `ActiveState`, `SubState` und PID. |
| SvxLink-Log | `/var/log/svxlink` | Höchstens die fünf jüngsten regulären Dateien; Join/Leave sowie bestätigte `Rx1`-, TG- und Talker-Muster. Unbekannte Zeilen werden ignoriert. |
| STATE-Snapshot | `/run/svxlink-webui/state.jsonl` | Optional; nur normalisierte `Tx:state`/`Rx:state`-Ereignisse. |
| FM-Funknetz | zwei feste HTTPS-URLs | Externe, ausdrücklich gekennzeichnete Telemetrie. |

## Optionaler STATE_PTY-Pfad

Die WebUI öffnet niemals den Roh-`STATE_PTY`. Der optionale Collector liest ihn einwegig und ersetzt ein JSONL-Snapshot atomar. Der Binder wird an SvxLink gebunden und setzt nur am akzeptierten PTY/FIFO restriktive Gruppenleserechte. Der Collector startet erst nach SvxLink und Binder.

```mermaid
flowchart LR
  V[SvxLink read-only STATE_PTY] --> P[root: Berechtigungs-Binder]
  P -->|0640, Gruppe svxlink-state-reader| R[svxlink-state-collector]
  R -->|nur Tx:state/Rx:state| J[/run/svxlink-webui/state.jsonl]
  J -->|read-only| W[svxlink-webui FastAPI]
  W --> B[Browser]
  D[COMMAND_PTY / DTMF / PTT] -. kein Zugriff .-> R
  D -. kein Zugriff .-> W
```

Der Collector akzeptiert nur Zeichen-Geräte oder FIFOs, verwirft fehlerhafte bzw. zu lange Zeilen und beendet sich bei geschlossenem Rohpfad, damit systemd ihn neu startet. Das Snapshot ist auf 200 Ereignisse begrenzt und wird ersetzt statt angehängt. Der Binder löst höchstens einen Symlink auf und akzeptiert nur direkte PTY-Ziele unter `/dev/pts/`; unzulässige Ziele schlagen fehl.

## Externe Datenflüsse

Der Backend-Abruf nutzt ausschließlich `https://dashboard.fm-funknetz.de/data/live.json` und `https://dashboard.fm-funknetz.de/data/lastheard.json`, ohne Redirects, Query-Strings oder alternative Hosts. Jede Abfrage hat einen begrenzten Wiederholungsversuch. Ein Ausfall liefert „nicht verfügbar“, niemals synthetische Funkdaten. Der Browser verbindet sich nicht mit MQTT.

## Aktualisierung und WebSocket

Das Frontend aktualisiert seinen Status zyklisch alle 15 Sekunden. `/api/ws/live` sendet nach Verbindung ein einzelnes `node.status`-Snapshot und wartet anschließend auf Nachrichten; es ist kein Push-Stream von SvxLink.

Weiter: [API-Referenz](api.md) · [Sicherheit](security.md)
