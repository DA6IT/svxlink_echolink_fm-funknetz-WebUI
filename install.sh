#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_NAME="SvxLink WebUI"
INSTALLER_VERSION="1.0.0-pre3"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_ROOT="/var/backups/svxlink-webui/${TIMESTAMP}"

# -----------------------------------------------------------------------------
# Farben nur auf einem echten Terminal verwenden
# -----------------------------------------------------------------------------
if [[ -t 1 ]]; then
  C_GREEN='\033[0;32m'
  C_YELLOW='\033[0;33m'
  C_RED='\033[0;31m'
  C_CYAN='\033[0;36m'
  C_BOLD='\033[1m'
  C_RESET='\033[0m'
else
  C_GREEN=''; C_YELLOW=''; C_RED=''; C_CYAN=''; C_BOLD=''; C_RESET=''
fi

say()   { printf '%b\n' "$*"; }
info()  { say "${C_CYAN}>>>${C_RESET} $*"; }
ok()    { say "${C_GREEN}✓${C_RESET} $*"; }
warn()  { say "${C_YELLOW}WARNUNG:${C_RESET} $*"; }
die() {
  say "${C_RED}FEHLER:${C_RESET} $*" >&2
  if [[ "${ROLLBACK_ARMED:-false}" == "true" ]] && declare -F rollback >/dev/null 2>&1; then
    rollback 1
  fi
  exit 1
}
hr()    { printf '%s\n' '============================================================'; }

# -----------------------------------------------------------------------------
# Root / sudo
# -----------------------------------------------------------------------------
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo
  die "Dieser Installer benötigt Root-Rechte. Starte ihn mit 'sudo ./install.sh' oder aus einer Root-Shell mit './install.sh'."
fi

INVOKING_USER="${SUDO_USER:-root}"
if [[ "$INVOKING_USER" == "root" ]]; then
  INVOCATION="direkte Root-Shell"
else
  INVOCATION="sudo durch ${INVOKING_USER}"
fi

# Innerhalb dieses Installers wird absichtlich niemals sudo verwendet.

# -----------------------------------------------------------------------------
# Kleine Eingabe-Helfer
# -----------------------------------------------------------------------------
ask() {
  local prompt="$1" default="${2:-}" value
  if [[ -n "$default" ]]; then
    read -r -p "$prompt [$default]: " value
    printf '%s' "${value:-$default}"
  else
    read -r -p "$prompt: " value
    printf '%s' "$value"
  fi
}

ask_secret() {
  local prompt="$1" keep_existing="${2:-false}" value
  if [[ "$keep_existing" == "true" ]]; then
    read -r -s -p "$prompt [ENTER = vorhandenen Wert behalten]: " value
  else
    read -r -s -p "$prompt: " value
  fi
  echo >&2
  printf '%s' "$value"
}

ask_yes_no() {
  local prompt="$1" default="${2:-y}" answer suffix
  if [[ "$default" == "y" ]]; then suffix="[J/n]"; else suffix="[j/N]"; fi
  while true; do
    read -r -p "$prompt $suffix " answer
    answer="${answer:-$default}"
    case "${answer,,}" in
      j|ja|y|yes) return 0 ;;
      n|nein|no) return 1 ;;
      *) echo "Bitte j oder n eingeben." ;;
    esac
  done
}

ask_port() {
  local prompt="$1" default="$2" value
  while true; do
    value="$(ask "$prompt" "$default")"
    if [[ "$value" =~ ^[0-9]+$ ]] && (( value >= 1 && value <= 65535 )); then
      printf '%s' "$value"
      return 0
    fi
    echo "Ungültiger Port. Bitte 1-65535 verwenden." >&2
  done
}

ask_callsign() {
  local prompt="$1" default="${2:-}" value
  while true; do
    value="$(ask "$prompt" "$default")"
    value="${value^^}"
    if [[ "$value" =~ ^[A-Z0-9][A-Z0-9/-]{1,19}$ ]]; then
      printf '%s' "$value"
      return 0
    fi
    echo "Ungültiges Rufzeichen/Node-Rufzeichen." >&2
  done
}

ask_web_username() {
  local prompt="$1" default="${2:-}" value
  while true; do
    value="$(ask "$prompt" "$default")"
    if [[ "$value" =~ ^[A-Za-z0-9._-]{1,64}$ ]]; then
      printf '%s' "$value"
      return 0
    fi
    echo "Ungültiger WebUI-Benutzername. Erlaubt sind A-Z, a-z, 0-9, Punkt, Unterstrich und Bindestrich." >&2
  done
}

