#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run with sudo.'; exit 1; }
command -v python3 >/dev/null; command -v npm >/dev/null; command -v apache2ctl >/dev/null
if ss -lnt | grep -q ':12345 '; then echo 'Port 12345 is already in use; refusing to alter it.'; exit 1; fi
id -u svxlink-webui >/dev/null 2>&1 || useradd --system --home /opt/svxlink-webui --shell /usr/sbin/nologin svxlink-webui
getent group svxlink-state-reader >/dev/null || groupadd --system svxlink-state-reader
id -u svxlink-state-collector >/dev/null 2>&1 || useradd --system --home /nonexistent --shell /usr/sbin/nologin --gid svxlink-webui svxlink-state-collector
install -d -m 0750 -o svxlink-webui -g svxlink-webui /opt/svxlink-webui /etc/svxlink-webui /var/lib/svxlink-webui/backups /var/www/new.shart
install -m 0644 .env.example /etc/svxlink-webui/environment
cp -a backend /opt/svxlink-webui/
python3 -m venv /opt/svxlink-webui/.venv
/opt/svxlink-webui/.venv/bin/pip install -r backend/requirements.txt
(cd frontend && npm ci && npm run build)
cp -a frontend/dist/. /var/www/new.shart/
chown -R svxlink-webui:svxlink-webui /opt/svxlink-webui /var/lib/svxlink-webui
install -m 0644 deploy/systemd/svxlink-webui.service /etc/systemd/system/
install -m 0644 deploy/systemd/svxlink-state-collector.service /etc/systemd/system/
install -m 0644 deploy/systemd/svxlink-state-pty-permissions.service /etc/systemd/system/
install -m 0644 deploy/apache/svxlink-webui.conf /etc/apache2/sites-available/
a2enmod proxy proxy_http proxy_wstunnel headers rewrite
a2ensite svxlink-webui
systemctl daemon-reload
systemctl enable svxlink-state-pty-permissions.service
apache2ctl configtest
systemctl enable --now svxlink-webui
systemctl reload apache2
echo 'Installed. Browse http://HOST:12345'
