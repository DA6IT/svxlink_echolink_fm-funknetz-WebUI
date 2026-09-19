# SHARI-Referenzinstallation und explizite Grenzen

## Referenzumfang

„SHARI“ ist im aktuellen Repository eine UI-/API-Bezeichnung für lokale, read-only RF-Telemetrie: TX/PTT und RX-Zustände können aus dem optionalen, normalisierten STATE_PTY-Snapshot angezeigt werden; ergänzend verarbeitet die WebUI klar begrenzte lokale SvxLink-Logmuster. Das Repository enthält keine vollständige, reproduzierbare Beschreibung einer konkreten physischen SHARI-Station, ihrer Hardware, Frequenzen, Rufzeichen, Netzadressen oder Zugangsdaten. Diese Werte dürfen daher nicht aus dieser Dokumentation abgeleitet oder erfunden werden.

Für eine reale Referenzinstallation gelten die allgemeinen Installationsschritte mit folgenden zusätzlichen Abnahmepunkten:

1. SvxLink stellt einen ausdrücklich read-only STATE_PTY bereit; `SVXLINK_STATE_PTY_RAW_PATH` verweist auf den konkret geprüften Pfad.
2. Der Binder akzeptiert den Pfad und setzt nur `svxlink-state-reader`/`0640`; der Collector läuft als eigenes Konto.
3. `SVXLINK_STATE_PTY_ENABLED=true` ist erst nach dieser Prüfung gesetzt.
4. `/api/rf/status` liefert ausschließlich normalisierte `Tx:state`/`Rx:state`-Daten oder kontrolliert „nicht verfügbar“.
5. Die WebUI wird über die Betreibergrenze (mindestens vertrauenswürdiges Netz; bei externer Nutzung TLS und starke Zugangskontrolle) veröffentlicht.

Die Oberfläche benennt Karten als „SHARI TX / PTT“ und „SHARI RX / Squelch“. Eine sichtbare Karte belegt aber keine physische Aktivität, wenn die API keine Quelle liefert.

## Was lokale Logs tatsächlich abbilden

Der Logadapter akzeptiert nur unterstützte Zeitstempelformate und die folgenden Muster:

- `ReflectorLogic: Node joined/left` für Reflector-Ereignisse,
- `Rx1: The squelch is OPEN/CLOSED (<level>)`,
- `ReflectorLogic: Selecting TG #<TG>`,
- `ReflectorLogic: Talker start/stop on TG #<TG>: <callsign>`.

Eine geschlossene Squelch- oder Stop-Zeile setzt den jeweiligen Live-Zustand zurück. Unbekannte Logzeilen werden verworfen. Die lokale TG ist nur bei einer neuen numerischen, allowlist-konformen Selecting-Zeile „bestätigt“.

## Nicht implementiert / offene Punkte

- Kein PTT, DTMF, `COMMAND_PTY`, Shell-Aufruf oder SvxLink-Service-Control aus der WebUI.
- Keine TG-Aktivierung und keine vorhandene Steuerroute, auch nicht bei `SVXLINK_CONTROL_ENABLED=true`.
- Kein MQTT-Client: WSS-Endpunkt und Topics sind nur dokumentierte Deployment-Werte.
- Kein Browser-MQTT, kein Publish und keine Steuer-Topics.
- Keine belastbare Clientzahl aus FM-Funknetz-JSON; die API gibt hierfür `null` aus.
- Kein stabiler Vertrag für Feldnamen externer FM-Funknetz-Payloads.
- Kein belastbar validierter lokaler Emitter für EchoLink-Peers. EchoLink-Daten werden nicht angezeigt oder angenommen.
- Talker werden nur als lokal geparste Logereignisse geführt, nicht aus externen Feed-Daten abgeleitet.
- Kein TLS, keine Authentifizierung und keine Autorisierung im ausgelieferten Apache-VHost.
- Keine automatische Sicherungsplanung; `/var/lib/svxlink-webui/backups` wird angelegt, aber nicht automatisch befüllt.

Diese Grenzen sind Absicht und müssen bei Planung weiterer Funktionen als Sicherheitsanforderungen behandelt werden.

Weiter: [Sicherheit](security.md) · [Betrieb](operations.md) · [Dokumentationsindex](README.md)
