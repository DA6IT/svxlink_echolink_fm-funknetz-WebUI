# Datenschutz und öffentliche Beispiele

## Grundsatz

Die WebUI verarbeitet Amateurfunk-Live-Daten wie Rufzeichen, Node-IDs, Zeitpunkte und Verbindungsinformationen.

Im realen Betrieb dürfen diese Daten angezeigt werden. Für statische öffentliche Beispiele gelten strengere Regeln.

## Nicht dauerhaft einbauen

Nicht als feste öffentliche Beispiele verwenden:
- zufällig beobachtete fremde Rufzeichen
- fremde EchoLink Node-IDs
- fremde Last-Heard-Daten
- fremde Verbindungshistorien
- unnötige personenbezogene Live-Daten in Screenshots

## Geeignete Beispiele

Eigene Projektdaten dürfen verwendet werden:

```text
DA6IT
DA6IT-L
```

Generische Beispiele:

```text
DB0XYZ-R
YOURCALL-L
<CALLSIGN>
<NODE_ID>
<TALKGROUP>
```

## UI-Platzhalter

Keine zufälligen realen fremden Rufzeichen im Quellcode fest eintragen.

Bevorzugt:

```text
Rufzeichen oder Node-ID
```

oder, falls ein Beispiel hilfreich ist:

```text
z. B. DA6IT-L oder 123456
```

## Screenshots

Vor Veröffentlichung prüfen:
- fremde Rufzeichen?
- fremde Node-IDs?
- History/Last Heard?
- interne Hostnamen/IP-Adressen?
- Zugangsdaten?

Nicht benötigte Daten anonymisieren.

## Repository

Live-Daten sollen nicht allein deshalb in Tests, Demo-Daten oder Dokumentation übernommen werden, weil sie während der Entwicklung sichtbar waren.
