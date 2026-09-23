# Installation

SvxLink WebUI can be installed directly from GitHub.

## Requirements

Debian and Ubuntu based systems are currently supported, including:

- Debian
- Ubuntu
- Raspberry Pi OS

Root access is required.

On a fresh system, install `curl` first:

    apt update
    apt install -y curl

All other required packages are installed by the installer.

## Start installation

As root:

    curl -fsSL https://raw.githubusercontent.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI/main/bootstrap.sh | bash

The installer downloads the current version and guides you through the setup.

A manual `git clone` is not required.

## Setup

Existing settings are detected where possible and offered as defaults.

### WebUI

The installer asks for items such as:

- installation path
- WebUI port
- optional hostname
- username
- password

Port 80 is convenient for normal browser access without specifying a port.

Any other free port can also be used.

### Station and SvxLink

You may be asked for:

- callsign
- default talkgroup
- locator and station details
- audio device
- PTT device

### FM-Funknetz

If FM-Funknetz is used, the installer asks for the required credentials and default talkgroup.

### EchoLink

If EchoLink is used, you can enter callsign, password, Node ID, and station information.

### SHARI

The installer tries to detect audio, HID/PTT, and serial devices automatically.

If several devices are present, manual selection may be required.

## If SvxLink is not installed

When SvxLink is not detected, the installer offers to install the required packages.

A basic configuration is then created automatically.

## After installation

At the end of the installation the WebUI address is shown.

With port 80, for example:

    http://192.168.1.100/

With a custom port:

    http://192.168.1.100:8080/

The WebUI is protected by the username and password configured during installation.

## Updates

Updates can be installed directly from:

    System → Updates

Public installations use GitHub `main` as their update source.

Normal updates do not require running the Curl installer again.

## HTTPS

The installer does not configure HTTPS certificates.

HTTP can be used directly on a trusted local network.

For internet access, add suitable protection such as:

- VPN
- HTTPS reverse proxy
- firewall or IP allowlist
- SSO

## Backup and recovery

The installer creates backups before important changes.

They are stored under:

    /var/backups/svxlink-webui/

If installation fails, the installer attempts to restore the previous configuration automatically.

## Running the installer again

The installer can be started again at any time:

    curl -fsSL https://raw.githubusercontent.com/DA6IT/svxlink_echolink_fm-funknetz-WebUI/main/bootstrap.sh | bash

Previously detected or entered values are reused where possible.

## Troubleshooting

Check the WebUI:

    systemctl status svxlink-webui

Check SvxLink:

    systemctl status svxlink

Check the updater:

    systemctl status svxlink-webui-updater

Check the backend:

    curl -s http://127.0.0.1:12346/health

WebUI logs:

    journalctl -u svxlink-webui -n 100 --no-pager

SvxLink logs:

    journalctl -u svxlink -n 100 --no-pager

More information:

- [Configuration](CONFIGURATION.en.md)
- [Security](SECURITY.en.md)
