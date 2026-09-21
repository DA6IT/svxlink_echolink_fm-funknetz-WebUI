# Configuration

## Environment file

Reference path:

```text
/etc/svxlink-webui/environment
```

Current variables:

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

## Production mode

```text
SVXLINK_WEBUI_DEMO=false
```

Production systems should not display generated fake radio activity.

## Control PTY

Example:

```text
TG_CONTROL_PTY=/var/lib/svxlink/control/simplex_ctrl
```

Do not configure a fixed `/dev/pts/X` number.

## EchoLink

EchoLink data is read from the existing `ModuleEchoLink.conf` and node information.

Example:

```ini
[ModuleEchoLink]
NAME=EchoLink
ID=2
CALLSIGN=DA6IT-L
```

Personal values should not be hard-coded in program source.

### Pre-release limitation

The current EchoLink control path still sends `2#` for module activation.

Before public release, the module ID must be used dynamically from the detected configuration.

## Apache authentication

For the Apache-published WebUI, the interactive installer uses `AuthType Basic` with `Require valid-user`. It asks for a username and an at-least-eight-character password; only the bcrypt hash is stored in `/etc/apache2/svxlink-webui.htpasswd` as `root:www-data` with mode `0640`. The plaintext value, the hash, and the runtime file must not be committed. Basic Auth does not protect transport; use HTTPS or a VPN as additional protection on untrusted networks.

## Secrets

Never commit:
- passwords
- authentication keys
- API tokens
- private keys
- internal credentials
