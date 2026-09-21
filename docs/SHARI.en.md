# SHARI hardware

## Status

The WebUI can read the SA818/SA818S radio module directly over UART. The current implementation is intentionally **read-only** and does not change radio parameters.

## Read values

Commands used: `AT+DMOCONNECT`, `AT+VERSION` and `AT+DMOREADGROUP`.

The UI displays module type, firmware, RX/TX frequency, channel spacing, TX/RX CTCSS, squelch, serial port and connection status.

## API

`GET /api/shari/hardware`

## Serial interface

Defaults: `SHARI_SERIAL_PORT=/dev/ttyUSB0`, `SHARI_SERIAL_BAUD=9600`, `SHARI_SERIAL_TIMEOUT=0.8`.

Values can be overridden in `/etc/svxlink-webui/environment`.

## Permissions

The `svxlink-webui` service needs access to the serial device. A restricted group such as `svxlink-control` with device mode `0660` is recommended.

## Proxmox LXC

For LXC installations the device must be passed from the Proxmox host into the container, for example with `pct set <CTID> -dev0 path=/dev/ttyUSB0,gid=<GID>,mode=0660`.

## Next step

Writing frequency, CTCSS, squelch, channel spacing, volume and filter settings is not implemented yet. Validation, before/after verification and error handling will be added before write access.
