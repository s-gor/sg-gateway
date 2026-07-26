#!/usr/bin/env bash
set -Eeuo pipefail

PREFIX="/opt/sg-gateway"
CONFIG_DIR="/etc/sg-gateway"
DATA_DIR="/var/lib/sg-gateway"
LOG_FILE="/var/log/sg-gateway-update.log"
BRANCH="${SG_GATEWAY_BRANCH:-main}"

GREEN=$'\033[1;32m'
RED=$'\033[1;31m'
RESET=$'\033[0m'

cd /

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run through sudo."
    exit 1
fi

if [[ ! -d "$PREFIX/.git" ]] || [[ ! -f "$CONFIG_DIR/sg-gateway.env" ]]; then
    echo "Native SG-Gateway installation was not found."
    exit 1
fi

: > "$LOG_FILE"
chmod 600 "$LOG_FILE"

run_step() {
    local label="$1"
    shift

    printf "%s... " "$label"
    if "$@" >> "$LOG_FILE" 2>&1; then
        printf "%sOK%s\n" "$GREEN" "$RESET"
    else
        printf "%sERROR%s\n" "$RED" "$RESET"
        tail -n 50 "$LOG_FILE" || true
        exit 1
    fi
}

backup_database() {
    install -d -m 0750 /var/backups/sg-gateway
    if [[ -f "$DATA_DIR/sg-gateway.sqlite" ]]; then
        cp -a \
            "$DATA_DIR/sg-gateway.sqlite" \
            "/var/backups/sg-gateway/sg-gateway-$(date +%Y%m%d-%H%M%S).sqlite"
    fi
}

update_code() {
    git -C "$PREFIX" fetch origin "$BRANCH"
    git -C "$PREFIX" checkout "$BRANCH"
    git -C "$PREFIX" reset --hard "origin/$BRANCH"
}

update_dependencies() {
    "$PREFIX/.venv/bin/python" -m pip install -r "$PREFIX/requirements.txt"
    "$PREFIX/.venv/bin/python" -m pip install -r "$PREFIX/hostd/requirements.txt"
}

restart_services() {
    systemctl restart sg-hostd.service
    systemctl restart sg-gateway.service
    systemctl is-active --quiet sg-hostd.service
    systemctl is-active --quiet sg-gateway.service
}

run_step "Резервная копия базы" backup_database
run_step "Обновление кода" update_code
run_step "Обновление Python-зависимостей" update_dependencies
run_step "Перезапуск systemd-служб" restart_services

echo "SG-Gateway updated successfully."
