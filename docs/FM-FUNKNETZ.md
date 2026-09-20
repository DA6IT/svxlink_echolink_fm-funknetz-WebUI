# FM-Funknetz

## Live-Aktivität

Die WebUI verarbeitet aktuelle Gesprächsaktivität über MQTT.

Typische Daten:
- Talkgroup
- Rufzeichen
- Start/Stop
- Server
- Zeit

## Aktive Talkgroups

Aktive Talkgroups erscheinen automatisch mit:
- TG-Nummer
- TG-Name
- aktuellem Rufzeichen
- Aktivitätsstatus

## Favoriten

Talkgroups können als Favoriten gespeichert werden und bleiben auch ohne aktuelle Aktivität sichtbar.

## Steuerung

Die Talkgroup-Auswahl erfolgt über den SvxLink DTMF Control PTY.

Eine Talkgroup wird erst dann als lokal verbunden angezeigt, wenn SvxLink den Zustand bestätigt hat.

## Verbindung verlassen

Die aktive Talkgroup kann verlassen werden. SvxLink fällt anschließend auf den konfigurierten Standardzustand zurück.

## Top Talkgroups

Zeiträume:

```text
24 Stunden
7 Tage
30 Tage
```

Angezeigt werden u. a.:
- Talkgroup
- Talkgroup-Name
- Anzahl Rufzeichen
- Anzahl Durchgänge
- Sprechzeit

## Buddy/Node-Daten

Zusätzliche FM-Funknetz Node-Informationen können ausgewertet werden. Buddy-Suchen verwenden Basisrufzeichen, damit technische Suffixe berücksichtigt werden können.

## Öffentliche Beispiele

Keine zufällig beobachteten fremden Rufzeichen dauerhaft in Screenshots, README oder Demo-Daten übernehmen.

Geeignete Beispiele:

```text
DA6IT
<CALLSIGN>
<TALKGROUP>
```
