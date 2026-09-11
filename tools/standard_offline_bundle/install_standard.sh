#!/usr/bin/env bash
set -Eeuo pipefail

BUNDLE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILES=(
  -f docker-compose.yml
  -f docker-compose.standard.yml
  -f docker-compose.standard.server.yml
)

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

[[ "$EUID" -eq 0 ]] || fail "Run with sudo: sudo bash install_standard.sh"

TARGET_USER="${TARGET_USER:-${SUDO_USER:-user}}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
[[ -n "$TARGET_HOME" ]] || fail "Target user was not found: $TARGET_USER"

INSTALL_DIR="${INSTALL_DIR:-$TARGET_HOME/procedure-db-mvp}"
EXPECTED_INSTALL_DIR="$TARGET_HOME/procedure-db-mvp"
[[ "$INSTALL_DIR" == "$EXPECTED_INSTALL_DIR" ]] || fail "Unexpected INSTALL_DIR: $INSTALL_DIR"

source_archive=("$BUNDLE_DIR"/payload/procedure-db-mvp-standard-*.tar.gz)
image_archive=("$BUNDLE_DIR"/payload/procedure-db-standard-images-*.tar)
[[ ${#source_archive[@]} -eq 1 && -f "${source_archive[0]}" ]] || fail "Exactly one source archive is required."
[[ ${#image_archive[@]} -eq 1 && -f "${image_archive[0]}" ]] || fail "Exactly one image archive is required."
[[ -d "$BUNDLE_DIR/debs" ]] || fail "debs directory was not found."
[[ -f "$BUNDLE_DIR/SHA256SUMS" ]] || fail "SHA256SUMS was not found."
[[ -f "$BUNDLE_DIR/config/docker-compose.standard.server.yml" ]] || fail "Server compose override was not found."
[[ -f "$BUNDLE_DIR/DEPLOY_SHA" ]] || fail "DEPLOY_SHA was not found."

echo "[1/9] Checking server baseline"
source /etc/os-release
[[ "${VERSION_ID:-}" == "24.04" ]] || fail "Ubuntu 24.04 is required. Current VERSION_ID=${VERSION_ID:-unknown}"
[[ "$(dpkg --print-architecture)" == "amd64" ]] || fail "amd64 is required."
[[ ! -e "$INSTALL_DIR" ]] || fail "Install directory already exists: $INSTALL_DIR"

for port in 3000 8000 5432; do
  if ss -ltn | awk '{print $4}' | grep -Eq "(^|:)$port$"; then
    fail "Port $port is already in use."
  fi
done

echo "[2/9] Verifying bundle checksums"
(cd "$BUNDLE_DIR" && sha256sum -c SHA256SUMS)
(cd "$BUNDLE_DIR/debs" && sha256sum -c SHA256SUMS)

echo "[3/9] Installing Docker packages from local deb files"
DEBIAN_FRONTEND=noninteractive dpkg -i "$BUNDLE_DIR"/debs/*.deb
audit_result="$(dpkg --audit)"
[[ -z "$audit_result" ]] || fail "Package audit failed after local installation: $audit_result"
for package in docker.io docker-compose-v2 containerd runc; do
  package_state="$(dpkg-query -W -f='${db:Status-Abbrev}' "$package" 2>/dev/null || true)"
  [[ "$package_state" == "ii " ]] || fail "Required package is not installed: $package ($package_state)"
done
systemctl enable --now docker
usermod -aG docker "$TARGET_USER"

echo "[4/9] Loading Docker images"
docker load -i "${image_archive[0]}"
for image in \
  procedure-db-mvp-standard-web:latest \
  procedure-db-mvp-standard-api:latest \
  postgres:16-alpine; do
  docker image inspect "$image" >/dev/null || fail "Required image was not loaded: $image"
done

echo "[5/9] Extracting application source"
mkdir -p "$INSTALL_DIR"
tar -xzf "${source_archive[0]}" -C "$INSTALL_DIR"
cp "$BUNDLE_DIR/config/docker-compose.standard.server.yml" \
  "$INSTALL_DIR/docker-compose.standard.server.yml"
cp "$BUNDLE_DIR/DEPLOY_SHA" "$INSTALL_DIR/.deploy-version"
mkdir -p \
  "$INSTALL_DIR/storage/standard/access_exports" \
  "$INSTALL_DIR/storage/standard/module_images" \
  "$INSTALL_DIR/storage/standard/config" \
  "$INSTALL_DIR/logs/standard/db"
chown -R "$TARGET_USER:$TARGET_USER" "$INSTALL_DIR"

echo "[6/9] Validating compose configuration"
cd "$INSTALL_DIR"
docker compose -p procedure-db-mvp "${COMPOSE_FILES[@]}" config >/tmp/procedure-db-standard-compose.yml

echo "[7/9] Starting Standard without build or pull"
docker compose -p procedure-db-mvp "${COMPOSE_FILES[@]}" \
  up -d --no-build --pull never

echo "[8/9] Showing container state"
docker compose -p procedure-db-mvp "${COMPOSE_FILES[@]}" ps

echo "[9/9] Installation completed"
echo "Run verification: sudo bash $BUNDLE_DIR/verify_standard.sh"
echo "Reconnect SSH before using docker without sudo."
