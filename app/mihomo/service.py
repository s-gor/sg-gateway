from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import string
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import load_config
from app.connections.geoip_country import lookup_country_code, resolve_host_ip
from app.connections.settings import get_connection_settings, update_connection_settings
from app.db import connect, init_db
from app.hostd.client import run_hostd_command
from app.maintenance.operations import log_operation
from app.clients.repository import get_primary_device


class MihomoError(RuntimeError):
    pass


MIHOMO_VERSION = "1.19.29"
MIHOMO_BINARY = Path("/usr/local/bin/mihomo")
MIHOMO_CONFIG_DIR = Path("/etc/mihomo")
MIHOMO_CONFIG = MIHOMO_CONFIG_DIR / "config.yaml"
MIHOMO_TLS_DIR = MIHOMO_CONFIG_DIR / "tls"
MIHOMO_STATE_DIR = Path("/var/lib/mihomo")
MIHOMO_CANDIDATE_DIR = Path("/var/lib/sg-gateway/candidates/mihomo")
MIHOMO_CANDIDATE = MIHOMO_CANDIDATE_DIR / "candidate.yaml"
MIHOMO_CANDIDATE_META = MIHOMO_CANDIDATE_DIR / "candidate.json"
MIHOMO_BACKUP_DIR = MIHOMO_STATE_DIR / "backups"

PROTOCOLS = ("mieru", "anytls", "tuic")


