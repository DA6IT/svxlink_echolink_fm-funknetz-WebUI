#!/usr/bin/env bash
set -Eeuo pipefail

INSTALL_DIR="${1:-/opt/svxlink-webui}"
DOCROOT="${2:-/var/www/svxlink-webui}"
API_PORT="${3:-12346}"
UI_PORT="${4:-80}"

WEBUI_USER="${SVXLINK_WEBUI_USER:-svxlink-webui}"
UPDATER_USER="svxlink-webui-updater"
UPDATE_GROUP="svxlink-webui-update"
IPC_ROOT="/var/lib/svxlink-webui-update"
UPDATE_DATA="/var/lib/svxlink-webui-updater"

ok() { printf 'OK  %s\n' "$*"; }
fail() { printf 'FAIL %s\n' "$*" >&2; exit 1; }
check() { "$@" || fail "$*"; }

check id "$WEBUI_USER"
check id "$UPDATER_USER"
check getent group "$UPDATE_GROUP"
ok "users/groups"

check test -d "$INSTALL_DIR/.git"
check test -L "$INSTALL_DIR/.venv-current"
check test -x "$INSTALL_DIR/.venv-current/bin/uvicorn"
ok "git checkout and active runtime"

check test -d "$UPDATE_DATA/venvs"
check test -d "$IPC_ROOT/status"
check test -d "$IPC_ROOT/control"
check test -d "$IPC_ROOT/requests"
ok "updater data and IPC"

runuser -u "$WEBUI_USER" -- test ! -w "$INSTALL_DIR/.git" \
  || fail "$WEBUI_USER can write .git"
runuser -u "$UPDATER_USER" -- test -w "$INSTALL_DIR/.git" \
  || fail "$UPDATER_USER cannot write .git"
runuser -u "$WEBUI_USER" -- test -x "$INSTALL_DIR/.venv-current/bin/python" \
  || fail "$WEBUI_USER cannot execute active runtime"
runuser -u "$UPDATER_USER" -- test -w "$DOCROOT" \
  || fail "$UPDATER_USER cannot write docroot"
runuser -u www-data -- test -r "$DOCROOT/index.html" \
  || fail "www-data cannot read index.html"
ok "privilege separation and ACLs"

check systemctl is-active --quiet svxlink-webui
check systemctl is-active --quiet svxlink-webui-updater
check systemctl is-active --quiet apache2
ok "core services active"

CONTROL_PTY="/var/lib/svxlink/control/simplex_ctrl"
RAW_STATE_PTY="/var/lib/svxlink/state/webui_state"

if [[ -e "$CONTROL_PTY" && -e "$RAW_STATE_PTY" ]]; then
  check systemctl is-active --quiet svxlink-webui-state-collector
  ok "SvxLink hardware PTYs and state collector active"
else
  printf 'WARN SvxLink hardware PTYs not present; state collector check skipped\n'
fi

curl -fsS "http://127.0.0.1:$API_PORT/health" >/dev/null \
  || fail "backend health failed"
ok "backend health"

for _ in {1..20}; do
  [[ -r "$IPC_ROOT/status/worker-status.json" ]] && break
  sleep 0.25
done
check test -r "$IPC_ROOT/status/worker-status.json"
ok "worker status"

UNAUTH_CODE="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$UI_PORT/")"
[[ "$UNAUTH_CODE" == "401" ]] \
  || fail "Apache returned $UNAUTH_CODE, expected 401"
ok "Apache Basic Auth active (401 without credentials)"

grep -Eq '^[[:space:]]*ProxyPreserveHost[[:space:]]+On([[:space:]]|$)' \
  /etc/apache2/sites-available/svxlink-webui.conf \
  || fail "ProxyPreserveHost On missing"
ok "Apache preserves original Host header"

INSTALL_CODE="$(curl -sS -o /dev/null -w '%{http_code}' \
  -X POST "http://127.0.0.1:$API_PORT/api/system/update/install")"
[[ "$INSTALL_CODE" == "403" ]] \
  || fail "browser updater guard returned $INSTALL_CODE, expected 403"
ok "browser updater rejects request without CSRF/origin guard"

grep -q '^SVXLINK_WEBUI_UPDATE_ENABLED=true$' /etc/svxlink-webui/environment \
  || fail "update enable flag is not true"
ok "browser updater enabled by default"

printf '\nClean-install verification passed.\n'
