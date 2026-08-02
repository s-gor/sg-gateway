#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY="s-gor/sg-gateway"
BRANCH="${SG_GATEWAY_GITHUB_BRANCH:-main}"
ARCHIVE_URL="https://github.com/${REPOSITORY}/archive/refs/heads/${BRANCH}.tar.gz"
TEMP_DIR=""

fail() {
  printf '[SG-Gateway] ERROR: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
    rm -rf "$TEMP_DIR"
  fi
}
trap cleanup EXIT INT TERM

[[ "$(id -u)" -eq 0 ]] || fail "run this installer through sudo"

bootstrap_port_preflight() {
  [[ ! -f /opt/sg-gateway/VERSION ]] || return 0
  local specs=(tcp:80 tcp:63443 tcp:443 tcp:2099 tcp:8444 tcp:8445 tcp:9443 tcp:8090 tcp:18080 udp:585 udp:8446 udp:10443)
  local item protocol port hex file local_address state found failures=0
  printf '[SG-Gateway] Early clean-server port check before bootstrap changes:\n'
  for item in "${specs[@]}"; do
    IFS=: read -r protocol port <<< "$item"
    printf -v hex '%04X' "$port"
    found=0
    if [[ "$protocol" == "tcp" ]]; then
      files=(/proc/net/tcp /proc/net/tcp6)
    else
      files=(/proc/net/udp /proc/net/udp6)
    fi
    for file in "${files[@]}"; do
      [[ -r "$file" ]] || continue
      while read -r _ local_address _ state _; do
        [[ "${local_address##*:}" == "$hex" ]] || continue
        [[ "$protocol" != "tcp" || "$state" == "0A" ]] || continue
        found=1
        break
      done < <(tail -n +2 "$file")
      (( found == 0 )) || break
    done
    if (( found == 1 )); then
      printf '  [BUSY] %s/%s\n' "$port" "${protocol^^}"
      failures=$((failures + 1))
    else
      printf '  [OK]   %s/%s\n' "$port" "${protocol^^}"
    fi
  done
  (( failures == 0 )) || fail "required port is occupied; server was not changed"
}

bootstrap_port_preflight

missing_packages=()
command -v curl >/dev/null 2>&1 || missing_packages+=(curl)
command -v tar >/dev/null 2>&1 || missing_packages+=(tar)
command -v gzip >/dev/null 2>&1 || missing_packages+=(gzip)
command -v python3 >/dev/null 2>&1 || missing_packages+=(python3)
[[ -s /etc/ssl/certs/ca-certificates.crt ]] || missing_packages+=(ca-certificates)

if (( ${#missing_packages[@]} > 0 )); then
  command -v apt-get >/dev/null 2>&1 || fail "apt-get is required to install bootstrap dependencies"
  printf '[SG-Gateway] Preparing required Ubuntu tools...\n'
  apt-get -o Dpkg::Use-Pty=0 update -qq
  env DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a \
    apt-get -o Dpkg::Use-Pty=0 install -y -qq --no-install-recommends "${missing_packages[@]}"
fi

for command in curl tar gzip; do
  command -v "$command" >/dev/null 2>&1 || fail "missing command after bootstrap: $command"
done

TEMP_DIR="$(mktemp -d /tmp/sg-gateway-github-install.XXXXXX)"
ARCHIVE="$TEMP_DIR/sg-gateway-main.tar.gz"
SOURCE_DIR="$TEMP_DIR/source"
mkdir -p "$SOURCE_DIR"

printf '[SG-Gateway] Downloading GitHub branch %s...\n' "$BRANCH"
curl -fL --retry 6 --retry-all-errors --retry-delay 3 --connect-timeout 20 \
  "$ARCHIVE_URL" -o "$ARCHIVE"

gzip -t "$ARCHIVE"
tar -xzf "$ARCHIVE" -C "$SOURCE_DIR" --strip-components=1

[[ -f "$SOURCE_DIR/install.sh" ]] || fail "install.sh is missing from the GitHub archive"
[[ -f "$SOURCE_DIR/VERSION" ]] || fail "VERSION is missing from the GitHub archive"
[[ -f "$SOURCE_DIR/requirements.txt" ]] || fail "requirements.txt is missing from the GitHub archive"
[[ -d "$SOURCE_DIR/app" ]] || fail "application source is missing from the GitHub archive"

printf '[SG-Gateway] GitHub source version: %s\n' "$(tr -d '\r\n' < "$SOURCE_DIR/VERSION")"
printf '[SG-Gateway] Starting the native Ubuntu installer...\n'
SG_GATEWAY_SOURCE_DIR="$SOURCE_DIR" bash "$SOURCE_DIR/install.sh"
