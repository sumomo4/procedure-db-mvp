#!/usr/bin/env bash
set -Eeuo pipefail

BUNDLE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET_USER="${TARGET_USER:-${SUDO_USER:-user}}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
INSTALL_DIR="${INSTALL_DIR:-$TARGET_HOME/procedure-db-mvp}"
COMPOSE_FILES=(
  -f docker-compose.yml
  -f docker-compose.standard.yml
  -f docker-compose.standard.server.yml
)

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

[[ "$EUID" -eq 0 ]] || fail "Run with sudo: sudo bash verify_standard.sh"
[[ -d "$INSTALL_DIR" ]] || fail "Install directory was not found: $INSTALL_DIR"

cd "$INSTALL_DIR"

echo "[1/6] Waiting for container health"
deadline=$((SECONDS + 120))
while true; do
  db_health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' procedure-db-mvp-standard-db-1 2>/dev/null || true)"
  api_health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' procedure-db-mvp-standard-api-1 2>/dev/null || true)"
  web_state="$(docker inspect -f '{{.State.Status}}' procedure-db-mvp-standard-web-1 2>/dev/null || true)"
  if [[ "$db_health" == "healthy" && "$api_health" == "healthy" && "$web_state" == "running" ]]; then
    break
  fi
  (( SECONDS < deadline )) || fail "Containers did not become healthy within 120 seconds. db=$db_health api=$api_health web=$web_state"
  sleep 3
done
docker compose -p procedure-db-mvp "${COMPOSE_FILES[@]}" ps

echo "[2/6] Checking port exposure"
ss -ltn | grep -E ':(3000|8000|5432)[[:space:]]'
ss -ltn | grep -Eq '0\.0\.0\.0:3000|\[::\]:3000' || fail "Web port 3000 is not exposed."
ss -ltn | grep -Eq '127\.0\.0\.1:8000' || fail "API port 8000 is not localhost-only."
ss -ltn | grep -Eq '127\.0\.0\.1:5432' || fail "DB port 5432 is not localhost-only."

echo "[3/6] Checking health endpoints"
curl -fsS http://127.0.0.1:8000/api/v1/health
echo
curl -fsS http://127.0.0.1:8000/api/v1/health/db
echo
curl -fsS http://127.0.0.1:3000/api/v1/health
echo
curl -fsS http://127.0.0.1:3000/api/v1/health/db
echo

echo "[4/6] Checking empty initial data"
initial_result="$(docker compose -p procedure-db-mvp "${COMPOSE_FILES[@]}" exec -T standard-db \
  psql -U standard_user -d mvp_standard -Atc \
  "SELECT 'modules=' || count(*) FROM proc.modules; SELECT 'blueprints=' || count(*) FROM proc.blueprints;")"
echo "$initial_result"
grep -qx 'modules=0' <<<"$initial_result" || fail "Expected modules=0."
grep -qx 'blueprints=0' <<<"$initial_result" || fail "Expected blueprints=0."

echo "[5/6] Checking restart policies"
for container in \
  procedure-db-mvp-standard-web-1 \
  procedure-db-mvp-standard-api-1 \
  procedure-db-mvp-standard-db-1; do
  policy="$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$container")"
  echo "$container restart=$policy"
  [[ "$policy" == "unless-stopped" ]] || fail "Unexpected restart policy: $container=$policy"
done

echo "[6/6] Verification passed"
echo "WebUI: http://$(hostname -I | awk '{print $1}'):3000/"
