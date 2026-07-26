#!/usr/bin/env bash
set -Eeuo pipefail

PREFIX="/opt/sg-gateway"
CONFIG_DIR="/etc/sg-gateway"
DATA_DIR="/var/lib/sg-gateway"
LOG_DIR="/var/log/sg-gateway"
UNINSTALL_LOG="/var/log/sg-gateway-uninstall.log"

GREEN=$'\033[1;32m'
RED=$'\033[1;31m'
YELLOW=$'\033[1;33m'
CYAN=$'\033[1;36m'
RESET=$'\033[0m'

TOTAL_STAGES=5
PANEL_PORT="63443"
XRAY_INSTALLED_BY_SG="0"
AWG_INSTALLED_BY_SG="0"

cd /

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run this uninstaller through sudo."
    exit 1
fi

if [[ -f "$CONFIG_DIR/runtime.env" ]]; then
    # The file is generated only by SG-Gateway and contains simple values.
    # shellcheck disable=SC1090
    source "$CONFIG_DIR/runtime.env"
    PANEL_PORT="${SG_GATEWAY_PANEL_PORT:-63443}"
    XRAY_INSTALLED_BY_SG="${SG_GATEWAY_XRAY_INSTALLED_BY_SG:-0}"
    AWG_INSTALLED_BY_SG="${SG_GATEWAY_AWG_INSTALLED_BY_SG:-0}"
fi

printf "\n%sПолное удаление SG-Gateway%s\n" "$CYAN" "$RESET"
printf "Будут удалены приложение, конфигурация, база данных и службы.\n"
read -r -p "Введите YES для подтверждения: " CONFIRM < /dev/tty

if [[ "$CONFIRM" != "YES" ]]; then
    echo "Удаление отменено."
    exit 0
fi

: > "$UNINSTALL_LOG"
chmod 600 "$UNINSTALL_LOG"

spinner_loop() {
    local pid="$1"
    local label="$2"
    local frames=('|' '/' '-' '\')
    local index=0

    while kill -0 "$pid" 2>/dev/null; do
        printf "\r\033[K%s[%s]%s %s" \
            "$GREEN" "${frames[$index]}" "$RESET" "$label"
        index=$(( (index + 1) % 4 ))
        sleep 0.12
    done
}

run_stage() {
    local stage="$1"
    local label="$2"
    local function_name="$3"
    local started=$SECONDS

    "$function_name" >> "$UNINSTALL_LOG" 2>&1 &
    local pid=$!
    spinner_loop "$pid" "Этап ${stage}/${TOTAL_STAGES} · ${label}"

    set +e
    wait "$pid"
    local rc=$?
    set -e

    local elapsed=$((SECONDS - started))
    if [[ "$rc" -ne 0 ]]; then
        printf "\r\033[K%s[ОШИБКА]%s Этап %s/%s · %s\n" \
            "$RED" "$RESET" "$stage" "$TOTAL_STAGES" "$label"
        tail -n 60 "$UNINSTALL_LOG" || true
        exit "$rc"
    fi

    printf "\r\033[K%s[OK]%s Этап %s/%s · %s (%s сек.)\n" \
        "$GREEN" "$RESET" "$stage" "$TOTAL_STAGES" "$label" "$elapsed"
}

stop_services() {
    systemctl disable --now sg-gateway.service >/dev/null 2>&1 || true
    systemctl disable --now sg-hostd.service >/dev/null 2>&1 || true
    rm -f \
        /etc/systemd/system/sg-gateway.service \
        /etc/systemd/system/sg-hostd.service
    systemctl daemon-reload
    systemctl reset-failed >/dev/null 2>&1 || true
}

cleanup_legacy_docker() {
    if command -v docker >/dev/null 2>&1; then
        if [[ -f "$PREFIX/docker-compose.yml" ]] \
            && docker compose version >/dev/null 2>&1; then
            (
                cd "$PREFIX"
                docker compose down --volumes --remove-orphans || true
            )
        fi

        docker rm -f sg-gateway-panel sg-gateway-xray \
            >/dev/null 2>&1 || true

        docker volume rm \
            sg-gateway_sg_gateway_data \
            sg-gateway_sg_gateway_logs \
            sg-gateway_sg_gateway_xray \
            sg_gateway_data \
            sg_gateway_logs \
            sg_gateway_xray \
            >/dev/null 2>&1 || true
    fi
}

remove_application() {
    cd /
    rm -rf "$PREFIX" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"

    if id sg-gateway >/dev/null 2>&1; then
        userdel sg-gateway >/dev/null 2>&1 || true
    fi

    if getent group sg-gateway >/dev/null 2>&1; then
        groupdel sg-gateway >/dev/null 2>&1 || true
    fi
}

remove_engine_runtimes() {
    if [[ "$XRAY_INSTALLED_BY_SG" == "1" ]]; then
        systemctl disable --now xray.service >/dev/null 2>&1 || true
        rm -f /etc/systemd/system/xray.service
        rm -rf /usr/local/etc/xray /usr/local/share/xray /var/log/xray
        rm -f /usr/local/bin/xray
        systemctl daemon-reload
    fi

    if [[ "$AWG_INSTALLED_BY_SG" == "1" ]]; then
        apt-get -o Dpkg::Use-Pty=0 purge -y \
            amneziawg amneziawg-dkms amneziawg-tools \
            >/dev/null 2>&1 || true
        apt-get -o Dpkg::Use-Pty=0 autoremove -y \
            >/dev/null 2>&1 || true
    fi
}

cleanup_network() {
    if command -v ufw >/dev/null 2>&1 \
        && ufw status 2>/dev/null | grep -q '^Status: active'; then
        ufw --force delete allow "${PANEL_PORT}/tcp" \
            >/dev/null 2>&1 || true
    fi
}

run_stage 1 "Остановка systemd-служб" stop_services
run_stage 2 "Удаление старых Docker-остатков" cleanup_legacy_docker
run_stage 3 "Удаление приложения и данных" remove_application
run_stage 4 "Удаление установленных runtime" remove_engine_runtimes
run_stage 5 "Очистка сетевых правил" cleanup_network

printf "\n%sSG-Gateway полностью удалён.%s\n" "$GREEN" "$RESET"
printf "Журнал удаления: %s\n" "$UNINSTALL_LOG"
