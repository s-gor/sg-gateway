#!/usr/bin/env bash
set -Eeuo pipefail

MODE=""
HOST=""
PUBLIC_PORT=""

APP_ROOT="/opt/sg-gateway"
ENV_FILE="/etc/sg-gateway/sg-gateway.env"
STATE_DIR="/var/lib/sg-gateway/security"
STATE_FILE="$STATE_DIR/tls-state.json"
REQUEST_FILE="$STATE_DIR/tls-request.json"
BACKUP_ROOT="$STATE_DIR/backups"
NGINX_CONF="/etc/nginx/sites-available/sg-gateway"
NGINX_LINK="/etc/nginx/sites-enabled/sg-gateway"
ACME_CONF="/etc/nginx/sites-available/sg-gateway-acme"
ACME_LINK="/etc/nginx/sites-enabled/sg-gateway-acme"
ACME_ROOT="/var/www/sg-gateway-acme"
RENEW_HOOK="/etc/letsencrypt/renewal-hooks/deploy/reload-sg-gateway-nginx.sh"
PANEL_USER="sg-gateway"
PANEL_GROUP="sg-gateway"

log(){ printf '[SG-Gateway HTTPS] %s\n' "$*"; }
fail(){ printf '[SG-Gateway HTTPS] ОШИБКА: %s\n' "$*" >&2; exit 1; }

usage(){
  cat <<'USAGE'
Использование:
  configure-panel-access.sh --mode https --host panel.example.com --port 63443
  configure-panel-access.sh --mode renew
  configure-panel-access.sh --mode rollback
  configure-panel-access.sh --mode refresh
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --host) HOST="${2:-}"; shift 2 ;;
    --port) PUBLIC_PORT="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) fail "неизвестный параметр: $1" ;;
  esac
done

[[ $EUID -eq 0 ]] || fail "запустите скрипт от root"
[[ "$MODE" == "https" || "$MODE" == "renew" || "$MODE" == "rollback" || "$MODE" == "refresh" ]] || { usage; exit 1; }
[[ -f "$ENV_FILE" ]] || fail "не найден $ENV_FILE"

get_env(){
  local key="$1" default="$2" value
  value="$(grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  printf '%s' "${value:-$default}"
}

BACKEND_PORT="$(get_env SG_GATEWAY_PORT 18080)"
CONFIGURED_PUBLIC_PORT="$(get_env SG_GATEWAY_PUBLIC_PORT 63443)"
PUBLIC_PORT="${PUBLIC_PORT:-$CONFIGURED_PUBLIC_PORT}"

[[ "$BACKEND_PORT" =~ ^[0-9]+$ ]] && (( BACKEND_PORT >= 1 && BACKEND_PORT <= 65535 )) || fail "некорректный backend port: $BACKEND_PORT"
[[ "$PUBLIC_PORT" =~ ^[0-9]+$ ]] && (( PUBLIC_PORT >= 1024 && PUBLIC_PORT <= 65535 )) || fail "порт панели должен быть 1024–65535"
[[ "$PUBLIC_PORT" == "$CONFIGURED_PUBLIC_PORT" ]] || fail "порт должен совпадать с установленным портом панели $CONFIGURED_PUBLIC_PORT"
case "$PUBLIC_PORT" in
  22|80|585|8090|18080) fail "порт $PUBLIC_PORT зарезервирован для другого назначения" ;;
esac

for command in nginx certbot openssl getent curl python3 systemctl; do
  command -v "$command" >/dev/null 2>&1 || fail "не найден $command"
done

install -d -m 0750 -o "$PANEL_USER" -g "$PANEL_GROUP" "$STATE_DIR"
install -d -m 0750 -o root -g "$PANEL_GROUP" "$BACKUP_ROOT"
install -d -m 0755 "$ACME_ROOT/.well-known/acme-challenge"
install -d -m 0755 /etc/nginx/sites-available /etc/nginx/sites-enabled
install -d -m 0755 /etc/letsencrypt/renewal-hooks/deploy

read_state_value(){
  local key="$1"
  python3 - "$STATE_FILE" "$key" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
key = sys.argv[2]
try:
    value = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    value = {}
print(value.get(key, ""))
PY
}