@dataclass(frozen=True)
class MihomoDeployment:
    client_id: int
    client_name: str
    enabled: bool
    config: dict[str, Any]

    @property
    def device_id(self) -> int:
        return self.client_id

    @property
    def access_name(self) -> str:
        return self.client_name


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    MIHOMO_CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(value: str, fallback: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-_")
    return clean[:48] or fallback


def _secret(length: int = 28) -> str:
    alphabet = string.ascii_letters + string.digits + "-_"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _yaml_string(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _int(value: Any, default: int, minimum: int = 1, maximum: int = 65535) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if minimum <= parsed <= maximum else default


def _tls_state() -> dict[str, Any]:
    path = load_config().data_dir / "security" / "tls-state.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _tls_paths(domain: str) -> tuple[Path, Path]:
    return (
        Path(f"/etc/letsencrypt/live/{domain}/fullchain.pem"),
        Path(f"/etc/letsencrypt/live/{domain}/privkey.pem"),
    )


# SG-Gateway Mihomo TLS readiness from public state
def _tls_ready(domain: str) -> bool:
    # The web panel is intentionally unprivileged and must not inspect
    # /etc/letsencrypt directly. The privileged HTTPS transaction writes
    # a panel-readable tls-state.json after Nginx and the certificate pass.
    if not domain:
        return False

    state = _tls_state()
    state_domain = str(state.get("domain") or "").strip().lower()
    certificate = state.get("certificate")
    return bool(
        state_domain == domain.strip().lower()
        and state.get("https_ready") is not False
        and isinstance(certificate, dict)
        and certificate
    )


def _deployment_config(device_id: int) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT config_json
            FROM device_credentials
            WHERE device_id = ? AND engine = 'mihomo'
            """,
            (device_id,),
        ).fetchone()
    if row is None or not row["config_json"]:
        return None
    try:
        return json.loads(row["config_json"])
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def build_client_credentials(client_id: int, client_name: str) -> tuple[str, str]:
    safe = _safe_name(client_name, f"client-{client_id}")
    payload = {
        "client_name": client_name,
        "mieru": {
            "username": f"{safe}-{client_id}",
            "password": _secret(30),
        },
        "anytls": {
            "label": f"{safe}-{client_id}",
            "password": _secret(32),
        },
        "tuic": {
            "uuid": str(uuid.uuid4()),
            "password": _secret(32),
        },
        "created_at": _now(),
    }
    return f"mihomo-{client_id}", json.dumps(
        payload, ensure_ascii=False, sort_keys=True
    )


def ensure_device_deployment(device_id: int) -> bool:
    init_db()
    with connect() as connection:
        row = connection.execute(
            """
            SELECT d.id, d.name AS device_name, d.is_primary,
                   c.id AS client_id, c.name AS client_name
            FROM devices d
            JOIN clients c ON c.id = d.client_id
            WHERE d.id = ?
            """,
            (device_id,),
        ).fetchone()
        if row is None:
            return False
        access_name = (
            str(row["client_name"])
            if bool(row["is_primary"])
            else f"{row['client_name']} · {row['device_name']}"
        )
        existing = connection.execute(
            """
            SELECT id FROM device_credentials
            WHERE device_id = ? AND engine = 'mihomo'
            """,
            (device_id,),
        ).fetchone()
        if existing:
            connection.execute(
                """
                UPDATE device_credentials SET status = 'generated'
                WHERE device_id = ? AND engine = 'mihomo'
                """,
                (device_id,),
            )
            return True
        object_id, config_json = build_client_credentials(device_id, access_name)
        connection.execute(
            """
            INSERT INTO device_credentials (
                device_id, engine, status, engine_object_id, config_json
            ) VALUES (?, 'mihomo', 'generated', ?, ?)
            """,
            (device_id, object_id, config_json),
        )
    log_operation(
        "mihomo.device.enable",
        f"device:{device_id}",
        "Подготовлены Mieru, AnyTLS и TUIC credentials",
    )
    return True


def ensure_client_deployment(client_id: int) -> bool:
    device = get_primary_device(client_id)
    return ensure_device_deployment(device.id) if device else False


def disable_device_deployment(device_id: int) -> bool:
    init_db()
    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE device_credentials SET status = 'disabled'
            WHERE device_id = ? AND engine = 'mihomo'
            """,
            (device_id,),
        )
    if cursor.rowcount:
        log_operation(
            "mihomo.device.disable", f"device:{device_id}", "Mihomo-доступ отключён"
        )
        return True
    return False


def disable_client_deployment(client_id: int) -> bool:
    device = get_primary_device(client_id)
    return disable_device_deployment(device.id) if device else False


def rotate_device_credentials(device_id: int) -> bool:
    init_db()
    with connect() as connection:
        row = connection.execute(
            """
            SELECT d.id, d.name AS device_name, d.is_primary, c.name AS client_name
            FROM devices d JOIN clients c ON c.id = d.client_id
            WHERE d.id = ?
            """,
            (device_id,),
        ).fetchone()
        if row is None:
            return False
        access_name = (
            str(row["client_name"])
            if bool(row["is_primary"])
            else f"{row['client_name']} · {row['device_name']}"
        )
        object_id, config_json = build_client_credentials(device_id, access_name)
        cursor = connection.execute(
            """
            UPDATE device_credentials
            SET status = 'generated', engine_object_id = ?, config_json = ?,
                rotated_at = CURRENT_TIMESTAMP
            WHERE device_id = ? AND engine = 'mihomo'
            """,
            (object_id, config_json, device_id),
        )
        if cursor.rowcount == 0:
            connection.execute(
                """
                INSERT INTO device_credentials (
                    device_id, engine, status, engine_object_id, config_json
                ) VALUES (?, 'mihomo', 'generated', ?, ?)
                """,
                (device_id, object_id, config_json),
            )
    log_operation(
        "mihomo.device.rotate", f"device:{device_id}", "Mihomo credentials перевыпущены"
    )
    return True


def rotate_client_credentials(client_id: int) -> bool:
    device = get_primary_device(client_id)
    return rotate_device_credentials(device.id) if device else False


def list_active_deployments() -> list[MihomoDeployment]:
    init_db()
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT d.id AS device_id, d.name AS device_name, d.is_primary,
                   c.name AS client_name, dc.status, dc.config_json
            FROM devices d
            JOIN clients c ON c.id = d.client_id
            JOIN device_credentials dc
              ON dc.device_id = d.id AND dc.engine = 'mihomo'
            WHERE c.enabled = 1 AND d.enabled = 1
              AND dc.status IN (
                'creating','checking','applying','pending',
                'generated','applied','error'
              )
            ORDER BY d.id
            """
        ).fetchall()
    deployments: list[MihomoDeployment] = []
    for row in rows:
        try:
            config = json.loads(row["config_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        access_name = (
            str(row["client_name"])
            if bool(row["is_primary"])
            else f"{row['client_name']} · {row['device_name']}"
        )
        deployments.append(
            MihomoDeployment(
                client_id=int(row["device_id"]),
                client_name=access_name,
                enabled=True,
                config=config,
            )
        )
    return deployments



_PLACEHOLDER_HOSTS = {
    "",
    "0.0.0.0",
    "127.0.0.1",
    "localhost",
    "vpn.example.com",
    "configured-endpoint",
    "server_ip",
}


def _usable_host(value: str) -> bool:
    host = (value or "").strip().lower().rstrip(".")
    if host in _PLACEHOLDER_HOSTS:
        return False
    if host.endswith(".example.com") or host.endswith(".example"):
        return False
    return True


def _endpoint_metadata() -> dict[str, str]:
    tls = _tls_state()
    domain = str(tls.get("domain") or "").strip().lower().rstrip(".")

    candidates = []
    for engine in ("xray", "amneziawg", "mihomo"):
        try:
            settings = get_connection_settings(engine)
        except Exception:
            continue
        host = str(settings.host or "").strip()
        if _usable_host(host):
            candidates.append((engine, host))

    public_ip = ""
    source = ""
    raw_host = ""
    for engine, host in candidates:
        resolved = resolve_host_ip(host)
        if resolved:
            public_ip = resolved
            source = engine
            raw_host = host
            break

    endpoint = domain if domain else (public_ip or raw_host)
    country_code = lookup_country_code(public_ip or raw_host or endpoint)

    return {
        "host": endpoint,
        "public_ip": public_ip,
        "domain": domain,
        "country_code": country_code,
        "endpoint_source": (
            "Security HTTPS"
            if domain
            else ("Текущий сервер" if public_ip else "Не определён")
        ),
        "country_source": (
            "Активный geoip.dat"
            if country_code != "unknown"
            else "Страна не определена"
        ),
        "source_engine": source,
    }


def refresh_endpoint_metadata() -> dict[str, str]:
    metadata = _endpoint_metadata()
    for engine in ("amneziawg", "xray", "mihomo"):
        settings = get_connection_settings(engine)
        config = dict(settings.config)
        config["country_code"] = metadata["country_code"]
        if engine == "mihomo":
            config["domain"] = metadata["domain"]
            host = metadata["host"] or settings.host
            port = _int(config.get("mieru_port"), settings.port or 2099)
        else:
            host = settings.host
            port = settings.port
        update_connection_settings(engine, host, port, config)
    return metadata

def save_settings(form: Any) -> bool:
    current = get_connection_settings("mihomo")
    config = dict(current.config)
    metadata = _endpoint_metadata()
    config.update(
        {
            "country_code": metadata["country_code"],
            "domain": metadata["domain"],
            "mieru_enabled": bool(form.get("mieru_enabled")),
            "mieru_port": _int(
                form.get("mieru_port"),
                _int(config.get("mieru_port"), current.port or 2099),
            ),
            "mieru_transport": (
                "UDP"
                if str(form.get("mieru_transport", "TCP")).upper() == "UDP"
                else "TCP"
            ),
            "mieru_multiplexing": str(
                form.get(
                    "mieru_multiplexing",
                    config.get("mieru_multiplexing", "MULTIPLEXING_LOW"),
                )
            ),
            "mieru_handshake": str(
                form.get(
                    "mieru_handshake",
                    config.get("mieru_handshake", "HANDSHAKE_STANDARD"),
                )
            ),
            "mieru_user_hint_mandatory": bool(
                form.get("mieru_user_hint_mandatory")
            ),
            "anytls_enabled": bool(form.get("anytls_enabled")),
            "anytls_port": _int(
                form.get("anytls_port"),
                _int(config.get("anytls_port"), 8443),
            ),
            "anytls_padding_scheme": str(
                form.get(
                    "anytls_padding_scheme",
                    config.get("anytls_padding_scheme", ""),
                )
            ),
            "tuic_enabled": bool(form.get("tuic_enabled")),
            "tuic_port": _int(
                form.get("tuic_port"),
                _int(config.get("tuic_port"), 10443),
            ),
            "tuic_congestion_controller": str(
                form.get(
                    "tuic_congestion_controller",
                    config.get("tuic_congestion_controller", "bbr"),
                )
            ),
            "tuic_udp_relay_mode": str(
                form.get(
                    "tuic_udp_relay_mode",
                    config.get("tuic_udp_relay_mode", "native"),
                )
            ),
            "tuic_alpn": str(
                form.get("tuic_alpn", config.get("tuic_alpn", "h3"))
            ).strip()
            or "h3",
        }
    )
    host = metadata["host"] or current.host
    return update_connection_settings(
        "mihomo",
        host,
        config["mieru_port"],
        config,
    )

def _settings_payload() -> dict[str, Any]:
    settings = get_connection_settings("mihomo")
    config = dict(settings.config)
    metadata = _endpoint_metadata()
    domain = metadata["domain"]
    host = metadata["host"] or settings.host
    country_code = metadata["country_code"]
    return {
        "enabled": bool(settings.enabled),
        "host": host,
        "server_ip": metadata["public_ip"],
        "country_code": country_code,
        "country_source": metadata["country_source"],
        "endpoint_source": metadata["endpoint_source"],
        "domain": domain,
        "tls_ready": _tls_ready(domain),
        "mieru_enabled": _bool(config.get("mieru_enabled", True)),
        "mieru_port": _int(config.get("mieru_port"), settings.port or 2099),
        "mieru_transport": (
            "UDP"
            if str(config.get("mieru_transport", "TCP")).upper() == "UDP"
            else "TCP"
        ),
        "mieru_multiplexing": str(
            config.get("mieru_multiplexing", "MULTIPLEXING_LOW")
        ),
        "mieru_handshake": str(
            config.get("mieru_handshake", "HANDSHAKE_STANDARD")
        ),
        "mieru_user_hint_mandatory": _bool(
            config.get("mieru_user_hint_mandatory", True)
        ),
        "anytls_enabled": _bool(config.get("anytls_enabled", False)),
        "anytls_port": _int(config.get("anytls_port"), 8443),
        "anytls_padding_scheme": str(config.get("anytls_padding_scheme", "")),
        "tuic_enabled": _bool(config.get("tuic_enabled", False)),
        "tuic_port": _int(config.get("tuic_port"), 10443),
        "tuic_congestion_controller": str(
            config.get("tuic_congestion_controller", "bbr")
        ),
        "tuic_udp_relay_mode": str(
            config.get("tuic_udp_relay_mode", "native")
        ),
        "tuic_alpn": str(config.get("tuic_alpn", "h3")),
    }

def _validate_settings(settings: dict[str, Any], user_count: int) -> None:
    ports = []
    if settings["mieru_enabled"]:
        ports.append(("Mieru", settings["mieru_port"]))
    if settings["anytls_enabled"]:
        ports.append(("AnyTLS", settings["anytls_port"]))
    if settings["tuic_enabled"]:
        ports.append(("TUIC", settings["tuic_port"]))
    if not ports:
        raise MihomoError("Включите хотя бы один Mihomo listener")
    if len({port for _, port in ports}) != len(ports):
        raise MihomoError("Порты Mieru, AnyTLS и TUIC должны различаться")

    awg = get_connection_settings("amneziawg")
    xray = get_connection_settings("xray")
    tcp_reserved = {
        80: "Nginx HTTP / ACME",
        443: "Nginx HTTPS",
        int(load_config().public_port): "SG-Gateway panel",
        int(xray.port): "Xray",
    }
    udp_reserved = {int(awg.port): "AmneziaWG"}
    requested: list[tuple[str, str, int]] = []
    if settings["mieru_enabled"]:
        requested.append(
            ("Mieru", settings["mieru_transport"], settings["mieru_port"])
        )
    if settings["anytls_enabled"]:
        requested.append(("AnyTLS", "TCP", settings["anytls_port"]))
    if settings["tuic_enabled"]:
        requested.append(("TUIC", "UDP", settings["tuic_port"]))
    for label, transport, port in requested:
        reserved = tcp_reserved if transport == "TCP" else udp_reserved
        conflict = reserved.get(port)
        if conflict:
            raise MihomoError(
                f"{label}: порт {port}/{transport} уже используется: {conflict}"
            )
    if user_count < 1:
        raise MihomoError(
            "Нет активных клиентов Mihomo. Сначала включите Mihomo-доступ "
            "хотя бы для одного клиента."
        )
    if (settings["anytls_enabled"] or settings["tuic_enabled"]) and not settings[
        "tls_ready"
    ]:
        raise MihomoError(
            "AnyTLS и TUIC требуют готового сертификата из раздела Security"
        )
    if settings["mieru_multiplexing"] not in {
        "MULTIPLEXING_OFF",
        "MULTIPLEXING_LOW",
        "MULTIPLEXING_MIDDLE",
        "MULTIPLEXING_HIGH",
    }:
        raise MihomoError("Некорректный режим multiplexing Mieru")
    if settings["mieru_handshake"] not in {
        "HANDSHAKE_STANDARD",
        "HANDSHAKE_NO_WAIT",
    }:
        raise MihomoError("Некорректный handshake mode Mieru")
    if settings["tuic_congestion_controller"] not in {
        "bbr",
        "cubic",
        "new_reno",
    }:
        raise MihomoError("Некорректный congestion controller TUIC")
    if settings["tuic_udp_relay_mode"] not in {"native", "quic"}:
        raise MihomoError("Некорректный UDP relay mode TUIC")


def _render_server_yaml(
    settings: dict[str, Any],
    deployments: list[MihomoDeployment],
) -> str:
    listeners: list[str] = []

    if settings["mieru_enabled"]:
        lines = [
            "  - name: mieru-in",
            "    type: mieru",
            f"    port: {settings['mieru_port']}",
            "    listen: 0.0.0.0",
            f"    transport: {settings['mieru_transport']}",
            "    users:",
        ]
        for deployment in deployments:
            item = deployment.config["mieru"]
            lines.append(
                f"      {_yaml_string(item['username'])}: "
                f"{_yaml_string(item['password'])}"
            )
        lines.append(
            "    user-hint-is-mandatory: "
            + ("true" if settings["mieru_user_hint_mandatory"] else "false")
        )
        listeners.append("\n".join(lines))

    if settings["anytls_enabled"]:
        lines = [
            "  - name: anytls-in",
            "    type: anytls",
            f"    port: {settings['anytls_port']}",
            "    listen: 0.0.0.0",
            "    users:",
        ]
        for deployment in deployments:
            item = deployment.config["anytls"]
            lines.append(
                f"      {_yaml_string(item['label'])}: "
                f"{_yaml_string(item['password'])}"
            )
        lines.extend(
            [
                "    certificate: /etc/mihomo/tls/fullchain.pem",
                "    private-key: /etc/mihomo/tls/privkey.pem",
            ]
        )
        if settings["anytls_padding_scheme"]:
            lines.append(
                "    padding-scheme: "
                + _yaml_string(settings["anytls_padding_scheme"])
            )
        listeners.append("\n".join(lines))

    if settings["tuic_enabled"]:
        lines = [
            "  - name: tuicv5-in",
            "    type: tuic",
            f"    port: {settings['tuic_port']}",
            "    listen: 0.0.0.0",
            "    users:",
        ]
        for deployment in deployments:
            item = deployment.config["tuic"]
            lines.append(
                f"      {_yaml_string(item['uuid'])}: "
                f"{_yaml_string(item['password'])}"
            )
        lines.extend(
            [
                "    certificate: /etc/mihomo/tls/fullchain.pem",
                "    private-key: /etc/mihomo/tls/privkey.pem",
                f"    alpn: [{_yaml_string(settings['tuic_alpn'])}]",
                "    congestion-controller: "
                + _yaml_string(settings["tuic_congestion_controller"]),
            ]
        )
        listeners.append("\n".join(lines))

    return "\n".join(
        [
            "# Managed by SG-Gateway. Do not edit by hand.",
            "mode: rule",
            "log-level: info",
            "ipv6: true",
            "allow-lan: false",
            "listeners:",
            *listeners,
            "rules:",
            "  - MATCH,DIRECT",
            "",
        ]
    )


def build_candidate() -> dict[str, Any]:
    _ensure_dirs()
    settings = _settings_payload()
    deployments = list_active_deployments()
    _validate_settings(settings, len(deployments))
    body = _render_server_yaml(settings, deployments)
    MIHOMO_CANDIDATE.write_text(body, encoding="utf-8", newline="\n")
    os.chmod(MIHOMO_CANDIDATE, 0o640)
    metadata = {
        "created_at": _now(),
        "settings": settings,
        "client_count": len(deployments),
        "protocols": [
            protocol
            for protocol in PROTOCOLS
            if settings[f"{protocol}_enabled"]
        ],
    }
    MIHOMO_CANDIDATE_META.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(MIHOMO_CANDIDATE_META, 0o640)
    log_operation(
        "mihomo.candidate",
        "mihomo:runtime",
        (
            f"Подготовлен candidate: {len(deployments)} клиентов; "
            f"{', '.join(metadata['protocols'])}"
        ),
    )
    return metadata


def _run_helper(action: str) -> dict[str, Any]:
    command = f"mihomo.{action}"
    result = run_hostd_command(command, timeout=180)
    if result.status != "ok":
        raise MihomoError(result.message or f"{command} failed")

    payload = dict(result.payload)
    payload.setdefault("ok", True)
    payload.setdefault("message", result.message)
    return payload


def apply_candidate() -> dict[str, Any]:
    build_candidate()
    payload = _run_helper("apply")
    log_operation(
        "mihomo.apply",
        "mihomo:runtime",
        str(payload.get("message", "Mihomo configuration applied")),
    )
    return payload


def rollback_latest() -> dict[str, Any]:
    payload = _run_helper("rollback")
    log_operation(
        "mihomo.rollback",
        "mihomo:runtime",
        str(payload.get("message", "Mihomo configuration restored")),
    )
    return payload


def restart_service() -> dict[str, Any]:
    payload = _run_helper("restart")
    log_operation(
        "mihomo.restart",
        "mihomo:runtime",
        str(payload.get("message", "Mihomo restarted")),
    )
    return payload


def test_candidate() -> dict[str, Any]:
    build_candidate()
    return _run_helper("test")


def _service_active() -> bool:
    return (
        subprocess.run(
            ["systemctl", "is-active", "--quiet", "mihomo.service"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def _service_enabled() -> bool:
    return (
        subprocess.run(
            ["systemctl", "is-enabled", "--quiet", "mihomo.service"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def _version() -> str:
    if not MIHOMO_BINARY.is_file():
        return "Не установлен"
    result = subprocess.run(
        [str(MIHOMO_BINARY), "-v"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    first = (result.stdout or result.stderr).strip().splitlines()
    return first[0] if first else "Неизвестно"



def _backup_names() -> list[str]:
    try:
        return [
            item.name
            for item in sorted(MIHOMO_BACKUP_DIR.glob("*"), reverse=True)
            if item.is_dir()
        ][:10]
    except OSError:
        return []

def overview() -> dict[str, Any]:
    _ensure_dirs()
    settings = _settings_payload()
    deployments = list_active_deployments()
    candidate = None
    try:
        candidate = json.loads(MIHOMO_CANDIDATE_META.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    service_active = _service_active()
    service_enabled = _service_enabled()
    protocols = [
        {
            "id": "mieru",
            "label": "Mieru",
            "transport": settings["mieru_transport"],
            "port": settings["mieru_port"],
            "enabled": settings["mieru_enabled"],
            "tls": False,
        },
        {
            "id": "anytls",
            "label": "AnyTLS",
            "transport": "TCP",
            "port": settings["anytls_port"],
            "enabled": settings["anytls_enabled"],
            "tls": True,
        },
        {
            "id": "tuic",
            "label": "TUIC v5",
            "transport": "UDP / QUIC",
            "port": settings["tuic_port"],
            "enabled": settings["tuic_enabled"],
            "tls": True,
        },
    ]
    enabled_count = sum(1 for item in protocols if item["enabled"])
    active_count = enabled_count if service_active and MIHOMO_CONFIG.is_file() else 0
    return {
        "version": _version(),
        "installed": MIHOMO_BINARY.is_file(),
        "service_active": service_active,
        "service_enabled": service_enabled,
        "config_exists": MIHOMO_CONFIG.is_file(),
        "settings": settings,
        "client_count": len(deployments),
        "candidate": candidate,
        "listener_total": len(protocols),
        "listener_enabled": enabled_count,
        "listener_active": active_count,
        "backups": _backup_names(),
        "protocols": protocols,
    }


def health_status() -> dict[str, str]:
    state = overview()
    if not state["installed"]:
        return {
            "status": "idle",
            "message": "Не используется: Mihomo не установлен",
        }
    if not state["service_enabled"] and not state["service_active"]:
        if state["client_count"]:
            return {
                "status": "warning",
                "message": (
                    f"Служба выключена; доступ Mihomo выбран для "
                    f"{state['client_count']} устройств"
                ),
            }
        return {
            "status": "idle",
            "message": "Не используется: служба Mihomo выключена",
        }
    if not state["config_exists"]:
        return {
            "status": "warning",
            "message": "Mihomo включён, но конфигурация ещё не применена",
        }
    if not state["service_active"]:
        return {
            "status": "error",
            "message": "Mihomo включён, но mihomo.service не активен",
        }
    protocols = [
        item["label"] for item in state["protocols"] if item["enabled"]
    ]
    return {
        "status": "ok",
        "message": (
            f"{state['version']}; активны: {', '.join(protocols)}; "
            f"клиентов: {state['client_count']}"
        ),
    }


def build_device_yaml(device_id: int, access_name: str) -> str:
    deployment = _deployment_config(device_id)
    if deployment is None:
        raise MihomoError("Для клиента не подготовлен Mihomo-доступ")
    settings = _settings_payload()
    host = settings["domain"] or settings["host"]
    mieru_host = settings.get("server_ip") or settings["host"]
    safe_name = access_name.replace('"', "").strip() or f"Access {device_id}"
    proxies: list[str] = []
    names: list[str] = []

    if settings["mieru_enabled"]:
        item = deployment["mieru"]
        name = f"{safe_name} · Mieru"
        names.append(name)
        proxies.extend(
            [
                f"  - name: {_yaml_string(name)}",
                "    type: mieru",
                f"    server: {_yaml_string(mieru_host)}",
                f"    port: {settings['mieru_port']}",
                f"    transport: {settings['mieru_transport']}",
                f"    username: {_yaml_string(item['username'])}",
                f"    password: {_yaml_string(item['password'])}",
                f"    multiplexing: {settings['mieru_multiplexing']}",
                f"    handshake-mode: {settings['mieru_handshake']}",
            ]
        )

    if settings["anytls_enabled"]:
        item = deployment["anytls"]
        name = f"{safe_name} · AnyTLS"
        names.append(name)
        proxies.extend(
            [
                f"  - name: {_yaml_string(name)}",
                "    type: anytls",
                f"    server: {_yaml_string(host)}",
                f"    port: {settings['anytls_port']}",
                f"    password: {_yaml_string(item['password'])}",
                "    client-fingerprint: chrome",
                "    udp: true",
                f"    sni: {_yaml_string(settings['domain'])}",
                "    alpn: [h2, http/1.1]",
                "    skip-cert-verify: false",
            ]
        )

    if settings["tuic_enabled"]:
        item = deployment["tuic"]
        name = f"{safe_name} · TUIC"
        names.append(name)
        proxies.extend(
            [
                f"  - name: {_yaml_string(name)}",
                "    type: tuic",
                f"    server: {_yaml_string(host)}",
                f"    port: {settings['tuic_port']}",
                f"    uuid: {_yaml_string(item['uuid'])}",
                f"    password: {_yaml_string(item['password'])}",
                f"    sni: {_yaml_string(settings['domain'])}",
                f"    alpn: [{_yaml_string(settings['tuic_alpn'])}]",
                "    skip-cert-verify: false",
                "    udp-relay-mode: "
                + _yaml_string(settings["tuic_udp_relay_mode"]),
                "    congestion-controller: "
                + _yaml_string(settings["tuic_congestion_controller"]),
            ]
        )

    if not proxies:
        raise MihomoError("Ни один Mihomo-протокол не включён")

    group_names = ", ".join(_yaml_string(name) for name in names)
    return "\n".join(
        [
            "# SG-Gateway Mihomo profile",
            f"# Access: {access_name}",
            "mode: rule",
            "log-level: info",
            "proxies:",
            *proxies,
            "proxy-groups:",
            f"  - name: {_yaml_string('SG-Gateway')}",
            "    type: select",
            f"    proxies: [{group_names}]",
            "rules:",
            "  - MATCH,SG-Gateway",
            "",
        ]
    )


def build_client_yaml(client_id: int, client_name: str) -> str:
    device = get_primary_device(client_id)
    if device is None:
        raise MihomoError("Для клиента не найден основной доступ")
    return build_device_yaml(device.id, client_name)
