#!/usr/bin/env bash
set -Eeuo pipefail

BRANCH="${SG_GATEWAY_GITHUB_BRANCH:-dev-02202-dual-awg}"
REPOSITORY="s-gor/sg-gateway"
PREFIX="/opt/sg-gateway"
TEMP_DIR=""
LOG="/var/log/sg-gateway-update-02202-dual-awg.log"

cleanup() {
  [[ -z "$TEMP_DIR" || ! -d "$TEMP_DIR" ]] || rm -rf "$TEMP_DIR"
}
trap cleanup EXIT INT TERM

fail() {
  printf '[SG-Gateway 022.02] ERROR: %s\n' "$*" >&2
  printf '[SG-Gateway 022.02] Log: %s\n' "$LOG" >&2
  exit 1
}

[[ "$(id -u)" -eq 0 ]] || fail "run through sudo"
[[ -f "$PREFIX/VERSION" ]] || fail "SG-Gateway is not installed"

: > "$LOG"
chmod 0600 "$LOG"

TEMP_DIR="$(mktemp -d /tmp/sg-gateway-02202-update.XXXXXX)"
SOURCE="$TEMP_DIR/source"
ARCHIVE="$TEMP_DIR/source.tar.gz"
mkdir -p "$SOURCE"

printf '[SG-Gateway 022.02] [1/6] Download source %s...\n' "$BRANCH"
curl -fsSL --retry 6 --retry-all-errors --retry-delay 3 \
  "https://github.com/${REPOSITORY}/archive/refs/heads/${BRANCH}.tar.gz" \
  -o "$ARCHIVE" >>"$LOG" 2>&1 || fail "source download failed"
tar -xzf "$ARCHIVE" -C "$SOURCE" --strip-components=1 >>"$LOG" 2>&1 \
  || fail "source unpack failed"
[[ "$(tr -d '\r\n' < "$SOURCE/VERSION")" == "0.1.0-022.02" ]] \
  || fail "unexpected source VERSION"
printf '[SG-Gateway 022.02] [OK]\n'

printf '[SG-Gateway 022.02] [2/6] Safe source update...\n'
SG_GATEWAY_GITHUB_BRANCH="$BRANCH" \
  bash "$SOURCE/deploy/update-from-github.sh" >>"$LOG" 2>&1 \
  || fail "base safe updater failed"
printf '[SG-Gateway 022.02] [OK]\n'

printf '[SG-Gateway 022.02] [3/6] Install pinned AWG3-compatible runtime...\n'
systemctl stop sg-gateway-awg3.service sg-gateway-awg.service >/dev/null 2>&1 || true
modprobe -r amneziawg >/dev/null 2>&1 || true
# shellcheck source=/dev/null
source "$PREFIX/install.sh"
UPDATE_MODE=1
if ! amneziawg_runtime_ready; then
  install_amneziawg_from_vendor >>"$LOG" 2>&1 \
    || fail "AWG3 runtime installation failed"
fi
awg --version >>"$LOG" 2>&1
modinfo amneziawg >>"$LOG" 2>&1
printf '[SG-Gateway 022.02] [OK]\n'

printf '[SG-Gateway 022.02] [4/6] Provision persistent AWG services/network...\n'
install -m 0644 "$PREFIX/deploy/sg-gateway-awg.service" \
  /etc/systemd/system/sg-gateway-awg.service
install -m 0644 "$PREFIX/deploy/sg-gateway-awg3.service" \
  /etc/systemd/system/sg-gateway-awg3.service
cat > /etc/sysctl.d/99-sg-gateway-forwarding.conf <<'EOF'
net.ipv4.ip_forward=1
net.ipv6.conf.all.forwarding=1
EOF
sysctl --system >>"$LOG" 2>&1
if ufw status 2>/dev/null | grep -q '^Status: active'; then
  ufw allow 585/udp >>"$LOG" 2>&1
  ufw allow 586/udp >>"$LOG" 2>&1
fi
systemctl daemon-reload
systemctl enable sg-gateway-awg.service sg-gateway-awg3.service >/dev/null
printf '[SG-Gateway 022.02] [OK]\n'

printf '[SG-Gateway 022.02] [5/6] Apply AWG2 + AWG3 clients...\n'
systemctl restart sg-hostd.service sg-gateway.service
sleep 2
response="$(
  curl -fsS --max-time 300 -X POST \
    http://127.0.0.1:8090/commands/clients.apply
)" || fail "clients.apply request failed"
printf '%s\n' "$response" >>"$LOG"
python3 -c '
import json,sys
value=json.load(sys.stdin)
if value.get("status") != "ok":
    raise SystemExit(value.get("message") or "clients.apply failed")
print(value.get("message") or "clients.apply: OK")
' <<<"$response" || fail "AWG2/AWG3 apply failed"
printf '[SG-Gateway 022.02] [OK]\n'

printf '[SG-Gateway 022.02] [6/6] Verify dual runtime...\n'
grep -Eq '^ListenPort[[:space:]]*=[[:space:]]*585[[:space:]]*$' \
  /etc/amnezia/amneziawg/awg0.conf || fail "AWG2 is not UDP 585"
grep -Eq '^ListenPort[[:space:]]*=[[:space:]]*586[[:space:]]*$' \
  /etc/amnezia/amneziawg/awg3.conf || fail "AWG3 is not UDP 586"
systemctl is-active --quiet sg-gateway-awg.service || fail "AWG2 service inactive"
systemctl is-active --quiet sg-gateway-awg3.service || fail "AWG3 service inactive"
ss -H -lun | grep -Eq '(:|\])585[[:space:]]' || fail "UDP 585 is not listening"
ss -H -lun | grep -Eq '(:|\])586[[:space:]]' || fail "UDP 586 is not listening"
printf '[SG-Gateway 022.02] [OK]\n'

printf '\n[SG-Gateway 022.02] SUCCESS\n'
printf 'AWG2: awg0 / UDP 585\n'
printf 'AWG3: awg3 / UDP 586\n'
printf 'Version: %s\n' "$(tr -d '\r\n' < "$PREFIX/VERSION")"
printf 'Log: %s\n' "$LOG"
