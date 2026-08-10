from __future__ import annotations

import ipaddress
import json
import os
import shutil
import subprocess
from pathlib import Path

from sg_hostd import client_runtime as cr


ENGINE = "amneziawg3"
AWG3_PORT = 586
AWG3_CONFIG = Path("/etc/amnezia/amneziawg/awg3.conf")
AWG3_SERVICE = "sg-gateway-awg3.service"
AWG3_SUBNET = "10.67.0.0/16"

AWG3_DEFAULTS = {
    "jc": 4,
    "jmin": 10,
    "jmax": 50,
    "s1": 64,
    "s2": 96,
    "s3": 48,
    "s4": 12,
    "content_padding_addition": "10-100",
    "rekey_after_time": "100-120",
    "rekey_timeout": "3-7",
    "reject_after_time": "150-180",
    "keepalive_timeout": "5-15",
    "max_handshake_attempts": "15-20",
    "persistent_keepalive": "25-35",
}


def _normalise_address(device_id: int, value: str) -> str:
    raw = str(value or "").strip()
    try:
        interface = ipaddress.ip_interface(raw)
        if interface.version == 4 and interface.ip in ipaddress.ip_network(AWG3_SUBNET):
            return str(interface)
    except ValueError:
        pass
    slot = max(1, int(device_id))
    third = min(254, slot // 250)
    fourth = 2 + (slot % 250)
    return f"10.67.{third}.{fourth}/32"


def _derive_public(private_key: str) -> str:
    if not private_key:
        raise cr.ClientRuntimeError("AWG3: отсутствует приватный ключ")
    return cr._run(
        ["awg", "pubkey"],
        input_text=private_key.strip() + "\n",
        timeout=30,
    ).stdout.strip()


def _set_env_values(path: Path, values: dict[str, str]) -> None:
    existing: list[str] = []
    if path.is_file():
        existing = path.read_text(encoding="utf-8").splitlines()
    wanted = dict(values)
    output: list[str] = []
    for line in existing:
        if "=" not in line or line.lstrip().startswith("#"):
            output.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in wanted:
            output.append(f"{key}={wanted.pop(key)}")
        else:
            output.append(line)
    for key, value in wanted.items():
        output.append(f"{key}={value}")
    cr._atomic_write(path, "\n".join(output).rstrip() + "\n", 0o600)


def _ensure_server_secrets() -> dict[str, str]:
    secrets = cr._read_env(cr.ENGINE_SECRETS)
    required = (
        "SG_GATEWAY_AWG3_PRIVATE_KEY",
        "SG_GATEWAY_AWG3_PUBLIC_KEY",
        "SG_GATEWAY_AWG3_HEADER_PROTECTION_KEY",
    )
    if all(str(secrets.get(name) or "").strip() for name in required):
        return secrets

    private_key = cr._run(["awg", "genkey"], timeout=30).stdout.strip()
    public_key = cr._run(
        ["awg", "pubkey"],
        input_text=private_key + "\n",
        timeout=30,
    ).stdout.strip()
    header_key = cr._run(["awg", "genkey"], timeout=30).stdout.strip()
    if not private_key or not public_key or not header_key:
        raise cr.ClientRuntimeError("AWG3: не удалось создать серверные ключи")

    # Reuse only the legacy H1-H4 values. AWG2 keys, subnet, client keys and
    # endpoint remain independent and untouched.
    legacy = cr._awg_obfuscation(secrets)
    values = {
        "SG_GATEWAY_AWG3_PRIVATE_KEY": private_key,
        "SG_GATEWAY_AWG3_PUBLIC_KEY": public_key,
        "SG_GATEWAY_AWG3_HEADER_PROTECTION_KEY": header_key,
        "SG_GATEWAY_AWG3_JC": str(AWG3_DEFAULTS["jc"]),
        "SG_GATEWAY_AWG3_JMIN": str(AWG3_DEFAULTS["jmin"]),
        "SG_GATEWAY_AWG3_JMAX": str(AWG3_DEFAULTS["jmax"]),
        "SG_GATEWAY_AWG3_S1": str(AWG3_DEFAULTS["s1"]),
        "SG_GATEWAY_AWG3_S2": str(AWG3_DEFAULTS["s2"]),
        "SG_GATEWAY_AWG3_S3": str(AWG3_DEFAULTS["s3"]),
        "SG_GATEWAY_AWG3_S4": str(AWG3_DEFAULTS["s4"]),
        "SG_GATEWAY_AWG3_H1": str(legacy["h1"]),
        "SG_GATEWAY_AWG3_H2": str(legacy["h2"]),
        "SG_GATEWAY_AWG3_H3": str(legacy["h3"]),
        "SG_GATEWAY_AWG3_H4": str(legacy["h4"]),
        "SG_GATEWAY_AWG3_CONTENT_PADDING_ADDITION": str(
            AWG3_DEFAULTS["content_padding_addition"]
        ),
        "SG_GATEWAY_AWG3_REKEY_AFTER_TIME": str(AWG3_DEFAULTS["rekey_after_time"]),
        "SG_GATEWAY_AWG3_REKEY_TIMEOUT": str(AWG3_DEFAULTS["rekey_timeout"]),
        "SG_GATEWAY_AWG3_REJECT_AFTER_TIME": str(AWG3_DEFAULTS["reject_after_time"]),
        "SG_GATEWAY_AWG3_KEEPALIVE_TIMEOUT": str(AWG3_DEFAULTS["keepalive_timeout"]),
        "SG_GATEWAY_AWG3_MAX_HANDSHAKE_ATTEMPTS": str(
            AWG3_DEFAULTS["max_handshake_attempts"]
        ),
    }
    _set_env_values(cr.ENGINE_SECRETS, values)
    return cr._read_env(cr.ENGINE_SECRETS)


def _ensure_credentials() -> None:
    """Add a separate AWG3 credential to devices that already have AWG2."""
    settings = cr.get_connection_settings("amneziawg")
    runtime = cr._read_env(cr.RUNTIME_ENV)
    host = str(settings.host or runtime.get("SG_GATEWAY_PUBLIC_ADDRESS") or "").strip()

    with cr.connect() as connection:
        devices = connection.execute(
            """
            SELECT
                d.id AS device_id,
                CASE WHEN d.is_primary = 1 THEN c.name
                     ELSE c.name || ' · ' || d.name END AS client_name
            FROM devices d
            JOIN clients c ON c.id = d.client_id
            JOIN device_credentials awg2
              ON awg2.device_id = d.id AND awg2.engine = 'amneziawg'
            LEFT JOIN device_credentials awg3
              ON awg3.device_id = d.id AND awg3.engine = 'amneziawg3'
            WHERE awg3.id IS NULL
            ORDER BY d.id
            """
        ).fetchall()

        for row in devices:
            device_id = int(row["device_id"])
            private_key = cr._run(["awg", "genkey"], timeout=30).stdout.strip()
            public_key = cr._run(
                ["awg", "pubkey"],
                input_text=private_key + "\n",
                timeout=30,
            ).stdout.strip()
            config = {
                "client_name": str(row["client_name"]),
                "private_key": private_key,
                "public_key": public_key,
                "address": _normalise_address(device_id, ""),
                "dns": settings.config.get("dns", "1.1.1.1"),
                "endpoint": f"{host}:{AWG3_PORT}",
                "allowed_ips": settings.config.get(
                    "allowed_ips",
                    "0.0.0.0/0, ::/0",
                ),
                "persistent_keepalive": AWG3_DEFAULTS["persistent_keepalive"],
                "generation": 3,
            }
            connection.execute(
                """
                INSERT INTO device_credentials (
                    device_id, engine, status, engine_object_id, config_json
                )
                VALUES (?, 'amneziawg3', 'creating', ?, ?)
                """,
                (
                    device_id,
                    public_key,
                    json.dumps(config, ensure_ascii=False, sort_keys=True),
                ),
            )


def _values(secrets: dict[str, str]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name in ("jc", "jmin", "jmax", "s1", "s2", "s3", "s4", "h1", "h2", "h3", "h4"):
        env = f"SG_GATEWAY_AWG3_{name.upper()}"
        raw = str(secrets.get(env) or "").strip()
        try:
            result[name] = int(raw)
        except ValueError as exc:
            raise cr.ClientRuntimeError(f"AWG3: некорректный параметр {env}") from exc

    if not 1 <= int(result["jc"]) <= 128:
        raise cr.ClientRuntimeError("AWG3: Jc вне допустимого диапазона")
    if not 1 <= int(result["jmin"]) <= int(result["jmax"]) <= 1280:
        raise cr.ClientRuntimeError("AWG3: Jmin/Jmax заданы некорректно")
    headers = [int(result[f"h{i}"]) for i in range(1, 5)]
    if any(value <= 0 for value in headers) or len(set(headers)) != 4:
        raise cr.ClientRuntimeError("AWG3: H1-H4 должны быть положительными и уникальными")

    result.update(
        {
            "header_protection_key": str(
                secrets.get("SG_GATEWAY_AWG3_HEADER_PROTECTION_KEY") or ""
            ).strip(),
            "content_padding_addition": str(
                secrets.get("SG_GATEWAY_AWG3_CONTENT_PADDING_ADDITION")
                or AWG3_DEFAULTS["content_padding_addition"]
            ).strip(),
            "rekey_after_time": str(
                secrets.get("SG_GATEWAY_AWG3_REKEY_AFTER_TIME")
                or AWG3_DEFAULTS["rekey_after_time"]
            ).strip(),
            "rekey_timeout": str(
                secrets.get("SG_GATEWAY_AWG3_REKEY_TIMEOUT")
                or AWG3_DEFAULTS["rekey_timeout"]
            ).strip(),
            "reject_after_time": str(
                secrets.get("SG_GATEWAY_AWG3_REJECT_AFTER_TIME")
                or AWG3_DEFAULTS["reject_after_time"]
            ).strip(),
            "keepalive_timeout": str(
                secrets.get("SG_GATEWAY_AWG3_KEEPALIVE_TIMEOUT")
                or AWG3_DEFAULTS["keepalive_timeout"]
            ).strip(),
            "max_handshake_attempts": str(
                secrets.get("SG_GATEWAY_AWG3_MAX_HANDSHAKE_ATTEMPTS")
                or AWG3_DEFAULTS["max_handshake_attempts"]
            ).strip(),
        }
    )
    if not result["header_protection_key"]:
        raise cr.ClientRuntimeError("AWG3: HeaderProtectionKey отсутствует")
    return result


def _repair_configs(secrets: dict[str, str]) -> None:
    settings = cr.get_connection_settings("amneziawg")
    runtime = cr._read_env(cr.RUNTIME_ENV)
    public_address = str(runtime.get("SG_GATEWAY_PUBLIC_ADDRESS") or "").strip()
    server_public = str(secrets.get("SG_GATEWAY_AWG3_PUBLIC_KEY") or "").strip()
    values = _values(secrets)

    with cr.connect() as connection:
        rows = connection.execute(
            """
            SELECT
                d.id AS device_id,
                CASE WHEN d.is_primary = 1 THEN c.name
                     ELSE c.name || ' · ' || d.name END AS client_name,
                dc.config_json
            FROM devices d
            JOIN clients c ON c.id = d.client_id
            JOIN device_credentials dc
              ON dc.device_id = d.id AND dc.engine = 'amneziawg3'
            ORDER BY d.id
            """
        ).fetchall()

        for row in rows:
            device_id = int(row["device_id"])
            config = cr._json(row["config_json"])
            private_key = str(config.get("private_key") or "").strip()
            public_key = _derive_public(private_key)
            config.update(
                {
                    "client_name": str(row["client_name"]),
                    "private_key": private_key,
                    "public_key": public_key,
                    "address": _normalise_address(
                        device_id,
                        str(config.get("address") or ""),
                    ),
                    "dns": settings.config.get("dns", "1.1.1.1"),
                    "server_public_key": server_public,
                    "endpoint": (
                        f"{settings.host or public_address}:{AWG3_PORT}"
                    ),
                    "port": AWG3_PORT,
                    "allowed_ips": settings.config.get(
                        "allowed_ips",
                        "0.0.0.0/0, ::/0",
                    ),
                    "persistent_keepalive": AWG3_DEFAULTS["persistent_keepalive"],
                    "generation": 3,
                    **values,
                }
            )
            connection.execute(
                """
                UPDATE device_credentials
                SET engine_object_id = ?, config_json = ?
                WHERE device_id = ? AND engine = 'amneziawg3'
                """,
                (
                    public_key,
                    json.dumps(config, ensure_ascii=False, sort_keys=True),
                    device_id,
                ),
            )


def _render(rows, secrets: dict[str, str]) -> str:
    server_private = str(secrets.get("SG_GATEWAY_AWG3_PRIVATE_KEY") or "").strip()
    if not server_private:
        raise cr.ClientRuntimeError("AWG3: серверный приватный ключ отсутствует")
    values = _values(secrets)
    external_interface = cr._default_interface()

    lines = [
        "[Interface]",
        "Address = 10.67.0.1/16",
        f"ListenPort = {AWG3_PORT}",
        f"PrivateKey = {server_private}",
        f"Jc = {values['jc']}",
        f"Jmin = {values['jmin']}",
        f"Jmax = {values['jmax']}",
        f"S1 = {values['s1']}",
        f"S2 = {values['s2']}",
        f"S3 = {values['s3']}",
        f"S4 = {values['s4']}",
        f"H1 = {values['h1']}",
        f"H2 = {values['h2']}",
        f"H3 = {values['h3']}",
        f"H4 = {values['h4']}",
        f"HeaderProtectionKey = {values['header_protection_key']}",
        f"ContentPaddingAddition = {values['content_padding_addition']}",
        f"RekeyAfterTime = {values['rekey_after_time']}",
        f"RekeyTimeout = {values['rekey_timeout']}",
        f"RejectAfterTime = {values['reject_after_time']}",
        f"KeepaliveTimeout = {values['keepalive_timeout']}",
        f"MaxHandshakeAttempts = {values['max_handshake_attempts']}",
        (
            "PostUp = "
            "nft delete table ip sg_gateway_awg3 2>/dev/null || true; "
            "nft add table ip sg_gateway_awg3; "
            "nft 'add chain ip sg_gateway_awg3 forward "
            "{ type filter hook forward priority filter; policy accept; }'; "
            "nft 'add chain ip sg_gateway_awg3 postrouting "
            "{ type nat hook postrouting priority srcnat; policy accept; }'; "
            f'nft add rule ip sg_gateway_awg3 postrouting '
            f'oifname "{external_interface}" ip saddr 10.67.0.0/16 masquerade'
        ),
        "PostDown = nft delete table ip sg_gateway_awg3 2>/dev/null || true",
        "",
    ]

    for row in rows:
        config = cr._json(row["config_json"])
        public_key = str(config.get("public_key") or "").strip()
        address = _normalise_address(
            int(row["client_id"]),
            str(config.get("address") or ""),
        )
        if not public_key:
            raise cr.ClientRuntimeError(
                f"AWG3: отсутствует public key клиента {row['client_name']}"
            )
        peer_ip = str(ipaddress.ip_interface(address).ip)
        lines.extend(
            [
                "[Peer]",
                f"# {row['client_name']} · device {row['client_id']}",
                f"PublicKey = {public_key}",
                f"AllowedIPs = {peer_ip}/32",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _runtime_valid() -> bool:
    return bool(
        AWG3_CONFIG.is_file()
        and cr._command_ok(["awg-quick", "strip", str(AWG3_CONFIG)], 30)
        and cr._command_ok(
            ["systemctl", "is-active", "--quiet", AWG3_SERVICE],
            30,
        )
        and cr._udp_port_listening(AWG3_PORT)
    )


def apply_awg3() -> cr.EngineResult:
    # Persistent provisioning is intentionally NOT done here.
    # install.sh/updater owns persistent service and network provisioning.
    _ensure_credentials()
    secrets = _ensure_server_secrets()
    _repair_configs(secrets)

    rows = cr._deployment_rows(ENGINE)
    ids = [int(row["client_id"]) for row in rows]
    previous = cr._status_snapshot(ENGINE)

    if not rows:
        subprocess.run(
            ["systemctl", "stop", AWG3_SERVICE],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        inactive = not cr._command_ok(
            ["systemctl", "is-active", "--quiet", AWG3_SERVICE],
            30,
        )
        if not inactive:
            return cr.EngineResult(
                ENGINE,
                False,
                "AWG3: runtime остался активен без клиентов",
                0,
            )
        return cr.EngineResult(ENGINE, True, "Нет активных клиентов AWG3", 0)

    candidate = cr.CANDIDATE_DIR / "awg3.conf"
    backup = AWG3_CONFIG.with_suffix(".conf.previous")
    try:
        cr._set_engine_status(ENGINE, ids, "checking")
        body = _render(rows, secrets)
        cr._atomic_write(candidate, body, 0o600)
        cr._run(["awg-quick", "strip", str(candidate)], timeout=30)

        cr._set_engine_status(ENGINE, ids, "applying")
        AWG3_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        if AWG3_CONFIG.is_file():
            shutil.copy2(AWG3_CONFIG, backup)
        cr._atomic_write(AWG3_CONFIG, body, 0o600)

        cr._run(["systemctl", "restart", AWG3_SERVICE], timeout=90)
        cr._run(["systemctl", "is-active", "--quiet", AWG3_SERVICE], timeout=30)
        if not cr._udp_port_listening(AWG3_PORT):
            raise cr.ClientRuntimeError("AWG3: UDP 586 не слушается после запуска")

        cr._set_engine_status(ENGINE, ids, "applied")
        return cr.EngineResult(
            ENGINE,
            True,
            f"AmneziaWG 3.0 применён; клиентов: {len(rows)}",
            len(rows),
        )
    except Exception as exc:
        if backup.is_file():
            shutil.copy2(backup, AWG3_CONFIG)
            subprocess.run(
                ["systemctl", "restart", AWG3_SERVICE],
                capture_output=True,
                text=True,
                check=False,
            )
        restored = _runtime_valid()
        cr._set_failure_status(
            ENGINE,
            ids,
            previous,
            runtime_restored=restored,
        )
        return cr.EngineResult(ENGINE, False, f"AWG3: {exc}", len(rows))
