#!/usr/bin/env sh
set -eu

PREFIX="${SG_GATEWAY_PREFIX:-/opt/sg-gateway}"
DATA_DIR="${SG_GATEWAY_DATA_DIR:-/var/lib/sg-gateway}"
LOG_DIR="${SG_GATEWAY_LOG_DIR:-/var/log/sg-gateway}"
CONFIRM="${SG_GATEWAY_CONFIRM_UNINSTALL:-NO}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root, for example: curl ... | sudo SG_GATEWAY_CONFIRM_UNINSTALL=YES sh" >&2
  exit 1
fi

if [ "$CONFIRM" != "YES" ]; then
  echo "Refusing to uninstall without SG_GATEWAY_CONFIRM_UNINSTALL=YES" >&2
  exit 1
fi

if [ -d "$PREFIX" ]; then
  if [ -f "$PREFIX/docker-compose.yml" ]; then
    cd "$PREFIX"
    docker compose down --volumes --remove-orphans || true
  fi
fi

docker rm -f sg-gateway-panel sg-gateway-xray >/dev/null 2>&1 || true
docker volume rm sg-gateway_sg_gateway_data sg-gateway_sg_gateway_logs sg-gateway_sg_gateway_xray >/dev/null 2>&1 || true
docker volume rm sg_gateway_data sg_gateway_logs sg_gateway_xray >/dev/null 2>&1 || true

systemctl stop sg-hostd >/dev/null 2>&1 || true
systemctl disable sg-hostd >/dev/null 2>&1 || true
rm -f /etc/systemd/system/sg-hostd.service
systemctl daemon-reload >/dev/null 2>&1 || true

rm -rf "$PREFIX" "$DATA_DIR" "$LOG_DIR"

echo "SG-Gateway fully uninstalled."
