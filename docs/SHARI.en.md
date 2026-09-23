# SHARI

The WebUI can read information directly from a connected SHARI/SA818 radio module.

## Displayed information

Depending on the hardware, the WebUI can show:

- module type
- firmware
- RX frequency
- TX frequency
- channel spacing
- TX CTCSS
- RX CTCSS
- squelch
- serial interface
- connection state

## Read-only

SHARI configuration is currently intentionally read-only.

The WebUI does not change frequencies or other radio settings.

This makes it safe to monitor an already configured SHARI without changing its existing setup.

## Serial connection

The installer tries to detect the serial interface automatically.

Typical devices include:

    /dev/ttyUSB0

or a path under:

    /dev/serial/by-id/

If several serial devices are present, manual selection may be required.

## Proxmox and LXC

When the WebUI runs inside an LXC container, SHARI hardware must be passed through from the Proxmox host.

Depending on the setup this may include:

- USB audio
- HID/PTT
- serial interface

The devices must be visible inside the container and accessible by the required services.
