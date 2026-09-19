# FM-Funknetz: verifizierte Quellen und Integrationsgrundlage

Stand: 2026-09-19

Diese Notiz dokumentiert ausschließlich Quellen, die für die read-only Anzeige belegt sind. Sie ist keine Freigabe für Publish, Steuerung oder einen direkten Browser-Brokerzugriff.

## Bereits im Repository verwendete Quellen

| Zweck | Konfiguration / Quelle | Belegter Datenumfang |
| --- | --- | --- |
| Aktive Live-Anzeige | `FM_FUNKNETZ_LIVE_URL`, Standard `https://dashboard.fm-funknetz.de/data/live.json` | JSON-Feed, als Array verarbeitet; der erste Eintrag wird als aktive Live-Quelle verwendet. Die konkrete Feldstruktur ist nicht durch dieses Repository normiert. |
| Last Heard | `FM_FUNKNETZ_LASTHEARD_URL`, Standard `https://dashboard.fm-funknetz.de/data/lastheard.json` | JSON-Feed, als Array verarbeitet und auf 100 Einträge begrenzt. Die konkrete Feldstruktur ist nicht durch dieses Repository normiert. |
| MQTT-over-WebSocket (nur Deployment-Konfiguration) | `FM_FUNKNETZ_MQTT_WS_URL`, aktuell bestätigter Wert `wss://status.thueringen.link/mqtt` | Verbindungsziel; kein MQTT-Client ist im Browser oder Backend aktiviert. |
| MQTT-Schalter | `FM_FUNKNETZ_MQTT_ENABLED`, Standard `false` | Nur Konfigurationsanzeige. Das Setzen auf `true` erzeugt in der aktuellen Anwendung keine Verbindung. |

Die beiden HTTP-Feeds wurden als CORS-fähige Dashboard-Assets bestätigt. Ein Feed-Fehler wird ohne Ersatzdaten als nicht verfügbar gemeldet; pro Feed gibt es einen begrenzten zweiten Abrufversuch.

## Historische MQTT/TCP-Quelle

Die offizielle historische Quelle ist `fm-funknetz.de:1883` (unverschlüsseltes MQTT/TCP). Die belegten historischen Topics sind:

- `/server/statethr`
- `/server/statethr/1`
- `/server/state/logins`

`/server/state/logins` wurde als Text-/Zahlquelle für Logins bzw. Clientzahl beschrieben. Eine andere Recherche der ausgelieferten Dashboard-JavaScript-Datei nennt für den aktuellen Bestand `/server/state/loginz`; diese Abweichung ist ungeklärt und wird nicht aufgelöst oder geraten. Das Nachrichtenformat und die Authentisierung sind für diese Anwendung nicht ausreichend validiert. Die Quelle darf daher nicht aus dem Browser verwendet werden und ist nicht als aktive Clientzahlquelle implementiert.

## Datenformat und Unsicherheiten

- Die JSON-Feeds sind als JSON-Arrays bestätigt. Feldnamen wie `call` oder `tg` erscheinen in vorhandenen Dashboard-Daten/Tests, sind aber kein von diesem Repository garantiertes externes Schema; neue Felder dürfen nicht geraten werden.
- Für die MQTT-Topics liegt kein belastbarer, versionierter Payload-Vertrag in diesem Repository vor. Insbesondere darf `/server/state/logins` nicht anhand eines vermuteten Payload-Feldes als Clientzahl interpretiert werden.
- Es gibt keine verlässlich belegte aktuelle Clientzahl im verwendeten JSON-Feed. Die API gibt `client_count: null` aus und die UI kennzeichnet diese Information als nicht verfügbar.
- Historische Topic-Namen und der aktuelle WSS-Endpunkt werden als read-only Beobachtungsquellen dokumentiert. Eine zukünftige Adapterimplementierung muss die Verbindung, Topic-Rechte und Payloads separat serverseitig validieren.

## Sicherheitsgrenzen

- Kein Publish, kein Subscribe auf Steuer-/DTMF-Themen und keine TG-Aktivierung.
- Keine Zugangsdaten, Broker-Passwörter oder öffentliche Broker-Credentials im Repository.
- Kein Browser-MQTT-over-WebSocket. Der konfigurierte WSS-Wert dient derzeit nur als dokumentierter Deployment-Wert; ein echter Adapter muss serverseitig, read-only und mit Least-Privilege-Zugang betrieben werden.
- Die externe Anzeige wird mit der Quelle `FM-Funknetz` bzw. `FM-Funknetz Dashboard-Livedaten` gekennzeichnet und verändert niemals den lokalen aktiven TG.

## Für die Implementierung nutzbare Umgebungsvariablen

```text
FM_FUNKNETZ_LIVE_URL
FM_FUNKNETZ_LASTHEARD_URL
FM_FUNKNETZ_MQTT_ENABLED
FM_FUNKNETZ_MQTT_WS_URL
```

Die Variablen stehen in `.env.example`. Es gibt absichtlich keine Umgebungsvariable für frei wählbare Topics: Die drei belegten read-only Topics sind im Backend fest vorgegeben.
