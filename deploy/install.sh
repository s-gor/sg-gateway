#!/usr/bin/env sh
set -eu

PREFIX="${SG_GATEWAY_PREFIX:-/opt/sg-gateway}"
DATA_DIR="${SG_GATEWAY_DATA_DIR:-/var/lib/sg-gateway}"
LOG_DIR="${SG_GATEWAY_LOG_DIR:-/var/log/sg-gateway}"
DRY_RUN="${SG_GATEWAY_DRY_RUN:-1}"

run() {
  if [ "$DRY_RUN" = "1" ]; then
    printf '[dry-run] %s\n' "$*"
  else
    "$@"
  fi
}

copy_file() {
  src="$1"
  dst="$2"
  if [ "$DRY_RUN" = "1" ]; then
    printf '[dry-run] install -m 0644 %s %s\n' "$src" "$dst"
  else
    install -m 0644 "$src" "$dst"
  fi
}

echo "SG-Gateway installer"
echo "PREFIX=$PREFIX"
echo "DATA_DIR=$DATA_DIR"
echo "LOG_DIR=$LOG_DIR"
echo "DRY_RUN=$DRY_RUN"

run mkdir -p "$PREFIX" "$DATA_DIR" "$LOG_DIR"
run mkdir -p "$PREFIX/deploy" "$PREFIX/hostd" "$PREFIX/docker"

copy_file docker-compose.yml "$PREFIX/docker-compose.yml"
copy_file docker-compose.dev.yml "$PREFIX/docker-compose.dev.yml"
copy_file hostd/systemd/sg-hostd.service "$PREFIX/deploy/sg-hostd.service"

cat <<'NEXT'

Next manual steps:
  1. Review copied files.
  2. Install sg-hostd service file into /etc/systemd/system/.
  3. Start sg-hostd on 127.0.0.1:8090.
  4. Run docker compose up -d panel.

To execute for real:
  SG_GATEWAY_DRY_RUN=0 ./deploy/install.sh
NEXT