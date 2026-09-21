# Konfiguration

## Environment-Datei

Referenz:

```text
/etc/svxlink-webui/environment
```

Aktuell verwendete Variablen:

```text
SVXLINK_WEBUI_DEMO
SVXLINK_CALLSIGN
SVXLINK_CONFIG_PATH
SVXLINK_LOCATION
SVXLINK_LOG_PATH
SVXLINK_NODE_INFO_PATH
SVXLINK_NODE_NAME
SVXLINK_PID_PATH
SVXLINK_SERVICE_NAME
SVXLINK_ACTIVITY_DB

SVXLINK_STATE_PTY_ENABLED
SVXLINK_STATE_PTY_PATH
SVXLINK_STATE_PTY_RAW_PATH

TG_CONTROL_ENABLED
TG_CONTROL_PTY

FM_FUNKNETZ_MQTT_ENABLED
FM_FUNKNETZ_MQTT_HOST
FM_FUNKNETZ_MQTT_PORT
FM_FUNKNETZ_MQTT_TOPICS
FM_FUNKNETZ_MQTT_STALE_AFTER

FM_FUNKNETZ_NODES_MQTT_HOST
FM_FUNKNETZ_NODES_MQTT_PORT

FM_FUNKNETZ_STATS_URL
FM_FUNKNETZ_STATS_CACHE_TTL
```

## Produktionsmodus

```text
SVXLINK_WEBUI_DEMO=false
```

Produktive Systeme sollen keine künstlich erzeugten Funkdaten anzeigen.

## Control PTY

Beispiel:

```text
TG_CONTROL_PTY=/var/lib/svxlink/control/simplex_ctrl
```

Keine feste `/dev/pts/X`-Nummer konfigurieren.

## EchoLink

EchoLink-Daten werden aus der vorhandenen `ModuleEchoLink.conf` und Node-Information gelesen.

Beispiel:

```ini
[ModuleEchoLink]
NAME=EchoLink
ID=2
CALLSIGN=DA6IT-L
```

Persönliche Werte sollen nicht im Programmcode fest hinterlegt werden.

### Pre-Release-Einschränkung

Der aktuelle EchoLink-Steuerpfad sendet für die Modulaktivierung noch `2#`.

Vor dem öffentlichen Release muss die Modul-ID dynamisch aus der vorhandenen Konfiguration verwendet werden.

## Secrets

Nicht in Git:
- Passwörter
- Auth Keys
- API-Tokens
- private Schlüssel
- interne Zugangsdaten