ask_web_password() {
  local first second
  while true; do
    first="$(ask_secret 'Passwort für die WebUI')"
    if (( ${#first} < 8 )); then
      echo "Das WebUI-Passwort muss mindestens 8 Zeichen lang sein." >&2
      continue
    fi
    second="$(ask_secret 'Passwort wiederholen')"
    if [[ "$first" != "$second" ]]; then
      echo "Die Passwörter stimmen nicht überein." >&2
      continue
    fi
    printf '%s' "$first"
    return 0
  done
}

# -----------------------------------------------------------------------------
# INI Helfer, ohne die komplette SvxLink-Datei neu zu formatieren
# -----------------------------------------------------------------------------
ini_get() {
  local file="$1" section="$2" key="$3"
  [[ -f "$file" ]] || return 0
  python3 - "$file" "$section" "$key" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
section = sys.argv[2].strip().lower()
key = sys.argv[3].strip().lower()
current = None
for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
    line = raw.strip()
    if not line or line.startswith(("#", ";")):
        continue
    if line.startswith("[") and line.endswith("]"):
        current = line[1:-1].strip().lower()
        continue
    if current == section and "=" in line:
        k, v = line.split("=", 1)
        if k.strip().lower() == key:
            print(v.strip())
            break
PY
}

ini_set() {
  local file="$1" section="$2" key="$3" value="$4"
  mkdir -p "$(dirname "$file")"
  [[ -f "$file" ]] || : > "$file"
  SVXWEBUI_INI_VALUE="$value" python3 - "$file" "$section" "$key" <<'PY'
from pathlib import Path
import os, sys, re

path = Path(sys.argv[1])
section, key = sys.argv[2], sys.argv[3]
value = os.environ.get("SVXWEBUI_INI_VALUE", "")
lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
sec_re = re.compile(r"^\s*\[([^]]+)\]\s*$")
key_re = re.compile(r"^(\s*)" + re.escape(key) + r"\s*=", re.I)
section_start = None
section_end = len(lines)
current = None

for i, raw in enumerate(lines):
    m = sec_re.match(raw)
    if m:
        name = m.group(1).strip()
        if current == section and section_end == len(lines):
            section_end = i
        current = name
        if name.lower() == section.lower() and section_start is None:
            section_start = i

if section_start is None:
    if lines and lines[-1].strip():
        lines.append("")
    lines.extend([f"[{section}]", f"{key}={value}"])
else:
    # Ende der Zielsektion bestimmen
    section_end = len(lines)
    for i in range(section_start + 1, len(lines)):
        if sec_re.match(lines[i]):
            section_end = i
            break
    replaced = False
    for i in range(section_start + 1, section_end):
        if lines[i].lstrip().startswith(("#", ";")):
            continue
        m = key_re.match(lines[i])
        if m:
            lines[i] = f"{m.group(1)}{key}={value}"
            replaced = True
            break
    if not replaced:
        lines.insert(section_end, f"{key}={value}")

path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
PY
}

ini_csv_add() {
  local file="$1" section="$2" key="$3" item="$4" current
  current="$(ini_get "$file" "$section" "$key")"
  python3 - "$file" "$section" "$key" "$item" "$current" <<'PY'
import sys
from pathlib import Path

file, section, key, item, current = sys.argv[1:]
items = [x.strip() for x in current.split(",") if x.strip()]
if item not in items:
    items.append(item)
print(",".join(items))
PY
}

# -----------------------------------------------------------------------------
# Backup / Rollback der Dateien, die der Installer verändert
# -----------------------------------------------------------------------------
TOUCH_FILES=(
  /etc/svxlink/svxlink.conf
  /etc/svxlink/svxlink.d/ModuleEchoLink.conf
  /etc/svxlink/node_info.json
  /usr/share/svxlink/events.d/local/EchoLinkWebUI.tcl
  /etc/svxlink-webui/environment
  /etc/systemd/system/svxlink-webui.service
  /etc/systemd/system/svxlink-webui-state-collector.service
  /etc/systemd/system/svxlink-webui-state-permissions.service
  /etc/systemd/system/svxlink-webui-state-permissions.path
  /etc/systemd/system/svxlink-webui-control-permissions.service
  /etc/systemd/system/svxlink-webui-control-permissions.path
  /usr/local/libexec/svxlink-webui-control-permissions
  /etc/apache2/sites-available/svxlink-webui.conf
  /etc/apache2/conf-available/svxlink-webui-port.conf
  /etc/apache2/svxlink-webui.htpasswd
)

backup_file() {
  local path="$1" key
  key="${path#/}"
  key="${key//\//__}"
  mkdir -p "$BACKUP_ROOT/files"
  if [[ -e "$path" || -L "$path" ]]; then
    cp -a "$path" "$BACKUP_ROOT/files/$key"
    touch "$BACKUP_ROOT/files/$key.present"
  else
    touch "$BACKUP_ROOT/files/$key.missing"
  fi
}

restore_file() {
  local path="$1" key
  key="${path#/}"
  key="${key//\//__}"
  if [[ -f "$BACKUP_ROOT/files/$key.present" ]]; then
    mkdir -p "$(dirname "$path")"
    rm -f "$path"
    cp -a "$BACKUP_ROOT/files/$key" "$path"
  elif [[ -f "$BACKUP_ROOT/files/$key.missing" ]]; then
    rm -f "$path"
  fi
}

ROLLBACK_ARMED=false
rollback() {
  local rc="${1:-$?}"
  trap - ERR INT TERM
  if [[ "$ROLLBACK_ARMED" == "true" ]]; then
    echo
    warn "Installation fehlgeschlagen. Konfigurationsdateien werden zurückgerollt."
    for path in "${TOUCH_FILES[@]}"; do
      restore_file "$path" || true
    done
    systemctl daemon-reload || true
    if command -v a2ensite >/dev/null 2>&1; then
      if [[ -f "$BACKUP_ROOT/apache-site-enabled" && "$(cat "$BACKUP_ROOT/apache-site-enabled")" == "true" ]]; then
        a2ensite svxlink-webui >/dev/null 2>&1 || true
      else
        a2dissite svxlink-webui >/dev/null 2>&1 || true
      fi
      if [[ -f "$BACKUP_ROOT/apache-portconf-enabled" && "$(cat "$BACKUP_ROOT/apache-portconf-enabled")" == "true" ]]; then
        a2enconf svxlink-webui-port >/dev/null 2>&1 || true
      else
        a2disconf svxlink-webui-port >/dev/null 2>&1 || true
      fi
    fi
    apache2ctl configtest >/dev/null 2>&1 && systemctl reload apache2 || true
    systemctl restart svxlink >/dev/null 2>&1 || true
    systemctl restart svxlink-webui >/dev/null 2>&1 || true
    warn "Rollback ausgeführt. Installierte Pakete/Benutzer/Gruppen werden absichtlich nicht entfernt."
    warn "Backup: $BACKUP_ROOT"
  fi
  exit "$rc"
}
trap 'rollback $?' ERR
trap 'rollback 130' INT TERM

# -----------------------------------------------------------------------------
# System erkennen
# -----------------------------------------------------------------------------
[[ -r /etc/os-release ]] || die "/etc/os-release fehlt. Unterstützt werden Debian/Ubuntu-basierte Systeme."
# shellcheck disable=SC1091
source /etc/os-release
DISTRO_ID="${ID:-unknown}"
DISTRO_LIKE="${ID_LIKE:-}"
if [[ "$DISTRO_ID" != "debian" && "$DISTRO_ID" != "ubuntu" && "$DISTRO_LIKE" != *debian* ]]; then
  die "Nicht unterstützte Distribution: ${PRETTY_NAME:-$DISTRO_ID}. Aktuell werden Debian/Ubuntu-Systeme unterstützt."
fi

SVXLINK_CONFIG="/etc/svxlink/svxlink.conf"
ECHOLINK_CONFIG="/etc/svxlink/svxlink.d/ModuleEchoLink.conf"
NODE_INFO="/etc/svxlink/node_info.json"
if [[ -f "$SVXLINK_CONFIG" ]]; then
  DETECTED_NODE_INFO="$(ini_get "$SVXLINK_CONFIG" ReflectorLogic NODE_INFO_FILE)"
  if [[ -n "$DETECTED_NODE_INFO" ]]; then
    NODE_INFO="$DETECTED_NODE_INFO"
  elif [[ -f /var/lib/svxlink/node_info.json && ! -f /etc/svxlink/node_info.json ]]; then
    NODE_INFO="/var/lib/svxlink/node_info.json"
  fi
fi

SVXLINK_FOUND=false
if command -v svxlink >/dev/null 2>&1 || dpkg-query -W -f='${Status}' svxlink-server 2>/dev/null | grep -q 'ok installed'; then
  SVXLINK_FOUND=true
fi

# -----------------------------------------------------------------------------
# Vorhandene Werte erkennen
# -----------------------------------------------------------------------------
CURRENT_WEBUI_USER=""
if [[ -f /etc/systemd/system/svxlink-webui.service ]]; then
  CURRENT_WEBUI_USER="$(sed -n 's/^User=//p' /etc/systemd/system/svxlink-webui.service | head -1)"
fi
CURRENT_WEBUI_USER="${CURRENT_WEBUI_USER:-svxlink-webui}"

CURRENT_API_PORT=""
if [[ -f /etc/systemd/system/svxlink-webui.service ]]; then
  CURRENT_API_PORT="$(grep -Eo -- '--port[ =]+[0-9]+' /etc/systemd/system/svxlink-webui.service | grep -Eo '[0-9]+' | tail -1 || true)"
fi
CURRENT_API_PORT="${CURRENT_API_PORT:-12346}"

CURRENT_UI_PORT=""
CURRENT_HOSTNAME=""
CURRENT_WEB_AUTH_USER=""
if [[ -f /etc/apache2/sites-available/svxlink-webui.conf ]]; then
  CURRENT_UI_PORT="$(sed -nE 's/.*<VirtualHost \*:\s*([0-9]+)>.*/\1/p' /etc/apache2/sites-available/svxlink-webui.conf | head -1)"
  CURRENT_HOSTNAME="$(sed -nE 's/^\s*ServerName\s+([^ ]+).*/\1/p' /etc/apache2/sites-available/svxlink-webui.conf | head -1)"
fi
if [[ -f /etc/apache2/svxlink-webui.htpasswd ]]; then
  CURRENT_WEB_AUTH_USER="$(sed -n '1s/:.*//p' /etc/apache2/svxlink-webui.htpasswd)"
fi
CURRENT_UI_PORT="${CURRENT_UI_PORT:-80}"

CURRENT_CALLSIGN="$(ini_get "$SVXLINK_CONFIG" SimplexLogic CALLSIGN)"
CURRENT_CONTROL_PTY="$(ini_get "$SVXLINK_CONFIG" SimplexLogic DTMF_CTRL_PTY)"
CURRENT_STATE_PTY="$(ini_get "$SVXLINK_CONFIG" SimplexLogic STATE_PTY)"
CURRENT_FM_CALL="$(ini_get "$SVXLINK_CONFIG" ReflectorLogic CALLSIGN)"
CURRENT_FM_AUTH="$(ini_get "$SVXLINK_CONFIG" ReflectorLogic AUTH_KEY)"
CURRENT_DEFAULT_TG="$(ini_get "$SVXLINK_CONFIG" ReflectorLogic DEFAULT_TG)"
CURRENT_LOCATOR="$(ini_get "$SVXLINK_CONFIG" LocationInfo LOCATOR)"
CURRENT_FREQ="$(ini_get "$SVXLINK_CONFIG" LocationInfo FREQUENCY)"
CURRENT_TX_POWER="$(ini_get "$SVXLINK_CONFIG" LocationInfo TX_POWER)"
CURRENT_ANTENNA="$(ini_get "$SVXLINK_CONFIG" LocationInfo ANTENNA)"
CURRENT_AUDIO_DEV="$(ini_get "$SVXLINK_CONFIG" Rx1 AUDIO_DEV)"
CURRENT_PTT_TYPE="$(ini_get "$SVXLINK_CONFIG" Tx1 PTT_TYPE)"
CURRENT_HID_DEVICE="$(ini_get "$SVXLINK_CONFIG" Tx1 HID_DEVICE)"
CURRENT_HID_PIN="$(ini_get "$SVXLINK_CONFIG" Tx1 HID_PTT_PIN)"

CURRENT_ECHO_CALL="$(ini_get "$ECHOLINK_CONFIG" ModuleEchoLink CALLSIGN)"
CURRENT_ECHO_PASS="$(ini_get "$ECHOLINK_CONFIG" ModuleEchoLink PASSWORD)"
CURRENT_ECHO_ID="$(ini_get "$ECHOLINK_CONFIG" ModuleEchoLink ID)"
CURRENT_SYSOP="$(ini_get "$ECHOLINK_CONFIG" ModuleEchoLink SYSOPNAME)"
CURRENT_ECHO_LOCATION="$(ini_get "$ECHOLINK_CONFIG" ModuleEchoLink LOCATION)"

if [[ -f "$NODE_INFO" ]]; then
  CURRENT_ECHO_NODE_ID="$(python3 - "$NODE_INFO" <<'PY' 2>/dev/null || true
import json, sys
try:
    data=json.load(open(sys.argv[1], encoding='utf-8'))
    print(data.get('Echolink') or data.get('EchoLink') or '')
except Exception:
    pass
PY
)"
else
  CURRENT_ECHO_NODE_ID=""
fi

# Hardware Auto-Detect
# Standardfall: Debian/Ubuntu/Raspberry Pi mit direkt angeschlossenem SHARI.
# Virtualisierung/LXC wird nicht vorausgesetzt.

AUTO_AUDIO_DEV=""
AUTO_AUDIO_CARD=""
AUTO_AUDIO_CARD_ID=""

shopt -s nullglob

# Bevorzugt eine USB-Soundkarte. Der ALSA Card-ID-Name ist stabiler
# als eine numerische Kartennummer, die sich nach Reboots ändern kann.
for CARD_PATH in /sys/class/sound/card[0-9]*; do
  CARD_INDEX="${CARD_PATH##*card}"
  CARD_DEVICE="$(readlink -f "$CARD_PATH/device" 2>/dev/null || true)"
  CARD_ID_FILE="/proc/asound/card${CARD_INDEX}/id"
  CARD_ID=""
  [[ -r "$CARD_ID_FILE" ]] && CARD_ID="$(tr -d "[:space:]" < "$CARD_ID_FILE")"

  if [[ "$CARD_DEVICE" == *"/usb"* && -n "$CARD_ID" ]]; then
    AUTO_AUDIO_CARD="$CARD_INDEX"
    AUTO_AUDIO_CARD_ID="$CARD_ID"
    AUTO_AUDIO_DEV="alsa:plughw:CARD=${CARD_ID},DEV=0"
    break
  fi
done

# Falls keine USB-Karte erkannt wurde, erste verfügbare ALSA-Karte nehmen.
if [[ -z "$AUTO_AUDIO_DEV" ]]; then
  for CARD_PATH in /sys/class/sound/card[0-9]*; do
    CARD_INDEX="${CARD_PATH##*card}"
    CARD_ID_FILE="/proc/asound/card${CARD_INDEX}/id"
    CARD_ID=""
    [[ -r "$CARD_ID_FILE" ]] && CARD_ID="$(tr -d "[:space:]" < "$CARD_ID_FILE")"

    if [[ -n "$CARD_ID" ]]; then
      AUTO_AUDIO_CARD="$CARD_INDEX"
      AUTO_AUDIO_CARD_ID="$CARD_ID"
      AUTO_AUDIO_DEV="alsa:plughw:CARD=${CARD_ID},DEV=0"
      break
    fi
  done
fi

AUTO_AUDIO_DEV="${CURRENT_AUDIO_DEV:-${AUTO_AUDIO_DEV:-alsa:plughw:0,0}}"

# HID/PTT automatisch erkennen, wenn genau ein hidraw-Gerät vorhanden ist.
AUTO_HID=""
mapfile -t HID_DEVICES < <(find /dev -maxdepth 1 -type c -name "hidraw*" 2>/dev/null | sort -V)

if (( ${#HID_DEVICES[@]} == 1 )); then
  AUTO_HID="${HID_DEVICES[0]}"
fi

AUTO_HID="${CURRENT_HID_DEVICE:-${AUTO_HID:-/dev/hidraw0}}"

# Serielle SHARI/SA818-Schnittstelle ist optional.
# /dev/serial/by-id ist gegenüber ttyUSB-Nummern zu bevorzugen.
AUTO_SERIAL_PORT=""
SERIAL_BY_ID=(/dev/serial/by-id/*)

if (( ${#SERIAL_BY_ID[@]} == 1 )); then
  AUTO_SERIAL_PORT="${SERIAL_BY_ID[0]}"
else
  SERIAL_DEVICES=(/dev/ttyUSB* /dev/ttyACM*)
  if (( ${#SERIAL_DEVICES[@]} == 1 )); then
    AUTO_SERIAL_PORT="${SERIAL_DEVICES[0]}"
  fi
fi

SHARI_SERIAL_PORT_DEFAULT="${AUTO_SERIAL_PORT:-/dev/ttyUSB0}"

shopt -u nullglob
hr
say "${C_BOLD}${PROJECT_NAME} Installer ${INSTALLER_VERSION}${C_RESET}"
hr
say "System:       ${PRETTY_NAME:-$DISTRO_ID}"
say "Root-Modus:   $INVOCATION"
say "Quellpfad:    $SOURCE_DIR"
say "SvxLink:      $([[ "$SVXLINK_FOUND" == true ]] && echo 'gefunden' || echo 'nicht gefunden')"
say "Config:       $SVXLINK_CONFIG"
say "Control PTY:  ${CURRENT_CONTROL_PTY:-nicht erkannt}"
say "State PTY:    ${CURRENT_STATE_PTY:-nicht erkannt}"
say "Audio:        $AUTO_AUDIO_DEV"
say "HID/PTT:      $AUTO_HID"
say "SHARI UART:   ${AUTO_SERIAL_PORT:-nicht automatisch erkannt (optional)}"

if [[ -z "$CURRENT_AUDIO_DEV" && -z "$AUTO_AUDIO_CARD" ]]; then
  warn "Keine ALSA-Soundkarte automatisch erkannt. AUDIO_DEV muss vor dem Start geprüft werden."
fi

if [[ -n "$CURRENT_AUDIO_DEV" && "$CURRENT_AUDIO_DEV" =~ ^alsa:(plug)?hw:[0-9]+,[0-9]+$ ]]; then
  warn "Vorhandene numerische ALSA-Konfiguration erkannt: $CURRENT_AUDIO_DEV"
  warn "Sie wird beim Upgrade nicht automatisch geändert. Eine stabile CARD-ID ist bei mehreren Soundkarten robuster."
fi

echo

# -----------------------------------------------------------------------------
# Frage-/Antwort-Dialog
# -----------------------------------------------------------------------------
FULL_SVXLINK_INSTALL=false
if [[ "$SVXLINK_FOUND" == false ]]; then
  warn "SvxLink wurde nicht gefunden."
  if ask_yes_no "SvxLink inklusive benötigter Pakete installieren und grundlegend konfigurieren?" y; then
    FULL_SVXLINK_INSTALL=true
  else
    die "Ohne SvxLink kann die WebUI nicht sinnvoll installiert werden."
  fi
fi

INSTALL_DIR="$(ask 'Installationspfad der WebUI' '/opt/svxlink-webui')"
DOCROOT="$(ask 'Apache DocumentRoot' '/var/www/svxlink-webui')"
WEBUI_USER="$(ask 'Systembenutzer für die WebUI' "$CURRENT_WEBUI_USER")"
[[ "$WEBUI_USER" != "root" ]] || die "Die WebUI darf nicht als root laufen."
[[ "$WEBUI_USER" =~ ^[a-z_][a-z0-9_-]*[$]?$ ]] || die "Ungültiger Linux-Benutzername: $WEBUI_USER"

WEB_HOSTNAME="$(ask 'Hostname für Apache (leer = Zugriff per IP)' "$CURRENT_HOSTNAME")"
if [[ -n "$WEB_HOSTNAME" && ! "$WEB_HOSTNAME" =~ ^[A-Za-z0-9.-]+$ ]]; then
  die "Ungültiger Hostname: $WEB_HOSTNAME"
fi
UI_PORT="$(ask_port 'Port für die WebUI' "$CURRENT_UI_PORT")"
API_PORT="$(ask_port 'Interner Port für die API' "$CURRENT_API_PORT")"
[[ "$UI_PORT" != "$API_PORT" ]] || die "UI-Port und API-Port dürfen nicht identisch sein."

WEB_AUTH_USER="$(ask_web_username 'Login-Benutzer für die WebUI' "$CURRENT_WEB_AUTH_USER")"
WEB_AUTH_PASSWORD="$(ask_web_password)"

if [[ -n "${CURRENT_CALLSIGN:-${CURRENT_FM_CALL:-}}" ]]; then
  BASE_CALL="$(ask_callsign 'Lokales SvxLink-/Hotspot-Rufzeichen' "${CURRENT_CALLSIGN:-$CURRENT_FM_CALL}")"
else
  BASE_CALL="$(ask_callsign 'Lokales SvxLink-/Hotspot-Rufzeichen')"
fi

if [[ -n "$CURRENT_CONTROL_PTY" ]]; then
  CONTROL_PTY="$(ask 'SvxLink DTMF Control PTY' "$CURRENT_CONTROL_PTY")"
else
  CONTROL_PTY="$(ask 'SvxLink DTMF Control PTY' '/var/lib/svxlink/control/simplex_ctrl')"
fi

if [[ -n "$CURRENT_STATE_PTY" ]]; then
  RAW_STATE_PTY="$(ask 'SvxLink State PTY' "$CURRENT_STATE_PTY")"
else
  RAW_STATE_PTY="$(ask 'SvxLink State PTY' '/var/lib/svxlink/state/webui_state')"
fi
NORMALIZED_STATE="/run/svxlink-webui/state.jsonl"

CONFIGURE_FM=false
if [[ -n "$(ini_get "$SVXLINK_CONFIG" ReflectorLogic TYPE)" ]]; then
  ask_yes_no "FM-Funknetz-Konfiguration erkannt. Werte prüfen/aktualisieren?" n && CONFIGURE_FM=true
else
  ask_yes_no "FM-Funknetz jetzt konfigurieren?" y && CONFIGURE_FM=true
fi
[[ "$FULL_SVXLINK_INSTALL" == true ]] && CONFIGURE_FM=true

FM_CALL="${CURRENT_FM_CALL:-$BASE_CALL}"
FM_AUTH="$CURRENT_FM_AUTH"
DEFAULT_TG="${CURRENT_DEFAULT_TG:-0}"
LOCATOR="${CURRENT_LOCATOR:-}"
FREQUENCY="${CURRENT_FREQ:-}"
TX_POWER="${CURRENT_TX_POWER:-1}"
ANTENNA="${CURRENT_ANTENNA:-SHARI Hotspot}"
AUDIO_DEV="$AUTO_AUDIO_DEV"
PTT_TYPE="${CURRENT_PTT_TYPE:-Hidraw}"
HID_DEVICE="$AUTO_HID"
HID_PIN="${CURRENT_HID_PIN:-GPIO3}"

if [[ "$CONFIGURE_FM" == true ]]; then
  echo
  say "${C_BOLD}FM-Funknetz${C_RESET}"
  FM_CALL="$(ask_callsign 'FM-Funknetz Rufzeichen/Node-Call' "$FM_CALL")"
  if [[ -n "$CURRENT_FM_AUTH" ]]; then
    NEW_SECRET="$(ask_secret 'FM-Funknetz AUTH_KEY' true)"
    [[ -n "$NEW_SECRET" ]] && FM_AUTH="$NEW_SECRET"
  else
    while [[ -z "$FM_AUTH" ]]; do FM_AUTH="$(ask_secret 'FM-Funknetz AUTH_KEY')"; done
  fi
  DEFAULT_TG="$(ask 'Standard-Talkgroup' "${DEFAULT_TG:-0}")"
  while [[ ! "$DEFAULT_TG" =~ ^[0-9]+$ ]]; do DEFAULT_TG="$(ask 'Standard-Talkgroup' '0')"; done
  while [[ -z "$LOCATOR" ]]; do LOCATOR="$(ask 'Locator' "$LOCATOR")"; done
  while [[ -z "$FREQUENCY" ]]; do FREQUENCY="$(ask 'Frequenz in MHz' "$FREQUENCY")"; done
  [[ "$FREQUENCY" =~ ^[0-9]+([.][0-9]+)?$ ]] || die "Frequenz muss numerisch sein, z. B. 430.025"
  TX_POWER="$(ask 'TX-Leistung in Watt' "$TX_POWER")"
  [[ "$TX_POWER" =~ ^[0-9]+([.][0-9]+)?$ ]] || die "TX-Leistung muss numerisch sein."
  ANTENNA="$(ask 'Antennenbeschreibung' "$ANTENNA")"
  AUDIO_DEV="$(ask 'ALSA Audio Device' "$AUDIO_DEV")"
  PTT_TYPE="$(ask 'PTT-Typ' "$PTT_TYPE")"
  if [[ "${PTT_TYPE,,}" == "hidraw" ]]; then
    if (( ${#HID_DEVICES[@]} > 1 )); then
      echo "Gefundene HID-Geräte:"
      printf '  %s\n' "${HID_DEVICES[@]}"
    fi
    HID_DEVICE="$(ask 'HID-Gerät für PTT' "$HID_DEVICE")"
    HID_PIN="$(ask 'HID PTT Pin' "$HID_PIN")"
  fi
fi

CONFIGURE_ECHO=false
if [[ -f "$ECHOLINK_CONFIG" && -n "$CURRENT_ECHO_CALL" ]]; then
  ask_yes_no "EchoLink-Konfiguration erkannt. Werte prüfen/aktualisieren?" n && CONFIGURE_ECHO=true
else
  ask_yes_no "EchoLink jetzt konfigurieren?" y && CONFIGURE_ECHO=true
fi
[[ "$FULL_SVXLINK_INSTALL" == true ]] && CONFIGURE_ECHO=true

ECHO_CALL="${CURRENT_ECHO_CALL:-$BASE_CALL}"
ECHO_PASS="$CURRENT_ECHO_PASS"
ECHO_MODULE_ID="${CURRENT_ECHO_ID:-2}"
ECHO_NODE_ID="$CURRENT_ECHO_NODE_ID"
SYSOP_NAME="$CURRENT_SYSOP"
ECHO_LOCATION="${CURRENT_ECHO_LOCATION:-${LOCATOR:-}}"

if [[ "$CONFIGURE_ECHO" == true ]]; then
  echo
  say "${C_BOLD}EchoLink${C_RESET}"
  ECHO_CALL="$(ask_callsign 'EchoLink Rufzeichen' "$ECHO_CALL")"
  if [[ -n "$CURRENT_ECHO_PASS" ]]; then
    NEW_SECRET="$(ask_secret 'EchoLink Passwort' true)"
    [[ -n "$NEW_SECRET" ]] && ECHO_PASS="$NEW_SECRET"
  else
    while [[ -z "$ECHO_PASS" ]]; do ECHO_PASS="$(ask_secret 'EchoLink Passwort')"; done
  fi
  ECHO_MODULE_ID="$(ask 'EchoLink Modul-ID' "$ECHO_MODULE_ID")"
  while [[ ! "$ECHO_MODULE_ID" =~ ^[0-9]+$ ]]; do
    echo "Modul-ID muss numerisch sein."
    ECHO_MODULE_ID="$(ask 'EchoLink Modul-ID' '2')"
  done
  ECHO_NODE_ID="$(ask 'EchoLink Node-ID (leer falls noch nicht vorhanden)' "$ECHO_NODE_ID")"
  [[ -z "$ECHO_NODE_ID" || "$ECHO_NODE_ID" =~ ^[0-9]+$ ]] || die "EchoLink Node-ID muss numerisch sein."
  SYSOP_NAME="$(ask 'EchoLink SYSOPNAME' "$SYSOP_NAME")"
  ECHO_LOCATION="$(ask 'EchoLink LOCATION' "$ECHO_LOCATION")"
fi

# Portbelegung nur warnen; bei Upgrade sind die Ports erwartbar belegt.
for port in "$UI_PORT" "$API_PORT"; do
  if command -v ss >/dev/null 2>&1 && ss -lnt | awk '{print $4}' | grep -Eq "(^|:)$port$"; then
    warn "Port $port ist aktuell belegt (bei Upgrade normal)."
    ask_yes_no "Port $port trotzdem verwenden?" y || die "Installation abgebrochen."
  fi
done

# -----------------------------------------------------------------------------
# Plan anzeigen
# -----------------------------------------------------------------------------
echo
hr
say "${C_BOLD}Installationsplan${C_RESET}"
hr
say "SvxLink installieren:       $FULL_SVXLINK_INSTALL"
say "FM-Funknetz konfigurieren: $CONFIGURE_FM"
say "EchoLink konfigurieren:    $CONFIGURE_ECHO"
say "WebUI User:                $WEBUI_USER"
say "Installationspfad:         $INSTALL_DIR"
say "DocumentRoot:              $DOCROOT"
say "Hostname:                  ${WEB_HOSTNAME:-<kein ServerName / IP>}"
say "UI Port:                   $UI_PORT"
say "API Port:                  $API_PORT"
say "WebUI Login:               $WEB_AUTH_USER (Apache Basic Auth)"
say "Control PTY:               $CONTROL_PTY"
say "State PTY:                 $RAW_STATE_PTY"
say "SvxLink Call:              $BASE_CALL"
[[ "$CONFIGURE_FM" == true ]] && say "FM Call / Default TG:       $FM_CALL / $DEFAULT_TG"
[[ "$CONFIGURE_ECHO" == true ]] && say "EchoLink Call / Modul:      $ECHO_CALL / $ECHO_MODULE_ID"
say "Passwörter/Keys:           werden nicht angezeigt"
echo
ask_yes_no "Änderungen jetzt anwenden?" y || { echo "Abgebrochen."; exit 0; }

# -----------------------------------------------------------------------------
# Ab hier Änderungen; Backup scharf schalten
# -----------------------------------------------------------------------------
install -d -m 0700 "$BACKUP_ROOT"
for path in "${TOUCH_FILES[@]}"; do backup_file "$path"; done
ROLLBACK_ARMED=true

# Apache enabled state merken
APACHE_SITE_WAS_ENABLED=false
[[ -L /etc/apache2/sites-enabled/svxlink-webui.conf ]] && APACHE_SITE_WAS_ENABLED=true
APACHE_PORTCONF_WAS_ENABLED=false
[[ -L /etc/apache2/conf-enabled/svxlink-webui-port.conf ]] && APACHE_PORTCONF_WAS_ENABLED=true
printf '%s\n' "$APACHE_SITE_WAS_ENABLED" > "$BACKUP_ROOT/apache-site-enabled"
printf '%s\n' "$APACHE_PORTCONF_WAS_ENABLED" > "$BACKUP_ROOT/apache-portconf-enabled"

# -----------------------------------------------------------------------------
# Pakete
# -----------------------------------------------------------------------------
info "Systempakete installieren/prüfen"
export DEBIAN_FRONTEND=noninteractive
apt-get update
PACKAGES=(
  apache2
  apache2-utils
  python3
  python3-venv
  python3-pip
  nodejs
  npm
  rsync
  curl
  ca-certificates
  alsa-utils
  usbutils
)
if [[ "$SVXLINK_FOUND" == false ]]; then
  PACKAGES+=(svxlink-server svxlink-calibration-tools)
fi
apt-get install -y "${PACKAGES[@]}"

NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
(( NODE_MAJOR >= 18 )) || die "Node.js >= 18 wird benötigt. Installiert ist: $(node --version 2>/dev/null || echo unbekannt)"

# -----------------------------------------------------------------------------
# Benutzer/Gruppen
# -----------------------------------------------------------------------------
info "Service-Benutzer und Gruppen einrichten"
getent group svxlink-state-reader >/dev/null || groupadd --system svxlink-state-reader
getent group svxlink-control >/dev/null || groupadd --system svxlink-control

if ! id "$WEBUI_USER" >/dev/null 2>&1; then
  useradd --system --user-group --home-dir "$INSTALL_DIR" --shell /usr/sbin/nologin "$WEBUI_USER"
fi
WEBUI_GROUP="$(id -gn "$WEBUI_USER")"
usermod -a -G svxlink-state-reader,svxlink-control "$WEBUI_USER"

# Direkte Hardwareinstallation, z. B. Raspberry Pi.
# SvxLink benötigt Zugriff auf ALSA/HID, die WebUI optional auf den UART.
if id svxlink >/dev/null 2>&1 && getent group audio >/dev/null 2>&1; then
  usermod -a -G audio svxlink
fi

if getent group dialout >/dev/null 2>&1; then
  usermod -a -G dialout "$WEBUI_USER"
fi

# -----------------------------------------------------------------------------
# Source installieren
# -----------------------------------------------------------------------------
info "WebUI installieren"
mkdir -p "$INSTALL_DIR" "$DOCROOT" /etc/svxlink-webui /var/lib/svxlink-webui /usr/local/libexec

if [[ "$(readlink -f "$SOURCE_DIR")" != "$(readlink -f "$INSTALL_DIR")" ]]; then
  rsync -a \
    --exclude '.git/' \
    --exclude '.venv/' \
    --exclude 'backups/' \
    --exclude 'frontend/node_modules/' \
    --exclude 'frontend/dist/' \
    "$SOURCE_DIR/" "$INSTALL_DIR/"
fi

python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/backend/requirements.txt"

(
  cd "$INSTALL_DIR/frontend"
  if [[ -f package-lock.json ]]; then npm ci; else npm install; fi
  npm run lint
  npm run build
)

rm -rf "$DOCROOT"/*
cp -a "$INSTALL_DIR/frontend/dist/." "$DOCROOT/"

chown -R root:root "$INSTALL_DIR"
chmod -R a+rX "$INSTALL_DIR"
chown -R "$WEBUI_USER:$WEBUI_GROUP" /var/lib/svxlink-webui
chown -R root:root "$DOCROOT"
chmod -R a+rX "$DOCROOT"

# -----------------------------------------------------------------------------
# SvxLink Konfiguration
# -----------------------------------------------------------------------------
mkdir -p /etc/svxlink/svxlink.d /var/lib/svxlink/control /var/lib/svxlink/state

if [[ "$FULL_SVXLINK_INSTALL" == true || ! -s "$SVXLINK_CONFIG" ]]; then
  info "Neue SvxLink-Grundkonfiguration erzeugen"
  MULTIARCH="$(dpkg-architecture -qDEB_HOST_MULTIARCH 2>/dev/null || true)"
  MODULE_PATH=""
  [[ -n "$MULTIARCH" && -d "/usr/lib/$MULTIARCH/svxlink" ]] && MODULE_PATH="/usr/lib/$MULTIARCH/svxlink"
  [[ -z "$MODULE_PATH" && -d /usr/lib/svxlink ]] && MODULE_PATH="/usr/lib/svxlink"
  if [[ -z "$MODULE_PATH" ]]; then
    MODULE_PATH="$(find /usr/lib -maxdepth 3 -type d -name svxlink 2>/dev/null | head -1)"
  fi
  [[ -n "$MODULE_PATH" ]] || die "SvxLink MODULE_PATH konnte nicht erkannt werden."
  cat > "$SVXLINK_CONFIG" <<EOF
[GLOBAL]
MODULE_PATH=$MODULE_PATH
LOGICS=SimplexLogic,ReflectorLogic
CFG_DIR=svxlink.d
TIMESTAMP_FORMAT="%d %b %Y %H:%M:%S.%f"
CARD_SAMPLE_RATE=48000
LINKS=NetLink

[SimplexLogic]
TYPE=Simplex
RX=Rx1
TX=Tx1
MODULES=ModuleHelp,ModuleEchoLink
CALLSIGN=$BASE_CALL
SHORT_IDENT_INTERVAL=0
LONG_IDENT_INTERVAL=0
EVENT_HANDLER=/usr/share/svxlink/events.tcl
DTMF_CTRL_PTY=$CONTROL_PTY
STATE_PTY=$RAW_STATE_PTY
DEFAULT_LANG=de_DE
RGR_SOUND_DELAY=0
FX_GAIN_NORMAL=0
FX_GAIN_LOW=-12
MACROS=SimplexLogicMacros

[Rx1]
TYPE=Local
AUDIO_DEV=$AUDIO_DEV
AUDIO_CHANNEL=0
SQL_DET=VOX
SQL_START_DELAY=500
SQL_DELAY=500
SQL_HANGTIME=1500
VOX_FILTER_DEPTH=10
VOX_THRESH=220
DEEMPHASIS=0
DTMF_DEC_TYPE=INTERNAL
DTMF_MUTING=1
DTMF_HANGTIME=40

[Tx1]
TYPE=Local
AUDIO_DEV=$AUDIO_DEV
AUDIO_CHANNEL=0
PTT_TYPE=$PTT_TYPE
HID_DEVICE=$HID_DEVICE
HID_PTT_PIN=$HID_PIN
TIMEOUT=300
TX_DELAY=500
PREEMPHASIS=0
DTMF_TONE_LENGTH=100
DTMF_TONE_SPACING=50
DTMF_DIGIT_PWR=-15

[ReflectorLogic]
TYPE=Reflector
DNS_DOMAIN=reflector-network.de
CALLSIGN=$FM_CALL
AUTH_KEY=$FM_AUTH
DEFAULT_TG=$DEFAULT_TG
TG_SELECT_TIMEOUT=60
ANNOUNCE_REMOTE_MIN_INTERVAL=300
EVENT_HANDLER=/usr/share/svxlink/events.tcl
NODE_INFO_FILE=$NODE_INFO
MUTE_FIRST_TX_LOC=0
MUTE_FIRST_TX_REM=0
TMP_MONITOR_TIMEOUT=3600
UDP_HEARTBEAT_INTERVAL=15
QSY_PENDING_TIMEOUT=15
DEFAULT_LANG=de_DE

[NetLink]
CONNECT_LOGICS=SimplexLogic:9:thr,ReflectorLogic
DEFAULT_ACTIVE=1
TIMEOUT=600

[LocationInfo]
CALLSIGN=$FM_CALL
LOCATOR=$LOCATOR
FREQUENCY=$FREQUENCY
TX_POWER=$TX_POWER
ANTENNA=$ANTENNA

[SimplexLogicMacros]
1=EchoLink:
2=:#
EOF
else
  info "Vorhandene SvxLink-Konfiguration gezielt ergänzen"
  ini_set "$SVXLINK_CONFIG" SimplexLogic CALLSIGN "$BASE_CALL"
  ini_set "$SVXLINK_CONFIG" SimplexLogic DTMF_CTRL_PTY "$CONTROL_PTY"
  ini_set "$SVXLINK_CONFIG" SimplexLogic STATE_PTY "$RAW_STATE_PTY"

  if [[ "$CONFIGURE_FM" == true ]]; then
    LOGICS="$(ini_csv_add "$SVXLINK_CONFIG" GLOBAL LOGICS ReflectorLogic)"
    LINKS="$(ini_csv_add "$SVXLINK_CONFIG" GLOBAL LINKS NetLink)"
    ini_set "$SVXLINK_CONFIG" GLOBAL LOGICS "$LOGICS"
    ini_set "$SVXLINK_CONFIG" GLOBAL LINKS "$LINKS"
    ini_set "$SVXLINK_CONFIG" ReflectorLogic TYPE Reflector
    ini_set "$SVXLINK_CONFIG" ReflectorLogic DNS_DOMAIN reflector-network.de
    ini_set "$SVXLINK_CONFIG" ReflectorLogic CALLSIGN "$FM_CALL"
    ini_set "$SVXLINK_CONFIG" ReflectorLogic AUTH_KEY "$FM_AUTH"
    ini_set "$SVXLINK_CONFIG" ReflectorLogic DEFAULT_TG "$DEFAULT_TG"
    ini_set "$SVXLINK_CONFIG" ReflectorLogic NODE_INFO_FILE "$NODE_INFO"
    ini_set "$SVXLINK_CONFIG" NetLink CONNECT_LOGICS 'SimplexLogic:9:thr,ReflectorLogic'
    ini_set "$SVXLINK_CONFIG" NetLink DEFAULT_ACTIVE 1
    ini_set "$SVXLINK_CONFIG" LocationInfo CALLSIGN "$FM_CALL"
    ini_set "$SVXLINK_CONFIG" LocationInfo LOCATOR "$LOCATOR"
    ini_set "$SVXLINK_CONFIG" LocationInfo FREQUENCY "$FREQUENCY"
    ini_set "$SVXLINK_CONFIG" LocationInfo TX_POWER "$TX_POWER"
    ini_set "$SVXLINK_CONFIG" LocationInfo ANTENNA "$ANTENNA"
  fi

  if [[ "$CONFIGURE_ECHO" == true ]]; then
    MODULES="$(ini_csv_add "$SVXLINK_CONFIG" SimplexLogic MODULES ModuleEchoLink)"
    ini_set "$SVXLINK_CONFIG" SimplexLogic MODULES "$MODULES"
  fi
fi

# -----------------------------------------------------------------------------
# EchoLink Konfiguration
# -----------------------------------------------------------------------------
if [[ "$CONFIGURE_ECHO" == true ]]; then
  info "EchoLink konfigurieren"
  ini_set "$ECHOLINK_CONFIG" ModuleEchoLink NAME EchoLink
  ini_set "$ECHOLINK_CONFIG" ModuleEchoLink ID "$ECHO_MODULE_ID"
  ini_set "$ECHOLINK_CONFIG" ModuleEchoLink TIMEOUT 60
  ini_set "$ECHOLINK_CONFIG" ModuleEchoLink SERVERS servers.echolink.org
  ini_set "$ECHOLINK_CONFIG" ModuleEchoLink CALLSIGN "$ECHO_CALL"
  ini_set "$ECHOLINK_CONFIG" ModuleEchoLink PASSWORD "$ECHO_PASS"
  [[ -n "$SYSOP_NAME" ]] && ini_set "$ECHOLINK_CONFIG" ModuleEchoLink SYSOPNAME "$SYSOP_NAME"
  [[ -n "$ECHO_LOCATION" ]] && ini_set "$ECHOLINK_CONFIG" ModuleEchoLink LOCATION "$ECHO_LOCATION"
  ini_set "$ECHOLINK_CONFIG" ModuleEchoLink MAX_QSOS 10
  ini_set "$ECHOLINK_CONFIG" ModuleEchoLink MAX_CONNECTIONS 11
  ini_set "$ECHOLINK_CONFIG" ModuleEchoLink LINK_IDLE_TIMEOUT 1800
fi

if [[ -n "$ECHO_NODE_ID" ]]; then
  info "EchoLink Node-ID in node_info.json eintragen"
  python3 - "$NODE_INFO" "$ECHO_NODE_ID" <<'PY'
from pathlib import Path
import json, sys
p=Path(sys.argv[1]); node=sys.argv[2]
try:
    data=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
except Exception:
    data={}
data['Echolink']=node
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
PY
fi

# SvxLink-Zugangsdaten nicht weltlesbar lassen.
if getent group svxlink >/dev/null 2>&1; then
  chown root:svxlink "$SVXLINK_CONFIG" 2>/dev/null || true
  chmod 0640 "$SVXLINK_CONFIG" 2>/dev/null || true
  if [[ -f "$ECHOLINK_CONFIG" ]]; then
    chown root:svxlink "$ECHOLINK_CONFIG" 2>/dev/null || true
    chmod 0640 "$ECHOLINK_CONFIG" 2>/dev/null || true
  fi
fi

# -----------------------------------------------------------------------------
# EchoLink Event Bridge
# -----------------------------------------------------------------------------
if [[ "$CONFIGURE_ECHO" == true || -f "$ECHOLINK_CONFIG" ]]; then
  info "EchoLink Event Bridge installieren"
  mkdir -p /usr/share/svxlink/events.d/local /var/lib/svxlink/echolink-webui
  cat > /usr/share/svxlink/events.d/local/EchoLinkWebUI.tcl <<'TCL'
namespace eval EchoLinkWebUI {
  variable event_file "/var/lib/svxlink/echolink-webui/events.tsv"

  proc emit {event {call ""} {clients ""}} {
    variable event_file
    if {[catch {
      set fh [open $event_file "a"]
      puts $fh "[clock seconds]\t$event\t$call\t$clients"
      close $fh
    } err]} {
      puts "EchoLinkWebUI: $err"
    }
  }
}

EchoLinkWebUI::emit "startup"

if {[llength [info procs activating_module]] && ![llength [info procs echolink_webui_original_activating_module]]} {
  rename activating_module echolink_webui_original_activating_module
  proc activating_module {} {
    EchoLinkWebUI::emit "module_active"
    return [echolink_webui_original_activating_module]
  }
}

if {[llength [info procs deactivating_module]] && ![llength [info procs echolink_webui_original_deactivating_module]]} {
  rename deactivating_module echolink_webui_original_deactivating_module
  proc deactivating_module {} {
    EchoLinkWebUI::emit "module_inactive"
    return [echolink_webui_original_deactivating_module]
  }
}

if {[llength [info procs connecting_to]] && ![llength [info procs echolink_webui_original_connecting_to]]} {
  rename connecting_to echolink_webui_original_connecting_to
  proc connecting_to {call} {
    EchoLinkWebUI::emit "connecting_to" $call
    return [echolink_webui_original_connecting_to $call]
  }
}

if {[llength [info procs remote_connected]] && ![llength [info procs echolink_webui_original_remote_connected]]} {
  rename remote_connected echolink_webui_original_remote_connected
  proc remote_connected {call} {
    EchoLinkWebUI::emit "remote_connected" $call
    return [echolink_webui_original_remote_connected $call]
  }
}

if {[llength [info procs connected]] && ![llength [info procs echolink_webui_original_connected]]} {
  rename connected echolink_webui_original_connected
  proc connected {call} {
    EchoLinkWebUI::emit "connected" $call
    return [echolink_webui_original_connected $call]
  }
}

if {[llength [info procs disconnected]] && ![llength [info procs echolink_webui_original_disconnected]]} {
  rename disconnected echolink_webui_original_disconnected
  proc disconnected {call} {
    EchoLinkWebUI::emit "disconnected" $call
    return [echolink_webui_original_disconnected $call]
  }
}

if {[llength [info procs client_list_changed]] && ![llength [info procs echolink_webui_original_client_list_changed]]} {
  rename client_list_changed echolink_webui_original_client_list_changed
  proc client_list_changed {client_list} {
    EchoLinkWebUI::emit "client_list_changed" "" [join $client_list ","]
    return [echolink_webui_original_client_list_changed $client_list]
  }
}
TCL
fi

# Besitz für Eventdatei; svxlink schreibt, WebUI liest.
SVXLINK_USER="svxlink"
id svxlink >/dev/null 2>&1 || SVXLINK_USER="root"
install -d -m 2770 -o "$SVXLINK_USER" -g "$WEBUI_GROUP" /var/lib/svxlink/echolink-webui
touch /var/lib/svxlink/echolink-webui/events.tsv
chown "$SVXLINK_USER:$WEBUI_GROUP" /var/lib/svxlink/echolink-webui/events.tsv
chmod 0660 /var/lib/svxlink/echolink-webui/events.tsv

# -----------------------------------------------------------------------------
# Sichere Control-PTY Permission Binder
# -----------------------------------------------------------------------------
info "PTY-Berechtigungen installieren"
cat > /usr/local/libexec/svxlink-webui-control-permissions <<'PY'
#!/usr/bin/env python3
from pathlib import Path
import grp, os, stat, sys

if len(sys.argv) != 3:
    raise SystemExit("usage: svxlink-webui-control-permissions PATH GROUP")
path=Path(sys.argv[1]); group=sys.argv[2]
info=os.lstat(path)
target=path
if stat.S_ISLNK(info.st_mode):
    raw=os.readlink(path)
    target=Path(raw)
    if not target.is_absolute() or target.parent != Path('/dev/pts') or not target.name.isdecimal():
        raise SystemExit('Control PTY symlink must target direct /dev/pts/N')
fd=os.open(target, os.O_RDWR | os.O_NONBLOCK | os.O_NOFOLLOW)
try:
    st=os.fstat(fd)
    if not stat.S_ISCHR(st.st_mode):
        raise SystemExit('Control PTY target is not a character device')
    gid=grp.getgrnam(group).gr_gid
    os.fchown(fd, -1, gid)
    os.fchmod(fd, 0o660)
finally:
    os.close(fd)
PY
chmod 0755 /usr/local/libexec/svxlink-webui-control-permissions

# State-Permission Helper kommt aus dem Projekt.
cat > /etc/systemd/system/svxlink-webui-state-permissions.service <<EOF
[Unit]
Description=SvxLink WebUI STATE_PTY permissions
After=svxlink.service

[Service]
Type=oneshot
ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/backend/app/state_pty_permissions.py $RAW_STATE_PTY --group svxlink-state-reader
EOF

cat > /etc/systemd/system/svxlink-webui-state-permissions.path <<EOF
[Unit]
Description=Watch SvxLink STATE_PTY for WebUI

[Path]
PathExists=$RAW_STATE_PTY
PathChanged=$RAW_STATE_PTY
Unit=svxlink-webui-state-permissions.service

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/svxlink-webui-control-permissions.service <<EOF
[Unit]
Description=SvxLink WebUI Control PTY permissions
After=svxlink.service

[Service]
Type=oneshot
ExecStart=/usr/local/libexec/svxlink-webui-control-permissions $CONTROL_PTY svxlink-control
EOF

cat > /etc/systemd/system/svxlink-webui-control-permissions.path <<EOF
[Unit]
Description=Watch SvxLink Control PTY for WebUI

[Path]
PathExists=$CONTROL_PTY
PathChanged=$CONTROL_PTY
Unit=svxlink-webui-control-permissions.service

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/svxlink-webui-state-collector.service <<EOF
[Unit]
Description=SvxLink WebUI State PTY collector
After=svxlink.service svxlink-webui-state-permissions.service

[Service]
Type=simple
User=$WEBUI_USER
Group=$WEBUI_GROUP
SupplementaryGroups=svxlink-state-reader
RuntimeDirectory=svxlink-webui
RuntimeDirectoryMode=0750
ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/backend/app/state_pty_collector.py --input $RAW_STATE_PTY --output $NORMALIZED_STATE
Restart=always
RestartSec=2
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# -----------------------------------------------------------------------------
# Environment
# -----------------------------------------------------------------------------
info "WebUI Environment schreiben"
cat > /etc/svxlink-webui/environment <<EOF
SVXLINK_WEBUI_DEMO=false
SVXLINK_NODE_NAME=$BASE_CALL
SVXLINK_CALLSIGN=$BASE_CALL
SVXLINK_LOCATION=${ECHO_LOCATION:-${LOCATOR:-}}
SVXLINK_CONFIG_PATH=$SVXLINK_CONFIG
SVXLINK_NODE_INFO_PATH=$NODE_INFO
SVXLINK_SERVICE_NAME=svxlink
SVXLINK_STATE_PTY_ENABLED=true
SVXLINK_STATE_PTY_PATH=$NORMALIZED_STATE
SVXLINK_STATE_PTY_RAW_PATH=$RAW_STATE_PTY
SVXLINK_ACTIVITY_DB=/var/lib/svxlink-webui/activity.sqlite3
TG_CONTROL_ENABLED=true
TG_CONTROL_PTY=$CONTROL_PTY
SHARI_SERIAL_PORT=$SHARI_SERIAL_PORT_DEFAULT
SHARI_SERIAL_BAUD=9600
SHARI_SERIAL_TIMEOUT=0.8
FM_FUNKNETZ_MQTT_ENABLED=true
FM_FUNKNETZ_MQTT_HOST=mqtt.fm-funknetz.de
FM_FUNKNETZ_MQTT_PORT=1883
FM_FUNKNETZ_MQTT_TOPICS=/server/statethr/1,/server/state/loginz,/server/state/logins
FM_FUNKNETZ_MQTT_STALE_AFTER=90
FM_FUNKNETZ_NODES_MQTT_HOST=status.thueringen.link
FM_FUNKNETZ_NODES_MQTT_PORT=1883
FM_FUNKNETZ_STATS_URL=https://dashboard.fm-funknetz.de/stats_api.php
FM_FUNKNETZ_STATS_CACHE_TTL=300
EOF
chown root:"$WEBUI_GROUP" /etc/svxlink-webui/environment
chmod 0640 /etc/svxlink-webui/environment

# -----------------------------------------------------------------------------
# WebUI systemd service
# -----------------------------------------------------------------------------
info "WebUI systemd-Service schreiben"
cat > /etc/systemd/system/svxlink-webui.service <<EOF
[Unit]
Description=SvxLink WebUI FastAPI backend
After=network-online.target svxlink.service
Wants=network-online.target

[Service]
Type=simple
User=$WEBUI_USER
Group=$WEBUI_GROUP
SupplementaryGroups=svxlink-control svxlink-state-reader
WorkingDirectory=$INSTALL_DIR/backend
EnvironmentFile=-/etc/svxlink-webui/environment
ExecStart=$INSTALL_DIR/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $API_PORT
Restart=on-failure
RestartSec=2
NoNewPrivileges=true
PrivateTmp=true
UMask=0027

[Install]
WantedBy=multi-user.target
EOF

# -----------------------------------------------------------------------------
# Apache
# -----------------------------------------------------------------------------
info "Apache konfigurieren"
a2enmod proxy proxy_http proxy_wstunnel headers rewrite auth_basic authn_file >/dev/null

printf '%s\n' "$WEB_AUTH_PASSWORD" \
  | htpasswd -cBi /etc/apache2/svxlink-webui.htpasswd "$WEB_AUTH_USER" >/dev/null
chown root:www-data /etc/apache2/svxlink-webui.htpasswd
chmod 0640 /etc/apache2/svxlink-webui.htpasswd

if grep -RhsE "^[[:space:]]*Listen[[:space:]]+$UI_PORT([[:space:]]|$)"     /etc/apache2 2>/dev/null     | grep -q .; then
  cat > /etc/apache2/conf-available/svxlink-webui-port.conf <<EOF
# Port $UI_PORT wird bereits durch eine andere Apache-Konfiguration geöffnet.
EOF
else
  cat > /etc/apache2/conf-available/svxlink-webui-port.conf <<EOF
Listen $UI_PORT
EOF
fi

a2enconf svxlink-webui-port >/dev/null

SERVER_NAME_LINE=""
[[ -n "$WEB_HOSTNAME" ]] && SERVER_NAME_LINE="    ServerName $WEB_HOSTNAME"

cat > /etc/apache2/sites-available/svxlink-webui.conf <<EOF
<VirtualHost *:$UI_PORT>
$SERVER_NAME_LINE
    DocumentRoot $DOCROOT

    <Directory $DOCROOT>
        Options -Indexes +FollowSymLinks
        AllowOverride None
        Require all granted
    </Directory>

    <Location "/">
        AuthType Basic
        AuthName "SvxLink WebUI"
        AuthBasicProvider file
        AuthUserFile /etc/apache2/svxlink-webui.htpasswd
        Require valid-user
    </Location>

    ProxyPreserveHost On

    ProxyPass /api/ws/ ws://127.0.0.1:$API_PORT/api/ws/
    ProxyPassReverse /api/ws/ ws://127.0.0.1:$API_PORT/api/ws/

    ProxyPass /api/ http://127.0.0.1:$API_PORT/api/
    ProxyPassReverse /api/ http://127.0.0.1:$API_PORT/api/

    RewriteEngine On
    RewriteCond %{REQUEST_URI} !^/api/
    RewriteCond %{DOCUMENT_ROOT}%{REQUEST_URI} !-f
    RewriteCond %{DOCUMENT_ROOT}%{REQUEST_URI} !-d
    RewriteRule ^ /index.html [L]

    ErrorLog \${APACHE_LOG_DIR}/svxlink-webui-error.log
    CustomLog \${APACHE_LOG_DIR}/svxlink-webui-access.log combined
</VirtualHost>
EOF

a2ensite svxlink-webui >/dev/null
apache2ctl configtest

# -----------------------------------------------------------------------------
# Syntax / Tests vor Restart
# -----------------------------------------------------------------------------
info "Projekt prüfen"
"$INSTALL_DIR/.venv/bin/python" -m py_compile "$INSTALL_DIR"/backend/app/*.py
(
  cd "$INSTALL_DIR"
  PYTHONPATH=backend "$INSTALL_DIR/.venv/bin/python" -m pytest backend/app/test_api.py -q
)

# -----------------------------------------------------------------------------
# Dienste starten
# -----------------------------------------------------------------------------
info "Dienste neu laden/starten"
systemctl daemon-reload
systemctl enable --now svxlink-webui-state-permissions.path svxlink-webui-control-permissions.path >/dev/null
systemctl enable svxlink-webui-state-collector.service svxlink-webui.service >/dev/null

systemctl restart svxlink

# Ein laufender svxlink-Prozess allein reicht nicht.
# SimplexLogic muss erfolgreich initialisiert sein und beide PTYs erzeugen.
for _ in {1..20}; do
  if systemctl is-active --quiet svxlink && [[ -e "$CONTROL_PTY" && -e "$RAW_STATE_PTY" ]]; then
    break
  fi
  sleep 0.25
done

systemctl is-active --quiet svxlink || die "SvxLink startet mit der neuen Konfiguration nicht."

if [[ ! -e "$CONTROL_PTY" || ! -e "$RAW_STATE_PTY" ]]; then
  warn "SvxLink läuft als Prozess, aber SimplexLogic ist nicht vollständig betriebsbereit."

  if [[ -f /var/log/svxlink ]]; then
    echo
    warn "Letzte SvxLink-Logzeilen:"
    tail -80 /var/log/svxlink >&2 || true
  fi

  [[ -e "$CONTROL_PTY" ]] || warn "Control PTY fehlt: $CONTROL_PTY"
  [[ -e "$RAW_STATE_PTY" ]] || warn "State PTY fehlt: $RAW_STATE_PTY"

  die "SvxLink-Hardware/Audio initialisiert nicht vollständig. Prüfe ALSA, RX/TX und PTT."
fi

# Permission Binder direkt ausführen; Path-Units kümmern sich danach um Neustarts.
systemctl start svxlink-webui-state-permissions.service
systemctl start svxlink-webui-control-permissions.service
systemctl restart svxlink-webui-state-collector.service
systemctl restart svxlink-webui.service
systemctl reload apache2

systemctl is-active --quiet svxlink-webui || die "svxlink-webui ist nicht aktiv."
systemctl is-active --quiet apache2 || die "Apache ist nicht aktiv."

# Healthcheck
sleep 1
curl -fsS "http://127.0.0.1:$API_PORT/health" >/dev/null || die "Backend-Healthcheck fehlgeschlagen."

UNAUTH_CODE="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$UI_PORT/")"
[[ "$UNAUTH_CODE" == "401" ]] || die "WebUI ist ohne Anmeldung erreichbar (erwartet HTTP 401, erhalten: $UNAUTH_CODE)."

SVXWEBUI_CHECK_USER="$WEB_AUTH_USER" \
SVXWEBUI_CHECK_PASSWORD="$WEB_AUTH_PASSWORD" \
SVXWEBUI_CHECK_PORT="$UI_PORT" \
python3 <<'PY'
import base64
import os
import sys
import urllib.request

user = os.environ["SVXWEBUI_CHECK_USER"]
password = os.environ["SVXWEBUI_CHECK_PASSWORD"]
port = os.environ["SVXWEBUI_CHECK_PORT"]

token = base64.b64encode(
    f"{user}:{password}".encode()
).decode()

request = urllib.request.Request(
    f"http://127.0.0.1:{port}/",
    headers={
        "Authorization": f"Basic {token}"
    },
)

try:
    with urllib.request.urlopen(
        request,
        timeout=5,
    ) as response:
        if response.status != 200:
            raise RuntimeError(
                f"HTTP {response.status}"
            )
except Exception as exc:
    print(
        "Authentifizierter WebUI-Healthcheck "
        f"fehlgeschlagen: {exc}",
        file=sys.stderr,
    )
    raise SystemExit(1)
PY

# -----------------------------------------------------------------------------
# Fertig
# -----------------------------------------------------------------------------
ROLLBACK_ARMED=false
trap - ERR INT TERM

IP_ADDR="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [[ -n "$WEB_HOSTNAME" ]]; then
  ACCESS_HOST="$WEB_HOSTNAME"
else
  ACCESS_HOST="${IP_ADDR:-SERVER-IP}"
fi

if [[ "$UI_PORT" == "80" ]]; then
  ACCESS_URL="http://$ACCESS_HOST/"
else
  ACCESS_URL="http://$ACCESS_HOST:$UI_PORT/"
fi

echo
hr
say "${C_GREEN}${C_BOLD}Installation erfolgreich${C_RESET}"
hr
say "WebUI:        $ACCESS_URL"
say "API intern:  http://127.0.0.1:$API_PORT/"
say "Serviceuser: $WEBUI_USER"
say "WebUI Login:  $WEB_AUTH_USER"
say "Control PTY: $CONTROL_PTY -> $(readlink -f "$CONTROL_PTY" 2>/dev/null || echo 'nicht aufgelöst')"
say "State PTY:   $RAW_STATE_PTY -> $(readlink -f "$RAW_STATE_PTY" 2>/dev/null || echo 'nicht aufgelöst')"
say "Backup:      $BACKUP_ROOT"
echo
say "EchoLink benötigt je nach Netzwerk/Router weiterhin die üblichen eingehenden UDP-Ports 5198/5199."
say "Die WebUI ist mit Apache Basic Auth geschützt. Bei Zugriff über nicht vertrauenswürdige Netze zusätzlich HTTPS oder VPN verwenden."
unset WEB_AUTH_PASSWORD
echo
ok "Fertig."
