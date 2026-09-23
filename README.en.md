# SvxLink WebUI

A modern web interface for **SvxLink**, **SHARI**, **FM-Funknetz**, and **EchoLink**.

The WebUI brings the most important functions of your SvxLink system into the browser: current talkgroups, favourites, buddies, EchoLink connections, SHARI status, and system information.

The interface is designed for desktop, tablet, and mobile use.

[German version](README.md)

## What can the WebUI do?

### FM-Funknetz

- show the currently connected talkgroup
- follow active talkgroups live
- connect directly to talkgroups
- save favourite talkgroups
- use favourites directly from the home page
- buddy list with online and last-seen status
- join the current talkgroup of an online buddy
- leave a talkgroup and return to the configured default
- view Top Talkgroups for 24 hours, 7 days, and 30 days

### EchoLink

- show your own EchoLink node
- activate and deactivate EchoLink
- view current connections
- disconnect active connections
- search by callsign or Node ID
- show ONLINE, BUSY, and OFFLINE state
- save EchoLink nodes as favourites
- connect directly to favourites
- view connection history

### SHARI and SvxLink

- show SvxLink status
- read SHARI/SA818 hardware information
- display RX and TX frequency
- display CTCSS, squelch, and channel spacing
- check audio, PTT, and PTY state
- view system health information

SHARI hardware is currently read-only. Radio parameters are not changed.

## Quick installation

A fresh Debian, Ubuntu, or Raspberry Pi OS installation only needs `curl` before starting.

As root:

    apt update
    apt install -y curl

Then run:

    curl -fsSL https://raw.githubusercontent.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI/main/bootstrap.sh | bash

The installer will guide you through the remaining setup.

## What does the installer ask for?

Existing settings are detected where possible and offered as defaults.

The installer may ask for:

- installation path
- WebUI port
- optional hostname
- WebUI username and password
- callsign
- FM-Funknetz credentials
- default talkgroup
- audio and PTT device
- EchoLink settings
- SHARI serial interface

If SvxLink is not installed yet, the installer can install the required packages as well.

Detailed instructions:

[Installation](docs/INSTALLATION.en.md)

## After installation

At the end of the installation the installer shows the WebUI address.

For port 80, for example:

    http://192.168.1.100/

or with a configured hostname:

    http://shari.example.local/

The WebUI is protected by username and password.

## Updates

Updates can be installed directly from the WebUI:

    System → Updates

Public installations use GitHub `main` as their update source.

Normal updates do not require running the installer again.

## Security

The WebUI can control real SvxLink functions.

Do not expose it directly to the internet without suitable protection.

Useful options include:

- VPN
- firewall or IP allowlist
- HTTPS reverse proxy
- SSO

More information:

[Security](docs/SECURITY.en.md)

## Documentation

- [Installation](docs/INSTALLATION.en.md)
- [Configuration](docs/CONFIGURATION.en.md)
- [FM-Funknetz](docs/FM-FUNKNETZ.en.md)
- [EchoLink](docs/ECHOLINK.en.md)
- [SHARI](docs/SHARI.en.md)
- [Security](docs/SECURITY.en.md)
- [Privacy](docs/PRIVACY.en.md)

Technical information for developers and administrators:

- [Architecture](docs/ARCHITECTURE.en.md)
- [Changelog](CHANGELOG.md)

## Project status

The WebUI is running on a real SHARI/SvxLink system.

The public installer has been successfully tested on a fresh system.
