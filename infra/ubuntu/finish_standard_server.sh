#!/usr/bin/env bash
set -euo pipefail

APP_ENV_NAME="procedure-db-standard"
SYSTEMD_SERVICE_NAME="${SYSTEMD_SERVICE_NAME:-standard-api}"
API_PORT="${API_PORT:-8000}"
APP_ROOT="${APP_ROOT:-/home/user/procedure-db-mvp}"
BACKEND_DIR="${APP_ROOT}/apps/standard/backend"
FRONTEND_DIST="${APP_ROOT}/apps/standard/frontend/dist"
WEB_ROOT="/var/www/procedure-db-standard"
ENV_DIR="/etc/${APP_ENV_NAME}"
ENV_FILE="${ENV_DIR}/api.env"
SERVICE_USER="${SUDO_USER:-user}"

log() {
  printf '\n==> %s\n' "$1"
}

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo: sudo bash infra/ubuntu/finish_standard_server.sh" >&2
  exit 1
fi

log "Checking deployed files"
test -f "${BACKEND_DIR}/requirements.txt"
test -f "${BACKEND_DIR}/app/main.py"
test -d "${FRONTEND_DIST}"

if [[ ! -f "${ENV_FILE}" ]]; then
  log "Creating API environment file"
  install -d -m 0755 "${ENV_DIR}"
  cat > "${ENV_FILE}" <<ENV
APP_ENV=standard
SERVICE_NAME=standard-api
API_PREFIX=/api/v1
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=mvp_standard
DB_USER=standard_user
DB_PASSWORD=standard_password
DB_CONNECT_TIMEOUT_SECONDS=3
CORS_ALLOW_ORIGINS=http://192.168.10.5,http://localhost,http://127.0.0.1
ENV
  chmod 0640 "${ENV_FILE}"
  chown root:"${SERVICE_USER}" "${ENV_FILE}"
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

log "Installing API dependencies"
sudo -u "${SERVICE_USER}" python3 -m venv "${BACKEND_DIR}/.venv"
sudo -u "${SERVICE_USER}" "${BACKEND_DIR}/.venv/bin/python" -m pip install -r "${BACKEND_DIR}/requirements.txt"

log "Applying standard DB schema"
PGPASSWORD="${DB_PASSWORD}" psql \
  -h "${DB_HOST}" \
  -p "${DB_PORT}" \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  -v ON_ERROR_STOP=1 \
  -f "${APP_ROOT}/apps/standard/db/init/001_standard_schema.sql"

log "Writing systemd service"
cat > "/etc/systemd/system/${SYSTEMD_SERVICE_NAME}.service" <<SERVICE
[Unit]
Description=Procedure DB Standard API
After=network.target postgresql.service

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${BACKEND_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${BACKEND_DIR}/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

log "Publishing WebUI"
install -d -m 0755 "${WEB_ROOT}"
rsync -a --delete "${FRONTEND_DIST}/" "${WEB_ROOT}/"

log "Writing Nginx site"
cat > /etc/nginx/sites-available/procedure-db-standard <<NGINX
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    root ${WEB_ROOT};
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:${API_PORT}/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
NGINX

rm -f /etc/nginx/sites-enabled/default
ln -sfn /etc/nginx/sites-available/procedure-db-standard /etc/nginx/sites-enabled/procedure-db-standard

log "Restarting services"
systemctl daemon-reload
systemctl enable "${SYSTEMD_SERVICE_NAME}"
systemctl restart "${SYSTEMD_SERVICE_NAME}"
nginx -t
systemctl reload nginx

log "Verifying local endpoints"
curl -fsS "http://127.0.0.1:${API_PORT}/api/v1/health"
echo
curl -fsS "http://127.0.0.1:${API_PORT}/api/v1/health/db"
echo
curl -fsS "http://127.0.0.1/api/v1/health"
echo

log "Deployment completed"
echo "http://192.168.10.5/"
