#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY="s-gor/sg-gateway"
BRANCH="${SG_GATEWAY_GITHUB_BRANCH:-${SG_GATEWAY_UPDATE_BRANCH:-dev-02205}}"
ARCHIVE_URL="https://github.com/${REPOSITORY}/archive/refs/heads/${BRANCH}.tar.gz"
TEMP_DIR=""
BOOTSTRAP_LOG="/tmp/sg-gateway-bootstrap-$$.log"

fail() {
  printf '[SG-Gateway] ERROR: %s\n' "$*" >&2
  if [[ -s "$BOOTSTRAP_LOG" ]]; then
    printf '[SG-Gateway] Bootstrap details:\n' >&2
    tail -n 30 "$BOOTSTRAP_LOG" >&2 || true
  fi
  exit 1
}

cleanup() {
  if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
    rm -rf "$TEMP_DIR"
  fi
  rm -f "$BOOTSTRAP_LOG"
}
trap cleanup EXIT INT TERM

[[ "$(id -u)" -eq 0 ]] || fail "run this installer through sudo"

# SG_GATEWAY_02112_INSTALL_UPDATE_SPLIT
# The clean-install command must never mutate an existing SG-Gateway.
if [[ -f /opt/sg-gateway/VERSION && -f /etc/sg-gateway/runtime.env && -f /etc/sg-gateway/sg-gateway.env ]]; then
  installed_version="$(tr -d '\r\n' < /opt/sg-gateway/VERSION 2>/dev/null || true)"
  printf '[SG-Gateway] SG-Gateway %s is already installed.\n' "${installed_version:-unknown}"
  printf '[SG-Gateway] Clean Install is blocked on an existing server.\n'
  printf '[SG-Gateway] Use the dedicated Update command.\n'
  printf '[SG-Gateway] Updater: /opt/sg-gateway/deploy/update-from-github.sh\n'
  exit 2
fi

: > "$BOOTSTRAP_LOG"
chmod 0600 "$BOOTSTRAP_LOG"

missing_packages=()
command -v curl >/dev/null 2>&1 || missing_packages+=(curl)
command -v tar >/dev/null 2>&1 || missing_packages+=(tar)
command -v gzip >/dev/null 2>&1 || missing_packages+=(gzip)
[[ -s /etc/ssl/certs/ca-certificates.crt ]] || missing_packages+=(ca-certificates)

printf '[SG-Gateway] Подготовка установщика...\n'

if (( ${#missing_packages[@]} > 0 )); then
  command -v apt-get >/dev/null 2>&1 || fail "apt-get is required to install bootstrap dependencies"
  apt-get -o Dpkg::Use-Pty=0 update -qq >>"$BOOTSTRAP_LOG" 2>&1 \
    || fail "apt update failed"
  env DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a \
    apt-get -o Dpkg::Use-Pty=0 install -y -qq --no-install-recommends "${missing_packages[@]}" \
    >>"$BOOTSTRAP_LOG" 2>&1 || fail "bootstrap package installation failed"
fi

for command in curl tar gzip; do
  command -v "$command" >/dev/null 2>&1 || fail "missing command after bootstrap: $command"
done

TEMP_DIR="$(mktemp -d /tmp/sg-gateway-github-install.XXXXXX)"
ARCHIVE="$TEMP_DIR/sg-gateway-source.tar.gz"
SOURCE_DIR="$TEMP_DIR/source"
mkdir -p "$SOURCE_DIR"

curl -fsSL --retry 6 --retry-all-errors --retry-delay 3 --connect-timeout 20 \
  "$ARCHIVE_URL" -o "$ARCHIVE" 2>>"$BOOTSTRAP_LOG" \
  || fail "cannot download GitHub branch $BRANCH"

gzip -t "$ARCHIVE" >>"$BOOTSTRAP_LOG" 2>&1 || fail "downloaded archive is invalid"
tar -xzf "$ARCHIVE" -C "$SOURCE_DIR" --strip-components=1 \
  >>"$BOOTSTRAP_LOG" 2>&1 || fail "cannot unpack downloaded source"

[[ -f "$SOURCE_DIR/install.sh" ]] || fail "install.sh is missing from the GitHub archive"
[[ -f "$SOURCE_DIR/VERSION" ]] || fail "VERSION is missing from the GitHub archive"
[[ -f "$SOURCE_DIR/requirements.txt" ]] || fail "requirements.txt is missing from the GitHub archive"
[[ -d "$SOURCE_DIR/app" ]] || fail "application source is missing from the GitHub archive"

printf '[SG-Gateway] Исходник: %s · версия %s\n' \
  "$BRANCH" "$(tr -d '\r\n' < "$SOURCE_DIR/VERSION")"

SG_GATEWAY_SOURCE_DIR="$SOURCE_DIR" bash "$SOURCE_DIR/install.sh"
