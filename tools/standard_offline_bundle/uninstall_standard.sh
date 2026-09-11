#!/usr/bin/env bash
set -Eeuo pipefail

PURGE_DATA=false
REMOVE_DOCKER=false
for arg in "$@"; do
  case "$arg" in
    --purge-data) PURGE_DATA=true ;;
    --remove-docker) REMOVE_DOCKER=true ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

[[ "$EUID" -eq 0 ]] || fail "Run with sudo."
TARGET_USER="${TARGET_USER:-${SUDO_USER:-user}}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
INSTALL_DIR="${INSTALL_DIR:-$TARGET_HOME/procedure-db-mvp}"
[[ "$INSTALL_DIR" == "$TARGET_HOME/procedure-db-mvp" ]] || fail "Unexpected INSTALL_DIR: $INSTALL_DIR"

if [[ -d "$INSTALL_DIR" ]]; then
  cd "$INSTALL_DIR"
  compose=(
    docker compose -p procedure-db-mvp
    -f docker-compose.yml
    -f docker-compose.standard.yml
    -f docker-compose.standard.server.yml
  )
  if $PURGE_DATA; then
    "${compose[@]}" down -v --rmi all --remove-orphans
    cd "$TARGET_HOME"
    rm -rf -- "$INSTALL_DIR"
    echo "Application, DB volume, images, and install directory were removed."
  else
    "${compose[@]}" down
    echo "Containers were removed. Data and install directory were retained."
  fi
fi

if $REMOVE_DOCKER; then
  systemctl disable --now docker.service docker.socket containerd.service 2>/dev/null || true
  gpasswd -d "$TARGET_USER" docker 2>/dev/null || true
  DEBIAN_FRONTEND=noninteractive apt-get purge -y \
    docker.io docker-compose-v2 containerd runc bridge-utils \
    dns-root-data dnsmasq-base pigz ubuntu-fan
  rm -rf -- /var/lib/docker /var/lib/containerd /etc/docker
  if getent group docker >/dev/null 2>&1; then
    members="$(getent group docker | cut -d: -f4)"
    [[ -n "$members" ]] || groupdel docker
  fi
  ip link delete docker0 2>/dev/null || true
  echo "Docker packages and state were removed."
fi

echo "Uninstall operation completed."
