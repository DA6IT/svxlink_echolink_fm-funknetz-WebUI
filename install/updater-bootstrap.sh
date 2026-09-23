#!/usr/bin/env bash
set -Eeuo pipefail

if (( $# != 5 )); then
  echo "usage: updater-bootstrap.sh INSTALL_DIR DOCROOT WEBUI_USER WEBUI_GROUP UPDATE_BRANCH" >&2
  exit 64
fi

INSTALL_DIR="$1"
DOCROOT="$2"
WEBUI_USER="$3"
WEBUI_GROUP="$4"
UPDATE_BRANCH="$5"

UPDATER_USER="svxlink-webui-updater"
UPDATE_GROUP="svxlink-webui-update"
UPDATE_DATA="/var/lib/svxlink-webui-updater"
IPC_ROOT="/var/lib/svxlink-webui-update"
UPDATE_REMOTE="${SVXLINK_WEBUI_UPDATE_REMOTE:-https://git.da6it.de/hermes/svxlink-webui.git}"

log() { printf '>>> updater bootstrap: %s\n' "$*"; }
die() { printf 'ERROR: updater bootstrap: %s\n' "$*" >&2; exit 1; }

[[ ${EUID:-$(id -u)} -eq 0 ]] || die "must run as root"
command -v setfacl >/dev/null 2>&1 || die "acl/setfacl missing"
command -v git >/dev/null 2>&1 || die "git missing"

ensure_identity() {
  log "users and groups"
  getent group "$UPDATE_GROUP" >/dev/null || groupadd --system "$UPDATE_GROUP"

  if ! id "$UPDATER_USER" >/dev/null 2>&1; then
    useradd --system \
      --home-dir "$UPDATE_DATA" \
      --shell /usr/sbin/nologin \
      --user-group \
      "$UPDATER_USER"
  fi

  usermod -a -G "$UPDATE_GROUP" "$UPDATER_USER"
  usermod -a -G "$UPDATE_GROUP" "$WEBUI_USER"
}

ensure_git_checkout() {
  log "git checkout"

  if [[ ! -d "$INSTALL_DIR/.git" ]]; then
    if [[ -d "${SOURCE_DIR:-}/.git" ]]; then
      rsync -a "${SOURCE_DIR}/.git/" "$INSTALL_DIR/.git/"
    else
      git -C "$INSTALL_DIR" init
      git -C "$INSTALL_DIR" remote add origin "$UPDATE_REMOTE"
      git -C "$INSTALL_DIR" fetch --depth=1 origin "$UPDATE_BRANCH"
      git -C "$INSTALL_DIR" reset --hard FETCH_HEAD
    fi
  fi

  if git -C "$INSTALL_DIR" remote get-url origin >/dev/null 2>&1; then
    git -C "$INSTALL_DIR" remote set-url origin "$UPDATE_REMOTE"
  else
    git -C "$INSTALL_DIR" remote add origin "$UPDATE_REMOTE"
  fi

  chown -R root:"$WEBUI_GROUP" "$INSTALL_DIR"
  chmod -R u=rwX,g=rX,o= "$INSTALL_DIR"

  setfacl -R -m "u:$WEBUI_USER:rX,u:$UPDATER_USER:rwX" "$INSTALL_DIR"
  find "$INSTALL_DIR" -type d -exec setfacl -m \
    "d:u:$WEBUI_USER:r-x,d:u:$UPDATER_USER:rwx" {} +
}

ensure_ipc() {
  log "updater data and IPC"

  install -d -m 0750 -o "$UPDATER_USER" -g "$UPDATER_USER" "$UPDATE_DATA"
  install -d -m 0750 -o "$UPDATER_USER" -g "$UPDATER_USER" \
    "$UPDATE_DATA/jobs" "$UPDATE_DATA/venvs" "$UPDATE_DATA/backups"

  setfacl -m "u:$WEBUI_USER:--x" "$UPDATE_DATA"
  setfacl -R -m "u:$WEBUI_USER:rX" "$UPDATE_DATA/venvs"
  setfacl -m "d:u:$WEBUI_USER:r-X" "$UPDATE_DATA/venvs"

  install -d -m 2750 -o root -g "$UPDATE_GROUP" "$IPC_ROOT"
  install -d -m 2750 -o "$UPDATER_USER" -g "$UPDATE_GROUP" \
    "$IPC_ROOT/status" "$IPC_ROOT/control"
  install -d -m 3770 -o "$UPDATER_USER" -g "$UPDATE_GROUP" \
    "$IPC_ROOT/requests"

  setfacl -m "u:$WEBUI_USER:rx,u:$UPDATER_USER:rwx,m::rwx" "$IPC_ROOT"
  setfacl -m "u:$WEBUI_USER:rx,u:$UPDATER_USER:rwx,m::rwx" \
    "$IPC_ROOT/status" "$IPC_ROOT/control"
  setfacl -m "u:$WEBUI_USER:rwx,u:$UPDATER_USER:rwx,m::rwx" \
    "$IPC_ROOT/requests"

  setfacl -m "d:u:$WEBUI_USER:r-x,d:u:$UPDATER_USER:rwx,d:m::rwx" \
    "$IPC_ROOT/status" "$IPC_ROOT/control"
  setfacl -m "d:u:$WEBUI_USER:rwx,d:u:$UPDATER_USER:rwx,d:m::rwx" \
    "$IPC_ROOT/requests"
}

bootstrap_runtime() {
  local version revision runtime
  log "versioned initial runtime"

  version="$(tr -cd 'A-Za-z0-9._-' < "$INSTALL_DIR/VERSION" 2>/dev/null || true)"
  [[ -n "$version" ]] || version="bootstrap"

  revision="$(git -C "$INSTALL_DIR" rev-parse --verify HEAD 2>/dev/null || true)"
  [[ "$revision" =~ ^[0-9a-f]{40}$ ]] || revision="bootstrap"

  runtime="$UPDATE_DATA/venvs/${version}-${revision:0:12}"

  if [[ ! -x "$runtime/bin/python" ]]; then
    rm -rf "$runtime"
    python3 -m venv "$runtime"
    "$runtime/bin/pip" install --upgrade pip
    "$runtime/bin/pip" install -r "$INSTALL_DIR/backend/requirements.txt"
    "$runtime/bin/pip" install -r "$INSTALL_DIR/backend/requirements-test.txt"
  fi

  chown -R "$UPDATER_USER:$UPDATER_USER" "$runtime"

  ln -sfn "$runtime" "$INSTALL_DIR/.venv-current.new"
  mv -Tf "$INSTALL_DIR/.venv-current.new" "$INSTALL_DIR/.venv-current"
  chown -h root:"$WEBUI_GROUP" "$INSTALL_DIR/.venv-current"

  [[ -x "$INSTALL_DIR/.venv-current/bin/uvicorn" ]] \
    || die ".venv-current is not usable"
}

ensure_frontend_acl() {
  log "frontend ACLs"

  install -d -m 2770 -o root -g "$WEBUI_GROUP" "$DOCROOT"

  setfacl -R -m "u:$UPDATER_USER:rwX" "$DOCROOT"
  find "$DOCROOT" -type d -exec setfacl -m \
    "u:www-data:rx,u:$UPDATER_USER:rwx,d:u:www-data:rx,d:u:$UPDATER_USER:rwx" {} +
  find "$DOCROOT" -type f -exec setfacl -m \
    "u:www-data:r--,u:$UPDATER_USER:rw-" {} +

  runuser -u www-data -- test -r "$DOCROOT/index.html" \
    || die "www-data cannot read $DOCROOT/index.html"
}

install_worker_unit() {
  log "updater systemd unit"

  cat > /etc/systemd/system/svxlink-webui-updater.service <<UNIT
[Unit]
Description=SvxLink WebUI rootless updater
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$UPDATER_USER
Group=$UPDATER_USER
SupplementaryGroups=$UPDATE_GROUP
WorkingDirectory=$INSTALL_DIR/backend
EnvironmentFile=-/etc/svxlink-webui/environment
ExecStart=/usr/bin/python3 -m app.updater_worker
Restart=always
RestartSec=2
UMask=0027
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectHome=true
ProtectSystem=strict
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
ReadWritePaths=$INSTALL_DIR
ReadWritePaths=$DOCROOT
ReadWritePaths=$UPDATE_DATA
ReadWritePaths=$IPC_ROOT

[Install]
WantedBy=multi-user.target
UNIT
}

verify_bootstrap() {
  log "bootstrap verification"

  id "$UPDATER_USER" >/dev/null
  getent group "$UPDATE_GROUP" >/dev/null
  [[ -x "$INSTALL_DIR/.venv-current/bin/python" ]]
  [[ -d "$INSTALL_DIR/.git" ]]
  [[ -d "$IPC_ROOT/status" && -d "$IPC_ROOT/control" && -d "$IPC_ROOT/requests" ]]

  runuser -u "$WEBUI_USER" -- test ! -w "$INSTALL_DIR/.git"
  runuser -u "$UPDATER_USER" -- test -w "$INSTALL_DIR/.git"
  runuser -u "$UPDATER_USER" -- test -w "$DOCROOT"
  runuser -u www-data -- test -r "$DOCROOT/index.html"
}

ensure_identity
ensure_git_checkout
ensure_ipc
bootstrap_runtime
ensure_frontend_acl
install_worker_unit
verify_bootstrap

log "complete"
