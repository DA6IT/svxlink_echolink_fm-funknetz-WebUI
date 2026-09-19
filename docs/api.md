# API-Referenz

Basis ist derselbe Origin wie die WebUI; Apache proxyt `/api/` und `/api/ws/` an das Loopback-Backend. Alle HTTP-Routen sind `GET`, außer dem WebSocket. Die CORS-Middleware lässt `GET` für beliebige Origins zu; das ist kein Authentifizierungsmechanismus.

| Route | Inhalt |
|---|---|
| `GET /health` | `{ok: true, version}` für einfache Erreichbarkeitsprüfung. |
| `GET /api/status` | Kombiniertes Dashboard-Snapshot: Node, Dienst, Reflector, lokale RF-Telemetrie, Log-Aktivität, Events, erlaubte Konfigurationswerte, Demo-Flag, Version, Zeitstempel. |
| `GET /api/svxlink/status` | Dienststatus aus `systemctl show` plus PID. |
| `GET /api/system` | Hostname, Betriebssystemkennung, Python-Version, monotonic Uptime und App-Version. |
| `GET /api/node-info` | Allowlist-gefilterte Node-Information und Verfügbarkeitsflag. |
| `GET /api/last-heard` | Nur geparste Reflector-Join/Leave-Ereignisse. |
| `GET /api/svxlink/logs` | Dasselbe Ereignismodell einschließlich Anzahl und Verfügbarkeit. Keine Rohlogs. |
| `GET /api/talkgroups` | Lokale bestätigte TG, Default-TG aus erlaubter Konfiguration, externe FM-Funknetz-Ansicht und fest deaktivierter Control-Status. |
| `GET /api/fm-funknetz/live` | Bis zu 100 Live- und Last-Heard-Elemente der externen JSON-Feeds, MQTT-Konfigurationshinweis und Verfügbarkeit. |
| `GET /api/rf/status` | Optionales, normalisiertes lokales STATE_PTY-Snapshot. |
| `GET /api/events` | Feature-gegate, normalisierte lokale Ereignisse; nimmt keine HTTP-Eingaben an. |
| `WS /api/ws/live` | Nach `accept` genau ein `{event: "node.status", data: ...}`. |

## Nicht vorhandene Schnittstellen

`/api/config` existiert absichtlich nicht. Ebenso fehlen Schreib-Endpoints, Shell- oder Service-Commands, MQTT-Client-Routen, PTT-/Funksteuerung und `POST /api/control/talkgroups/{tg}`. Rohkonfiguration und Rohlogs werden nicht ausgeliefert.

## Semantische Grenzen

Eine lokal bestätigte aktive TG beruht nur auf einer neuen, numerischen und allowlist-konformen Logzeile `ReflectorLogic: Selecting TG #<TG>`. Ohne solche Bestätigung kann die API einen `DEFAULT_TG` aus der gefilterten Konfiguration anzeigen, markiert ihn aber nicht als bestätigt. Externe FM-Funknetz-Daten verändern die lokale TG nicht.

Log-Talker werden nur gezeigt, wenn ein unterstütztes lokales `ReflectorLogic: Talker start ...`-Muster gelesen wurde; ein Stop setzt diesen Zustand zurück. EchoLink-Peers werden durch diese API nicht erhoben und sind daher nicht als vorhanden anzunehmen.

Weiter: [Sicherheit und Berechtigungsgrenzen](security.md) · [Betrieb](operations.md)
