# EchoLink

## Eigener Node

Die WebUI zeigt:
- eigenes EchoLink-Rufzeichen
- Node-ID
- Directory-Status
- Modulstatus
- aktuelle Verbindungen

## EchoLink-Modul

Das EchoLink-Modul kann über die WebUI aktiviert und deaktiviert werden.

Aktuelle Pre-Release-Einschränkung: Die Aktivierung verwendet im Steuerpfad noch die Modul-ID `2`. Vor dem öffentlichen Release muss diese dynamisch aus `ModuleEchoLink.conf` übernommen werden.

## Aktuelle Verbindungen

Unterschieden werden:
- eingehend
- ausgehend

Angezeigt werden Rufzeichen und Verbindungsdauer.

## Directory-Suche

Suche nach:

```text
<CALLSIGN>
<NODE_ID>
```

Das Backend kombiniert registrierte Node-Informationen mit den aktuell eingeloggten EchoLink-Stationen.

Status:

### ONLINE
Node existiert und ist aktuell angemeldet.

### BUSY
Node ist angemeldet, akzeptiert aber aktuell keine normale neue Verbindung.

### OFFLINE
Node ist registriert, aber aktuell nicht angemeldet.

OFFLINE bedeutet nicht „Node existiert nicht“.

## Favoriten

Gespeichert werden:
- Anzeigename
- Rufzeichen
- Node-ID

Der aktuelle ONLINE/BUSY/OFFLINE-Status wird beim Laden ergänzt.

## Connect/Disconnect

Online-Nodes können aus Suchergebnissen oder Favoriten verbunden werden. Bestehende Verbindungen können über die WebUI getrennt werden.

## History

Neue EchoLink-Verbindungen werden persistent erfasst:
- Rufzeichen
- Richtung
- Startzeit
- Endzeit
- Dauer

Vor Installation der Event-Erfassung nicht aufgezeichnete Verbindungen werden nicht rückwirkend erfunden.

## Event Bridge

Original bleibt unverändert:

```text
/usr/share/svxlink/events.d/EchoLink.tcl
```

Lokaler Handler:

```text
/usr/share/svxlink/events.d/local/EchoLinkWebUI.tcl
```

Verarbeitete Events umfassen:
- activating_module
- deactivating_module
- connecting_to
- remote_connected
- connected
- disconnected
- client_list_changed

Roh-Events:

```text
/var/lib/svxlink/echolink-webui/events.tsv
```

SQLite:

```text
/var/lib/svxlink-webui/echolink.sqlite3
```

## Directory Provider

Die aktuelle Implementierung verwendet öffentliche EchoLink-Webquellen für Node Lookup und Current Logins. HTML-Verarbeitung ist im Backend gekapselt.

## Öffentliche Beispiele

Keine fremden realen Rufzeichen oder Node-IDs dauerhaft in README, Dokumentation, Screenshots, Platzhaltern oder Demo-Daten einbauen.

Geeignete Beispiele:

```text
DA6IT-L
DB0XYZ-R
<CALLSIGN>
<NODE_ID>
```
