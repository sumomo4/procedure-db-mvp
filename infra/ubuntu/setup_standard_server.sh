#!/usr/bin/env bash
set -euo pipefail

APP_ENV_NAME="procedure-db-standard"
SYSTEMD_SERVICE_NAME="${SYSTEMD_SERVICE_NAME:-standard-api}"
DB_NAME="${DB_NAME:-mvp_standard}"
DB_USER="${DB_USER:-standard_user}"
DB_PASSWORD="${DB_PASSWORD:-standard_password}"
API_PORT="${API_PORT:-8000}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo: sudo bash infra/ubuntu/setup_standard_server.sh" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKEND_DIR="${APP_ROOT}/apps/standard/backend"
FRONTEND_DIST="${APP_ROOT}/apps/standard/frontend/dist"
WEB_ROOT="/var/www/procedure-db-standard"
ENV_DIR="/etc/${APP_ENV_NAME}"
ENV_FILE="${ENV_DIR}/api.env"
SERVICE_USER="${SUDO_USER:-user}"

verify_static_asset() {
  local asset_path="$1"
  local expected_type="$2"
  local header

  header="$(curl -I -s "http://127.0.0.1${asset_path}" | tr -d '\r')"
  printf '%s\n' "${header}"

  if ! grep -qi "^Content-Type: ${expected_type}" <<<"${header}"; then
    echo "Static asset verification failed for ${asset_path}. Expected Content-Type ${expected_type}." >&2
    echo "Check ${WEB_ROOT} permissions. Directories must be 0755 and files must be 0644." >&2
    exit 1
  fi
}

wait_for_http() {
  local url="$1"
  local label="$2"
  local max_attempts="${3:-15}"
  local sleep_seconds="${4:-2}"
  local attempt

  for ((attempt = 1; attempt <= max_attempts; attempt++)); do
    if curl -fsS "${url}" >/dev/null; then
      return 0
    fi

    printf 'Waiting for %s (%s/%s)\n' "${label}" "${attempt}" "${max_attempts}"
    sleep "${sleep_seconds}"
  done

  echo "Timed out waiting for ${label}: ${url}" >&2
  systemctl status "${SYSTEMD_SERVICE_NAME}" --no-pager || true
  return 1
}

if [[ ! -d "${BACKEND_DIR}" ]]; then
  echo "Backend directory not found: ${BACKEND_DIR}" >&2
  exit 1
fi

if [[ ! -d "${FRONTEND_DIST}" ]]; then
  echo "Frontend dist directory not found: ${FRONTEND_DIST}" >&2
  echo "Build the frontend before running this script." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3-venv python3-pip nginx postgresql postgresql-contrib rsync curl

install -d -m 0755 "${ENV_DIR}"
cat > "${ENV_FILE}" <<ENV
APP_ENV=standard
SERVICE_NAME=standard-api
API_PREFIX=/api/v1
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_CONNECT_TIMEOUT_SECONDS=3
CORS_ALLOW_ORIGINS=http://192.168.10.5,http://localhost,http://127.0.0.1
ENV
chmod 0640 "${ENV_FILE}"
chown root:"${SERVICE_USER}" "${ENV_FILE}"

sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
  ELSE
    ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';
  END IF;
END
\$\$;
SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d "${DB_NAME}" <<SQL
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER SCHEMA public OWNER TO ${DB_USER};
SQL

sudo -u "${SERVICE_USER}" python3 -m venv "${BACKEND_DIR}/.venv"
sudo -u "${SERVICE_USER}" "${BACKEND_DIR}/.venv/bin/python" -m pip install --upgrade pip
sudo -u "${SERVICE_USER}" "${BACKEND_DIR}/.venv/bin/python" -m pip install -r "${BACKEND_DIR}/requirements.txt"

sudo -u postgres psql -v ON_ERROR_STOP=1 -d "${DB_NAME}" -f "${APP_ROOT}/apps/standard/db/init/001_standard_schema.sql"

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

install -d -m 0755 "${WEB_ROOT}"
rsync -a --delete "${FRONTEND_DIST}/" "${WEB_ROOT}/"
find "${WEB_ROOT}" -type d -exec chmod 0755 {} +
find "${WEB_ROOT}" -type f -exec chmod 0644 {} +

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

systemctl daemon-reload
systemctl enable "${SYSTEMD_SERVICE_NAME}"
systemctl restart "${SYSTEMD_SERVICE_NAME}"
nginx -t
systemctl reload nginx

wait_for_http "http://127.0.0.1:${API_PORT}/api/v1/health" "standard-api health"
curl -fsS "http://127.0.0.1:${API_PORT}/api/v1/health"
echo
wait_for_http "http://127.0.0.1:${API_PORT}/api/v1/health/db" "standard-api database health"
curl -fsS "http://127.0.0.1:${API_PORT}/api/v1/health/db"
echo
wait_for_http "http://127.0.0.1/api/v1/health" "nginx API proxy health"
curl -fsS "http://127.0.0.1/api/v1/health"
echo

INDEX_JS_PATH="$(grep -o '/assets/[^"]*\.js' "${WEB_ROOT}/index.html" | head -n 1)"
INDEX_CSS_PATH="$(grep -o '/assets/[^"]*\.css' "${WEB_ROOT}/index.html" | head -n 1)"

if [[ -z "${INDEX_JS_PATH}" || -z "${INDEX_CSS_PATH}" ]]; then
  echo "Could not resolve asset paths from ${WEB_ROOT}/index.html" >&2
  exit 1
fi

verify_static_asset "${INDEX_JS_PATH}" "application/javascript"
echo "---"
verify_static_asset "${INDEX_CSS_PATH}" "text/css"

echo "Deployment completed: http://192.168.10.5/"
