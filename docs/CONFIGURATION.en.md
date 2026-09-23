# Configuration

Most settings are entered during installation.

After a successful installation, normal operation usually does not require editing configuration files manually.

## WebUI

During installation you choose:

- port
- optional hostname
- username
- password

These values determine how you access the WebUI later.

## FM-Funknetz

FM-Funknetz setup includes items such as:

- callsign
- credentials
- default talkgroup

The currently selected talkgroup can later be changed directly from the WebUI.

## EchoLink

EchoLink configuration can include:

- EchoLink callsign
- password
- Node ID
- sysop name
- location

Existing EchoLink settings are detected where possible.

## Audio and PTT

The installer tries to detect suitable audio and PTT devices automatically.

If several devices are available, verify that the correct one is selected.

## SHARI

The serial interface of a SHARI/SA818 module is detected automatically where possible.

Typical devices include:

    /dev/ttyUSB0

or a stable path under:

    /dev/serial/by-id/

A `/dev/serial/by-id/` path is usually more reliable than a changing `ttyUSB` number.

## Advanced settings

Runtime configuration is stored in:

    /etc/svxlink-webui/environment

This file is mainly intended for advanced configuration.

For normal operation, only change it when you know exactly which setting you need to adjust.

## Everyday changes

Common functions are controlled directly from the WebUI, including:

- changing talkgroups
- leaving a talkgroup
- activating EchoLink
- connecting or disconnecting EchoLink
- managing favourites
- managing buddies

No manual file editing is required for these functions.

## More information

- [Installation](INSTALLATION.en.md)
- [FM-Funknetz](FM-FUNKNETZ.en.md)
- [EchoLink](ECHOLINK.en.md)
- [SHARI](SHARI.en.md)
