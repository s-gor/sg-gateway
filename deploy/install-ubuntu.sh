#!/usr/bin/env sh
set -eu

REPO_URL="${SG_GATEWAY_REPO_URL:-https://github.com/s-gor/sg-gateway.git}"
BRANCH="${SG_GATEWAY_BRANCH:-main}"
PREFIX="${SG_GATEWAY_PREFIX:-/opt/sg-gateway}"
BIND_HOST="${SG_GATEWAY_BIND_HOST:-0.0.0.0}"
PUBLIC_PORT="${SG_GATEWAY_PUBLIC_PORT:-${SG_GATEWAY_PORT:-80}}"
ADMIN_PASSWORD="${SG_GATEWAY_ADMIN_PASSWORD:-change-this-password}"
SECRET_KEY="${SG_GATEWAY_SECRET_KEY:-}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root, for example: curl ... | sudo sh" >&2
  exit 1
fi

if [ -z "$SECRET_KEY" ]; then
  if command -v openssl >/dev/null 2>&1; then
    SECRET_KEY="$(openssl rand -hex 32)"
  else
    SECRET_KEY="$(date +%s)-sg-gateway-secret"
  fi
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y ca-certificates curl git

if ! command -v docker >/dev/null 2>&1; then
  if apt-cache policy docker-ce 2>/dev/null | grep -q 'Candidate: [^(]'; then
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  else
    apt-get install -y docker.io docker-compose-plugin
  fi
elif ! docker compose version >/dev/null 2>&1; then
  apt-get install -y docker-compose-plugin
fi

systemctl enable --now docker >/dev/null 2>&1 || true

if [ -d "$PREFIX/.git" ]; then
  git -C "$PREFIX" fetch origin "$BRANCH"
  git -C "$PREFIX" checkout "$BRANCH"
  git -C "$PREFIX" reset --hard "origin/$BRANCH"
else
  rm -rf "$PREFIX"
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$PREFIX"
fi

cd "$PREFIX"

if grep -q '127.0.0.1:8080:8080' docker-compose.yml; then
  sed -i "s/127.0.0.1:8080:8080/${BIND_HOST}:${PUBLIC_PORT}:8080/" docker-compose.yml
fi

cat > "$PREFIX/docker-compose.override.yml" <<EOF
services:
  panel:
    environment:
      SG_GATEWAY_ENV: production
      SG_GATEWAY_HOST: 0.0.0.0
      SG_GATEWAY_PORT: 8080
      SG_GATEWAY_SECRET_KEY: ${SECRET_KEY}
      SG_GATEWAY_ADMIN_PASSWORD: ${ADMIN_PASSWORD}
EOF

mkdir -p /var/lib/sg-gateway /var/log/sg-gateway

docker compose up -d --build panel

echo
echo "SG-Gateway installed."
if [ "$PUBLIC_PORT" = "80" ]; then
  echo "URL: http://SERVER_IP"
else
  echo "URL: http://SERVER_IP:${PUBLIC_PORT}"
fi
echo "Password: ${ADMIN_PASSWORD}"
echo
echo "Status:"
docker compose ps