write_state(){
  local domain="$1" action="$2" message="$3" backup_name="${4:-}"
  python3 - "$STATE_FILE" "$domain" "$PUBLIC_PORT" "$BACKEND_PORT" "$action" "$message" "$backup_name" "$PANEL_GROUP" <<'PY'
import grp
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
domain = sys.argv[2]
public_port = int(sys.argv[3])
backend_port = int(sys.argv[4])
action = sys.argv[5]
message = sys.argv[6]
backup = sys.argv[7]
group = sys.argv[8]
cert_path = Path(f"/etc/letsencrypt/live/{domain}/fullchain.pem")
key_path = Path(f"/etc/letsencrypt/live/{domain}/privkey.pem")

certificate = {}
try:
    result = subprocess.run(
        [
            "openssl", "x509", "-in", str(cert_path), "-noout",
            "-subject", "-issuer", "-startdate", "-enddate", "-serial",
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode == 0:
        parsed = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                parsed[key.strip().lower()] = value.strip()
        days_left = None
        end = parsed.get("notafter", "")
        if end:
            try:
                expiry = datetime.strptime(end, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                days_left = max(0, (expiry - datetime.now(timezone.utc)).days)
            except ValueError:
                pass
        certificate = {
            "subject": parsed.get("subject", ""),
            "issuer": parsed.get("issuer", ""),
            "not_before": parsed.get("notbefore", ""),
            "not_after": parsed.get("notafter", ""),
            "serial": parsed.get("serial", ""),
            "days_left": days_left,
        }
except (OSError, subprocess.TimeoutExpired):
    certificate = {}

payload = {
    "domain": domain,
    "public_port": public_port,
    "panel_port": public_port,
    "backend_port": backend_port,
    "https_ready": bool(certificate),
    "certificate": certificate,
    "certificate_path": str(cert_path),
    "key_path": str(key_path),
    "last_action": action,
    "last_message": message,
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "backup": backup,
}
path.parent.mkdir(parents=True, exist_ok=True)
temporary = path.with_name(path.name + ".new")
temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.chmod(temporary, 0o640)
try:
    os.chown(temporary, 0, grp.getgrnam(group).gr_gid)
except KeyError:
    pass
os.replace(temporary, path)
PY
}

wait_for_backend(){
  local attempt
  log "Ожидаю backend 127.0.0.1:$BACKEND_PORT"
  for ((attempt=1; attempt<=45; attempt++)); do
    if curl -fsS --max-time 3 "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null 2>&1; then
      log "Backend панели готов"
      return 0
    fi
    sleep 1
  done
  systemctl --no-pager --full status sg-gateway.service >&2 || true
  journalctl -u sg-gateway.service -n 60 --no-pager >&2 || true
  fail "backend не стал доступен за 45 секунд"
}

wait_for_https(){
  local domain="$1" attempt
  log "Проверяю HTTPS https://$domain:$PUBLIC_PORT/health"
  for ((attempt=1; attempt<=20; attempt++)); do
    if curl -kfsS --max-time 5 \
      --resolve "$domain:$PUBLIC_PORT:127.0.0.1" \
      "https://$domain:$PUBLIC_PORT/health" >/dev/null 2>&1; then
      log "HTTPS отвечает корректно"
      return 0
    fi
    sleep 1
  done
  tail -n 60 /var/log/nginx/error.log >&2 2>/dev/null || true
  fail "HTTPS не стал доступен за 20 секунд"
}

apply_client_runtime(){
  local output
  log "Применяю клиентские runtime с новым TLS-сертификатом"
  if output="$(
    cd "$APP_ROOT"
    PYTHONPATH="$APP_ROOT:$APP_ROOT/hostd" \
      "$APP_ROOT/.venv/bin/python" - \
      "$ENV_FILE" \
      "/etc/sg-gateway/runtime.env" \
      "/etc/sg-gateway/engine-secrets.env" <<'PY'
import json
import os
import shlex
import sys
from pathlib import Path


def load_environment_file(filename: str) -> None:
    path = Path(filename)
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value[:1] in {"\"", "'"}:
            try:
                parsed = shlex.split(value, posix=True)
                value = parsed[0] if parsed else ""
            except ValueError:
                value = value[1:-1] if len(value) >= 2 else ""
        os.environ[key] = value


for environment_file in sys.argv[1:]:
    load_environment_file(environment_file)

from sg_hostd.client_runtime import apply_all_clients

result = apply_all_clients()
print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
if not result.get("ok"):
    raise SystemExit(1)
PY
  )"; then
    while IFS= read -r line; do
      [[ -n "$line" ]] && log "$line"
    done <<<"$output"
  else
    log "ПРЕДУПРЕЖДЕНИЕ: HTTPS включён, но клиентские runtime применились не полностью"
    while IFS= read -r line; do
      [[ -n "$line" ]] && printf '[SG-Gateway HTTPS] %s\n' "$line" >&2
    done <<<"$output"
  fi
}

detect_public_ipv4(){
  local token="" value=""
  token="$(curl -fsS --connect-timeout 1 --max-time 2 -X PUT \
    -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' \
    http://169.254.169.254/latest/api/token 2>/dev/null || true)"
  if [[ -n "$token" ]]; then
    value="$(curl -fsS --connect-timeout 1 --max-time 2 \
      -H "X-aws-ec2-metadata-token: $token" \
      http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)"
  fi
  if [[ ! "$value" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    value="$(curl -4fsS --max-time 15 https://checkip.amazonaws.com 2>/dev/null | tr -d '[:space:]' || true)"
  fi
  printf '%s' "$value"
}

backup_path(){
  local source="$1" name="$2" backup_dir="$3"
  if [[ -e "$source" || -L "$source" ]]; then
    cp -a "$source" "$backup_dir/$name"
  fi
}

restore_path(){
  local backup="$1" target="$2"
  rm -rf "$target"
  if [[ -e "$backup" || -L "$backup" ]]; then
    mkdir -p "$(dirname "$target")"
    cp -a "$backup" "$target"
  fi
}

create_backup(){
  local backup_dir="$BACKUP_ROOT/$(date -u +%Y%m%d-%H%M%S)-panel-access"
  install -d -m 0750 -o root -g "$PANEL_GROUP" "$backup_dir"
  backup_path "$NGINX_CONF" nginx-conf "$backup_dir"
  backup_path "$NGINX_LINK" nginx-link "$backup_dir"
  backup_path "$ACME_CONF" acme-conf "$backup_dir"
  backup_path "$ACME_LINK" acme-link "$backup_dir"
  backup_path "$STATE_FILE" tls-state.json "$backup_dir"
  backup_path "$RENEW_HOOK" renewal-hook "$backup_dir"
  printf '%s' "$backup_dir"
}

restore_backup(){
  local backup_dir="$1"
  restore_path "$backup_dir/nginx-conf" "$NGINX_CONF"
  restore_path "$backup_dir/nginx-link" "$NGINX_LINK"
  restore_path "$backup_dir/acme-conf" "$ACME_CONF"
  restore_path "$backup_dir/acme-link" "$ACME_LINK"
  restore_path "$backup_dir/tls-state.json" "$STATE_FILE"
  restore_path "$backup_dir/renewal-hook" "$RENEW_HOOK"
  if nginx -t >/dev/null 2>&1; then
    systemctl reload nginx.service >/dev/null 2>&1 || true
  fi
}

configure_https(){
  [[ -n "$HOST" ]] || fail "укажите домен"
  HOST="${HOST,,}"
  [[ "$HOST" =~ ^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$ ]] || fail "некорректное доменное имя"

  local public_ip resolved cert_dir cert_file key_file https_authority
  SG_HTTPS_BACKUP_DIR=""
  SG_HTTPS_COMMITTED=0
  public_ip="$(detect_public_ipv4)"
  [[ "$public_ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || fail "не удалось определить публичный IPv4"
  resolved="$(getent ahostsv4 "$HOST" | awk '{print $1}' | sort -u || true)"
  if ! grep -Fxq "$public_ip" <<<"$resolved"; then
    printf 'Домен: %s\nПубличный IP: %s\nDNS возвращает:\n%s\n' "$HOST" "$public_ip" "${resolved:-ничего}" >&2
    fail "A-запись домена ещё не указывает на этот сервер"
  fi

  SG_HTTPS_BACKUP_DIR="$(create_backup)"
  rollback(){
    local rc=$?
    trap - EXIT ERR INT TERM
    if [[ ${SG_HTTPS_COMMITTED:-0} -eq 0 && -n ${SG_HTTPS_BACKUP_DIR:-} ]]; then
      log "HTTPS не настроен, восстанавливаю предыдущую конфигурацию"
      restore_backup "$SG_HTTPS_BACKUP_DIR"
    fi
    exit "$rc"
  }
  trap rollback EXIT INT TERM

  log "Готовлю HTTP-01 на TCP 80"
  cat > "$ACME_CONF" <<EOF_ACME
server {
    listen 80;
    listen [::]:80;
    server_name $HOST;

    location ^~ /.well-known/acme-challenge/ {
        root $ACME_ROOT;
        default_type text/plain;
    }

    location / {
        return 404;
    }
}
EOF_ACME
  ln -sfn "$ACME_CONF" "$ACME_LINK"
  nginx -t
  systemctl enable --now nginx.service
  systemctl reload nginx.service

  cert_dir="/etc/letsencrypt/live/$HOST"
  cert_file="$cert_dir/fullchain.pem"
  key_file="$cert_dir/privkey.pem"
  if [[ -s "$cert_file" && -s "$key_file" ]] && openssl x509 -checkend 604800 -noout -in "$cert_file" >/dev/null 2>&1; then
    log "Использую существующий сертификат"
  else
    log "Получаю сертификат Let's Encrypt для $HOST"
    certbot certonly \
      --webroot -w "$ACME_ROOT" \
      --domain "$HOST" \
      --register-unsafely-without-email \
      --agree-tos \
      --non-interactive \
      --keep-until-expiring
  fi
  [[ -s "$cert_file" && -s "$key_file" ]] || fail "Certbot не создал ожидаемые файлы сертификата"

  https_authority="$HOST"
  [[ "$PUBLIC_PORT" == "443" ]] || https_authority="$HOST:$PUBLIC_PORT"

  log "Переключаю Nginx на HTTPS"
  cat > "$NGINX_CONF" <<EOF_NGINX
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    location ^~ /.well-known/acme-challenge/ {
        root $ACME_ROOT;
        default_type text/plain;
    }

    location / {
        return 404;
    }
}

server {
    listen 80;
    listen [::]:80;
    server_name $HOST;

    location ^~ /.well-known/acme-challenge/ {
        root $ACME_ROOT;
        default_type text/plain;
    }

    location / {
        return 308 https://$https_authority\$request_uri;
    }
}

server {
    listen $PUBLIC_PORT ssl;
    listen [::]:$PUBLIC_PORT ssl;
    server_name $HOST;

    error_page 497 =308 https://$https_authority\$request_uri;

    ssl_certificate $cert_file;
    ssl_certificate_key $key_file;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:SG_GATEWAY_TLS:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_cookie_flags ~ secure httponly samesite=lax;
        proxy_read_timeout 120s;
    }
}
EOF_NGINX

  rm -f "$ACME_LINK" "$ACME_CONF"
  ln -sfn "$NGINX_CONF" "$NGINX_LINK"
  nginx -t
  systemctl reload nginx.service

  wait_for_backend
  wait_for_https "$HOST"

  systemctl enable --now certbot.timer >/dev/null 2>&1 || true
  cat > "$RENEW_HOOK" <<'EOF_HOOK'
#!/usr/bin/env bash
set -Eeuo pipefail
exec /bin/bash /opt/sg-gateway/deploy/configure-panel-access.sh --mode refresh
EOF_HOOK
  chmod 0755 "$RENEW_HOOK"

  write_state "$HOST" issue "HTTPS включён и проверен" "$(basename "$SG_HTTPS_BACKUP_DIR")"
  apply_client_runtime
  SG_HTTPS_COMMITTED=1
  trap - EXIT ERR INT TERM
  log "HTTPS настроен: https://$HOST:$PUBLIC_PORT"
  log "Backend: 127.0.0.1:$BACKEND_PORT"
  log "Резервная конфигурация: $(basename "$SG_HTTPS_BACKUP_DIR")"
}

renew_https(){
  local domain
  domain="$(read_state_value domain)"
  [[ -n "$domain" ]] || fail "HTTPS ещё не настроен"
  log "Проверяю обновление сертификата $domain"
  certbot renew --cert-name "$domain" --non-interactive
  nginx -t
  systemctl reload nginx.service
  wait_for_https "$domain"
  write_state "$domain" renew "Сертификат проверен/обновлён" "$(read_state_value backup)"
  apply_client_runtime
  log "Сертификат $domain проверен; Nginx и клиентские runtime обновлены"
}

refresh_https(){
  local domain
  domain="$(read_state_value domain)"
  [[ -n "$domain" ]] || fail "HTTPS ещё не настроен"
  nginx -t
  systemctl reload nginx.service
  wait_for_https "$domain"
  write_state "$domain" refresh "Сертификат и Nginx проверены" "$(read_state_value backup)"
  apply_client_runtime
  log "Состояние сертификата и клиентских runtime обновлено"
}

rollback_https(){
  local latest current
  latest="$(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name '*-panel-access' -printf '%f\n' | sort | tail -n 1 || true)"
  [[ -n "$latest" ]] || fail "нет резервной конфигурации HTTPS"
  current="$(create_backup)"
  restore_backup "$BACKUP_ROOT/$latest"
  if ! nginx -t; then
    restore_backup "$current"
    fail "резервная конфигурация не прошла nginx -t; текущая конфигурация возвращена"
  fi
  if ! systemctl reload nginx.service; then
    restore_backup "$current"
    fail "Nginx не принял резервную конфигурацию; текущая конфигурация возвращена"
  fi
  log "Восстановлена конфигурация $latest; страховочная копия текущей: $(basename "$current")"
}

case "$MODE" in
  https) configure_https ;;
  renew) renew_https ;;
  rollback) rollback_https ;;
  refresh) refresh_https ;;
esac
