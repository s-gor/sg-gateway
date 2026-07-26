from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import load_config
from app.hostd.client import run_hostd_command
from app.maintenance.operations import log_operation


DOMAIN_RE = re.compile(
    r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


class TlsError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_dir() -> Path:
    override = os.getenv("SG_GATEWAY_SECURITY_STATE_DIR", "").strip()
    return Path(override) if override else load_config().data_dir / "security"


def _request_path() -> Path:
    return _state_dir() / "tls-request.json"


def _state_path() -> Path:
    return _state_dir() / "tls-state.json"


def _backups_dir() -> Path:
    return _state_dir() / "backups"


def _ensure_dirs() -> None:
    _state_dir().mkdir(parents=True, exist_ok=True)
    _backups_dir().mkdir(parents=True, exist_ok=True)


def normalize_domain(value: str) -> str:
    domain = (value or "").strip().lower().rstrip(".")
    if domain.startswith("http://") or domain.startswith("https://"):
        raise TlsError("Введите только домен без http:// или https://")
    if not DOMAIN_RE.fullmatch(domain):
        raise TlsError("Некорректное доменное имя")
    return domain


def normalize_email(value: str) -> str:
    """Legacy compatibility: email is no longer required by SG-Gateway."""
    return (value or "").strip().lower()


def _write_json(path: Path, payload: dict, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{uuid.uuid4().hex}")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _public_ip() -> str:
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip"):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "SG-Gateway-Security/1.0"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                value = response.read(128).decode("ascii", "ignore").strip()
            socket.inet_aton(value)
            return value
        except (OSError, ValueError, urllib.error.URLError, TimeoutError):
            continue
    return ""


def check_domain(domain: str) -> dict:
    normalized = normalize_domain(domain)
    addresses: set[str] = set()
    try:
        for item in socket.getaddrinfo(normalized, 443, type=socket.SOCK_STREAM):
            address = item[4][0]
            if ":" not in address:
                addresses.add(address)
    except socket.gaierror as exc:
        return {
            "domain": normalized,
            "ok": False,
            "status": "error",
            "message": f"DNS не разрешается: {exc}",
            "addresses": [],
            "public_ip": _public_ip(),
            "matches_public_ip": False,
            "checked_at": _utc_now(),
        }

    public_ip = _public_ip()
    matches = bool(public_ip and public_ip in addresses)
    if not addresses:
        status = "error"
        message = "Для домена не найден IPv4-адрес"
    elif public_ip and not matches:
        status = "warning"
        message = (
            f"Домен ведёт на {', '.join(sorted(addresses))}, "
            f"а публичный IPv4 сервера определён как {public_ip}"
        )
    elif matches:
        status = "ok"
        message = "DNS домена указывает на публичный IPv4 этого сервера"
    else:
        status = "warning"
        message = "DNS найден, но публичный IPv4 сервера определить не удалось"

    return {
        "domain": normalized,
        "ok": status != "error",
        "status": status,
        "message": message,
        "addresses": sorted(addresses),
        "public_ip": public_ip,
        "matches_public_ip": matches,
        "checked_at": _utc_now(),
    }


def stage_request(domain: str, email: str | None = None) -> dict:
    _ensure_dirs()
    normalized_domain = normalize_domain(domain)
    dns = check_domain(normalized_domain)
    config = load_config()
    payload = {
        "domain": normalized_domain,
        "panel_port": int(config.public_port),
        "public_port": int(config.public_port),
        "backend_port": int(config.port),
        "dns": dns,
        "created_at": _utc_now(),
    }
    _write_json(_request_path(), payload)
    log_operation(
        "security.tls.check",
        f"tls:{normalized_domain}",
        dns["message"],
        status="ok" if dns["status"] != "error" else "error",
    )
    return payload


def _helper_path() -> Path:
    return Path(
        os.getenv(
            "SG_GATEWAY_TLS_HELPER",
            "/usr/local/lib/sg-gateway/tls-helper",
        )
    )


def _run_helper(action: str) -> dict:
    command = f"tls.{action}"
    result = run_hostd_command(command, timeout=600)
    if result.status != "ok":
        raise TlsError(result.message or f"{command} failed")

    payload = dict(result.payload)
    payload.setdefault("ok", True)
    payload.setdefault("message", result.message)
    return payload

def issue_certificate() -> dict:
    request = _read_json(_request_path())
    if not request:
        raise TlsError("Сначала проверьте домен")
    payload = _run_helper("issue")
    log_operation(
        "security.tls.issue",
        f"tls:{request.get('domain', 'unknown')}",
        str(payload.get("message", "TLS certificate issued")),
    )
    return payload


def renew_certificate() -> dict:
    payload = _run_helper("renew")
    state = _read_json(_state_path()) or {}
    log_operation(
        "security.tls.renew",
        f"tls:{state.get('domain', 'unknown')}",
        str(payload.get("message", "TLS certificate renewed")),
    )
    return payload


def rollback_latest() -> dict:
    payload = _run_helper("rollback")
    log_operation(
        "security.tls.rollback",
        "tls:nginx",
        str(payload.get("message", "TLS configuration restored")),
    )
    return payload


def _openssl_info(cert_path: Path) -> dict:
    if not cert_path.is_file() or shutil.which("openssl") is None:
        return {}
    result = subprocess.run(
        [
            "openssl",
            "x509",
            "-in",
            str(cert_path),
            "-noout",
            "-subject",
            "-issuer",
            "-startdate",
            "-enddate",
            "-serial",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode != 0:
        return {}
    parsed: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip().lower()] = value.strip()
    days_left = None
    end = parsed.get("notafter")
    if end:
        try:
            expiry = datetime.strptime(end, "%b %d %H:%M:%S %Y %Z").replace(
                tzinfo=timezone.utc
            )
            days_left = max(0, (expiry - datetime.now(timezone.utc)).days)
        except ValueError:
            pass
    return {
        "subject": parsed.get("subject", ""),
        "issuer": parsed.get("issuer", ""),
        "not_before": parsed.get("notbefore", ""),
        "not_after": parsed.get("notafter", ""),
        "serial": parsed.get("serial", ""),
        "days_left": days_left,
    }


def _service_active(name: str) -> bool:
    if shutil.which("systemctl") is None:
        return False
    return (
        subprocess.run(
            ["systemctl", "is-active", "--quiet", name],
            check=False,
        ).returncode
        == 0
    )


def _service_enabled(name: str) -> bool:
    if shutil.which("systemctl") is None:
        return False
    return (
        subprocess.run(
            ["systemctl", "is-enabled", "--quiet", name],
            check=False,
        ).returncode
        == 0
    )


def overview() -> dict:
    _ensure_dirs()
    state = _read_json(_state_path()) or {}
    request = _read_json(_request_path()) or {}
    domain = state.get("domain") or request.get("domain") or ""
    cert_path = (
        Path(f"/etc/letsencrypt/live/{domain}/fullchain.pem")
        if domain
        else Path("/nonexistent")
    )
    cert = _openssl_info(cert_path)
    nginx_conf = Path("/etc/nginx/sites-available/sg-gateway")
    https_ready = bool(domain and cert and nginx_conf.is_file() and _service_active("nginx.service"))
    dns = request.get("dns") or (check_domain(domain) if domain else None)
    return {
        "domain": domain,
        "https_ready": https_ready,
        "nginx_active": _service_active("nginx.service"),
        "certbot_timer": _service_active("certbot.timer"),
        "certbot_timer_enabled": _service_enabled("certbot.timer"),
        "certificate": cert,
        "dns": dns,
        "panel_port": int(load_config().public_port),
        "backend_port": int(load_config().port),
        "nginx_config": str(nginx_conf),
        "certificate_path": str(cert_path) if domain else "",
        "last_action": state.get("last_action", ""),
        "last_message": state.get("last_message", ""),
        "updated_at": state.get("updated_at", ""),
        "backups": [
            item.name
            for item in sorted(_backups_dir().glob("*"), reverse=True)[:10]
            if item.is_dir()
        ],
    }


def health_status() -> dict:
    state = overview()
    if not state["domain"]:
        return {
            "status": "warning",
            "message": "Домен и HTTPS ещё не настроены",
        }
    if state["https_ready"]:
        days = state["certificate"].get("days_left")
        suffix = f", осталось {days} дней" if days is not None else ""
        return {
            "status": "ok",
            "message": f"HTTPS активен для {state['domain']}{suffix}",
        }
    return {
        "status": "warning",
        "message": f"HTTPS для {state['domain']} ещё не готов",
    }


def _request_for_root() -> dict:
    request = _read_json(_request_path())
    if not request:
        raise TlsError("TLS request не найден")
    request["domain"] = normalize_domain(str(request.get("domain", "")))
    config = load_config()
    request["public_port"] = int(request.get("public_port", request.get("panel_port", config.public_port)))
    request["backend_port"] = int(request.get("backend_port", config.port))
    request["panel_port"] = request["public_port"]
    for label, port in (("публичный", request["public_port"]), ("внутренний", request["backend_port"])):
        if port < 1 or port > 65535:
            raise TlsError(f"Некорректный {label} порт панели")
    return request


def _nginx_http(domain: str, backend_port: int, public_port: int) -> str:
    return f"""server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    location ^~ /.well-known/acme-challenge/ {{
        root /var/www/sg-gateway-acme;
        default_type text/plain;
    }}

    location / {{
        proxy_pass http://127.0.0.1:{backend_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto http;
    }}
}}

server {{
    listen {public_port};
    listen [::]:{public_port};
    server_name _;

    location / {{
        proxy_pass http://127.0.0.1:{backend_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto http;
    }}
}}
"""


def _nginx_https(domain: str, backend_port: int, public_port: int) -> str:
    redirect_port = "" if public_port == 443 else f":{public_port}"
    return f"""server {{
    listen 80;
    listen [::]:80;
    server_name {domain};

    location ^~ /.well-known/acme-challenge/ {{
        root /var/www/sg-gateway-acme;
        default_type text/plain;
    }}

    location / {{
        return 301 https://$host{redirect_port}$request_uri;
    }}
}}

server {{
    listen {public_port} ssl http2;
    listen [::]:{public_port} ssl http2;
    server_name {domain};

    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SG_GATEWAY_TLS:10m;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {{
        proxy_pass http://127.0.0.1:{backend_port};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 120s;
    }}
}}
"""


def _progress(message: str) -> None:
    if os.getenv("SG_GATEWAY_TLS_LIVE_LOG", "").strip() == "1":
        print(f"[SG-Gateway HTTPS] {message}", flush=True)


def _run(command: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    live = os.getenv("SG_GATEWAY_TLS_LIVE_LOG", "").strip() == "1"
    if live:
        print("$ " + " ".join(command), flush=True)
        result = subprocess.run(command, text=True, timeout=timeout, check=False)
    else:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        raise TlsError((getattr(result, "stderr", "") or getattr(result, "stdout", "") or "Command failed").strip())
    return result


def _backup_nginx() -> Path:
    _ensure_dirs()
    backup = _backups_dir() / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup.mkdir(parents=True, exist_ok=False)
    available = Path("/etc/nginx/sites-available/sg-gateway")
    enabled = Path("/etc/nginx/sites-enabled/sg-gateway")
    if available.is_file():
        shutil.copy2(available, backup / "sg-gateway.nginx")
    if enabled.is_symlink():
        (backup / "enabled-target.txt").write_text(
            os.readlink(enabled),
            encoding="utf-8",
        )
    if _state_path().is_file():
        shutil.copy2(_state_path(), backup / "tls-state.json")
    bind_dropin = Path(
        "/etc/systemd/system/sg-gateway.service.d/50-https-local-bind.conf"
    )
    if bind_dropin.is_file():
        shutil.copy2(bind_dropin, backup / "50-https-local-bind.conf")
    return backup


def _write_nginx(config: str) -> None:
    available = Path("/etc/nginx/sites-available/sg-gateway")
    enabled = Path("/etc/nginx/sites-enabled/sg-gateway")
    available.parent.mkdir(parents=True, exist_ok=True)
    enabled.parent.mkdir(parents=True, exist_ok=True)
    temp = available.with_name(available.name + f".tmp-{uuid.uuid4().hex}")
    temp.write_text(config, encoding="utf-8")
    os.chmod(temp, 0o644)
    os.replace(temp, available)
    if enabled.exists() or enabled.is_symlink():
        enabled.unlink()
    enabled.symlink_to(available)


def _restore_backup(backup: Path) -> None:
    available = Path("/etc/nginx/sites-available/sg-gateway")
    enabled = Path("/etc/nginx/sites-enabled/sg-gateway")
    previous = backup / "sg-gateway.nginx"
    if previous.is_file():
        shutil.copy2(previous, available)
    elif available.exists():
        available.unlink()
    if enabled.exists() or enabled.is_symlink():
        enabled.unlink()
    target_file = backup / "enabled-target.txt"
    if target_file.is_file():
        enabled.symlink_to(target_file.read_text(encoding="utf-8").strip())
    elif previous.is_file():
        enabled.symlink_to(available)
    previous_state = backup / "tls-state.json"
    if previous_state.is_file():
        shutil.copy2(previous_state, _state_path())
    bind_dropin = Path(
        "/etc/systemd/system/sg-gateway.service.d/50-https-local-bind.conf"
    )
    previous_bind = backup / "50-https-local-bind.conf"
    bind_dropin.parent.mkdir(parents=True, exist_ok=True)
    if previous_bind.is_file():
        shutil.copy2(previous_bind, bind_dropin)
    elif bind_dropin.exists():
        bind_dropin.unlink()
    subprocess.run(
        ["systemctl", "daemon-reload"],
        capture_output=True,
        text=True,
        check=False,
    )
    subprocess.run(
        ["systemctl", "restart", "sg-gateway.service"],
        capture_output=True,
        text=True,
        check=False,
    )


def _enable_local_panel_bind() -> None:
    dropin = Path(
        "/etc/systemd/system/sg-gateway.service.d/50-https-local-bind.conf"
    )
    dropin.parent.mkdir(parents=True, exist_ok=True)
    dropin.write_text(
        "[Service]\nEnvironment=SG_GATEWAY_HOST=127.0.0.1\n",
        encoding="utf-8",
    )
    os.chmod(dropin, 0o644)
    _run(["systemctl", "daemon-reload"])
    _run(["systemctl", "restart", "sg-gateway.service"])
    _run(["systemctl", "is-active", "--quiet", "sg-gateway.service"])


def root_issue() -> dict:
    request = _request_for_root()
    domain = request["domain"]
    public_port = request["public_port"]
    backend_port = request["backend_port"]
    _progress(f"Домен: {domain}; публичный порт: {public_port}; backend: {backend_port}")
    if shutil.which("nginx") is None or shutil.which("certbot") is None:
        raise TlsError("Nginx или Certbot не установлены")

    _progress("Создаю полную резервную копию Nginx, TLS state и local-bind")
    backup = _backup_nginx()
    try:
        _progress("Готовлю временный HTTP-01 listener на TCP 80")
        Path("/var/www/sg-gateway-acme").mkdir(parents=True, exist_ok=True)
        _write_nginx(_nginx_http(domain, backend_port, public_port))
        _run(["nginx", "-t"])
        _run(["systemctl", "enable", "--now", "nginx.service"])
        _run(["systemctl", "reload", "nginx.service"])

        cert = Path(f"/etc/letsencrypt/live/{domain}/fullchain.pem")
        key = Path(f"/etc/letsencrypt/live/{domain}/privkey.pem")
        if cert.is_file() and key.is_file():
            _progress("Действующий сертификат уже найден; повторный выпуск не требуется")
        else:
            _progress("Запускаю Certbot / Let's Encrypt")
            _run([
                "certbot", "certonly", "--webroot", "-w", "/var/www/sg-gateway-acme",
                "-d", domain, "--agree-tos", "--non-interactive",
                "--register-unsafely-without-email", "--keep-until-expiring",
            ], timeout=300)
        if not cert.is_file() or not key.is_file():
            raise TlsError("Certbot завершился без ожидаемого сертификата")

        _progress("Собираю финальную HTTPS-конфигурацию Nginx")
        _write_nginx(_nginx_https(domain, backend_port, public_port))
        _run(["nginx", "-t"])
        _run(["systemctl", "reload", "nginx.service"])
        _progress("Перевожу backend панели на 127.0.0.1")
        _enable_local_panel_bind()
        _progress("Проверяю backend и HTTPS в реальном runtime")
        _run(["curl", "-fsS", "--max-time", "10", f"http://127.0.0.1:{backend_port}/health"], timeout=20)
        _run(["curl", "-kfsS", "--max-time", "12", "--resolve", f"{domain}:{public_port}:127.0.0.1", f"https://{domain}:{public_port}/health"], timeout=25)

        subprocess.run(["systemctl", "enable", "--now", "certbot.timer"], capture_output=True, text=True, check=False)
        hook = Path("/etc/letsencrypt/renewal-hooks/deploy/sg-gateway-nginx")
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text("#!/usr/bin/env bash\nset -e\nnginx -t && systemctl reload nginx.service\n", encoding="utf-8")
        os.chmod(hook, 0o755)
        state = {
            "domain": domain,
            "panel_port": public_port,
            "public_port": public_port,
            "backend_port": backend_port,
            "last_action": "issue",
            "last_message": "HTTPS включён и проверен; панель привязана к 127.0.0.1",
            "updated_at": _utc_now(),
            "backup": backup.name,
            "local_bind": True,
        }
        _write_json(_state_path(), state, mode=0o644)
        _progress("HTTPS успешно включён; сертификат и Nginx проверены")
        suffix = "" if public_port == 443 else f":{public_port}"
        return {"ok": True, "message": f"HTTPS включён: https://{domain}{suffix}", "backup": backup.name}
    except Exception:
        _progress("Ошибка: выполняю автоматический rollback")
        _restore_backup(backup)
        if Path("/etc/nginx/nginx.conf").is_file():
            subprocess.run(["nginx", "-t"], capture_output=True, text=True, check=False)
            subprocess.run(["systemctl", "reload", "nginx.service"], capture_output=True, text=True, check=False)
        _progress(f"Предыдущая конфигурация восстановлена из {backup.name}")
        raise


def root_renew() -> dict:
    state = _read_json(_state_path()) or {}
    domain = normalize_domain(str(state.get("domain", "")))
    _run(["certbot", "renew", "--cert-name", domain, "--non-interactive"], timeout=240)
    _run(["nginx", "-t"])
    _run(["systemctl", "reload", "nginx.service"])
    state.update(
        {
            "last_action": "renew",
            "last_message": "Сертификат проверен/обновлён",
            "updated_at": _utc_now(),
        }
    )
    _write_json(_state_path(), state, mode=0o644)
    return {
        "ok": True,
        "message": f"Сертификат {domain} проверен и Nginx перезагружен",
    }


def root_rollback() -> dict:
    backups = [
        item for item in sorted(_backups_dir().glob("*"), reverse=True) if item.is_dir()
    ]
    if not backups:
        raise TlsError("Нет резервной конфигурации Nginx")
    backup = backups[0]
    current = _backup_nginx()
    try:
        _restore_backup(backup)
        _run(["nginx", "-t"])
        _run(["systemctl", "reload", "nginx.service"])
        return {
            "ok": True,
            "message": (
                f"Восстановлена конфигурация {backup.name}; "
                f"страховочная копия текущей: {current.name}"
            ),
        }
    except Exception:
        _restore_backup(current)
        subprocess.run(
            ["systemctl", "reload", "nginx.service"],
            capture_output=True,
            text=True,
            check=False,
        )
        raise
