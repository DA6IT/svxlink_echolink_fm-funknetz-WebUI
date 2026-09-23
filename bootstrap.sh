#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="SvxLink WebUI"
GITHUB_REPO="DA6IT/svxlink_echolink_fm-funknetz-WebUI"
BRANCH="${SVXLINK_WEBUI_BRANCH:-main}"

C_GREEN='\033[0;32m'
C_YELLOW='\033[0;33m'
C_RED='\033[0;31m'
C_CYAN='\033[0;36m'
C_BOLD='\033[1m'
C_RESET='\033[0m'

say()  { printf '%b\n' "$*"; }
info() { say "${C_CYAN}>>>${C_RESET} $*"; }
ok()   { say "${C_GREEN}✓${C_RESET} $*"; }
warn() { say "${C_YELLOW}WARNUNG:${C_RESET} $*"; }
die()  { say "${C_RED}FEHLER:${C_RESET} $*" >&2; exit 1; }
hr()   { printf '%s\n' '============================================================'; }

cleanup() {
    if [[ -n "${TMPDIR_INSTALL:-}" && -d "${TMPDIR_INSTALL:-}" ]]; then
        rm -rf "$TMPDIR_INSTALL"
    fi
}

trap cleanup EXIT INT TERM

hr
say "${C_BOLD}${PROJECT} – GitHub Bootstrap Installer${C_RESET}"
hr

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo
    die "Dieser Installer benötigt Root-Rechte."
fi

for command in curl tar mktemp; do
    command -v "$command" >/dev/null 2>&1 \
        || die "Benötigtes Programm fehlt: $command"
done

case "$BRANCH" in
    *[!A-Za-z0-9._/-]*|'')
        die "Ungültiger Git-Branch: $BRANCH"
        ;;
esac

ARCHIVE_URL="https://github.com/${GITHUB_REPO}/archive/refs/heads/${BRANCH}.tar.gz"

TMPDIR_INSTALL="$(mktemp -d /tmp/svxlink-webui-install.XXXXXX)"
ARCHIVE="$TMPDIR_INSTALL/source.tar.gz"
SOURCE="$TMPDIR_INSTALL/source"

mkdir -p "$SOURCE"

echo
info "Lade aktuellen Stand von GitHub"

say "Repository: https://github.com/${GITHUB_REPO}"
say "Branch:     ${BRANCH}"

curl \
    --fail \
    --silent \
    --show-error \
    --location \
    --retry 3 \
    --connect-timeout 15 \
    "$ARCHIVE_URL" \
    --output "$ARCHIVE"

[[ -s "$ARCHIVE" ]] \
    || die "GitHub-Archiv wurde nicht heruntergeladen."

info "Prüfe GitHub-Archiv"

tar -tzf "$ARCHIVE" >/dev/null \
    || die "Das heruntergeladene Archiv ist ungültig."

tar \
    -xzf "$ARCHIVE" \
    --strip-components=1 \
    -C "$SOURCE"

[[ -f "$SOURCE/install.sh" ]] \
    || die "install.sh fehlt im heruntergeladenen Projekt."

[[ -f "$SOURCE/install/updater-bootstrap.sh" ]] \
    || die "Updater-Bootstrap fehlt im heruntergeladenen Projekt."

chmod +x "$SOURCE/install.sh"

ok "Projekt vollständig heruntergeladen."

echo
info "Starte interaktiven Installer"
echo

if [[ -r /dev/tty ]]; then
    bash "$SOURCE/install.sh" </dev/tty
else
    die "/dev/tty ist nicht verfügbar. Der Installer benötigt ein interaktives Terminal."
fi

echo
ok "Installation abgeschlossen."
