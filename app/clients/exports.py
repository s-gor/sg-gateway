from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from urllib.parse import quote, urlencode

from app.clients.repository import (
    Client,
    Device,
    get_primary_device,
    list_client_deployments,
    list_device_credentials,
)
from app.connections.settings import get_connection_settings
from app.mihomo.service import build_device_yaml

from app.security.tls import overview as tls_overview
from app.xray.profiles import REALITY_TCP_FLOW, overview as xray_profiles_overview
from app.xray.sg_panel_vless import reality_tcp_link, xhttp_reality_link
from app.xray.settings_transactions import pending as pending_settings_transaction


@dataclass(frozen=True)
class ClientExport:
    filename: str
    media_type: str
    body: str


def _resolve_device(client: Client, device: Device | None) -> Device | None:
    return device if device is not None else get_primary_device(client.id)


def _deployments(client: Client, device: Device | None = None) -> dict:
    # Keep the legacy primary wrapper here: several existing extension tests
    # monkeypatch list_client_deployments and must continue to work.
    rows = (
        list_device_credentials(device.id)
        if device is not None
        else list_client_deployments(client.id)
    )
    return {item.engine: item for item in rows}


def _deployment_config(
    client: Client,
    engine: str,
    device: Device | None = None,
) -> dict:
    deployment = _deployments(client, device).get(engine)
    if deployment is None or not deployment.config_json:
        return {}
    try:
        value = json.loads(deployment.config_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _label(client: Client, device: Device | None) -> str:
    if device is None or device.is_primary:
        return client.name
    return f"{client.name} · {device.name}"


def _slug(client: Client, device: Device | None) -> str:
    return f"{client.id}" if device is None else f"{client.id}-device-{device.id}"


def is_export_ready(
    client: Client,
    engine: str,
    device: Device | None = None,
) -> bool:
    resolved = _resolve_device(client, device)
    deployment = _deployments(client, device).get(engine)
    return bool(
        client.enabled
        and (resolved is None or resolved.enabled)
        and deployment is not None
        and deployment.status == "applied"
    )


def _selected_xray_profiles(
    client: Client,
    device: Device | None = None,
) -> list[str]:
    config = _deployment_config(client, "xray", device)
    selected = config.get("profiles")
    if isinstance(selected, list):
        result = [str(item) for item in selected if str(item).strip()]
        if result:
            return result
    return ["reality_tcp", "xhttp_reality"]


def build_awg_config(client: Client, device: Device | None = None) -> ClientExport:
    config = _deployment_config(client, "amneziawg", device)
    label = _label(client, device)
    body = f"""# SG-Gateway AmneziaWG
# Access: {label}

[Interface]
PrivateKey = {config.get("private_key", "")}
Address = {config.get("address", "")}
DNS = {config.get("dns", "1.1.1.1")}
Jc = {config.get("jc", "")}
Jmin = {config.get("jmin", "")}
Jmax = {config.get("jmax", "")}
S1 = {config.get("s1", "")}
S2 = {config.get("s2", "")}
H1 = {config.get("h1", "")}
H2 = {config.get("h2", "")}
H3 = {config.get("h3", "")}
H4 = {config.get("h4", "")}

[Peer]
PublicKey = {config.get("server_public_key", "")}
Endpoint = {config.get("endpoint", "")}
AllowedIPs = {config.get("allowed_ips", "0.0.0.0/0, ::/0")}
PersistentKeepalive = {config.get("persistent_keepalive", 25)}
"""
    return ClientExport(
        filename=f"sg-gateway-{_slug(client, device)}-amneziawg.conf",
        media_type="text/plain; charset=utf-8",
        body=body,
    )


def _xray_profile(profile_id: str):
    state = xray_profiles_overview()
    return state, next(
        (item for item in state["profiles"] if item.id == profile_id),
        None,
    )


def build_xray_profile_link(
    client: Client,
    profile_id: str,
    device: Device | None = None,
) -> ClientExport:
    config = _deployment_config(client, "xray", device)
    selected = _selected_xray_profiles(client, device)
    state, profile = _xray_profile(profile_id)
    filename = f"sg-gateway-{_slug(client, device)}-{profile_id}.txt"
    if profile is None or profile_id not in selected:
        return ClientExport(filename, "text/plain; charset=utf-8", "")

    safe_name = quote(f"{_label(client, device)} · {profile.title}", safe="")
    # SG-Panel contract: the access stores the UUID/profile selection, while
    # every server-dependent value comes from the current server state. This
    # prevents old client rows from exporting links for rotated/stale keys.
    current = get_connection_settings("xray")
    current_config = dict(current.config)
    current_host = str(current.host or "")
    pending = pending_settings_transaction("xray")
    if pending is not None:
        # While a candidate is being tested/applied, public links must remain
        # compatible with the still-live configuration. The candidate becomes
        # visible only after the runtime commits the transaction.
        current_config = dict(pending.previous_config)
        current_host = str(pending.previous_host or "")
        enabled_key = {
            "reality_tcp": "reality_tcp_enabled",
            "xhttp_reality": "xhttp_reality_enabled",
            "xhttp_tls": "xhttp_tls_enabled",
            "hysteria2": "hysteria2_enabled",
        }.get(profile_id, "")
        if enabled_key and not bool(current_config.get(enabled_key, profile_id in {"reality_tcp", "xhttp_reality"})):
            return ClientExport(filename, "text/plain; charset=utf-8", "")
        port_key = {
            "reality_tcp": "reality_tcp_port",
            "xhttp_reality": "xhttp_reality_port",
            "xhttp_tls": "xhttp_tls_port",
            "hysteria2": "hysteria2_port",
        }.get(profile_id, "")
        path_key = {
            "xhttp_reality": "xhttp_reality_path",
            "xhttp_tls": "xhttp_tls_path",
        }.get(profile_id, "")
        mode_key = {
            "xhttp_reality": "xhttp_reality_mode",
            "xhttp_tls": "xhttp_tls_mode",
        }.get(profile_id, "")
        xmux_key = {
            "xhttp_reality": "xhttp_reality_xmux_enabled",
            "xhttp_tls": "xhttp_tls_xmux_enabled",
        }.get(profile_id, "")
        if port_key:
            legacy_default = pending.previous_port if profile_id == "reality_tcp" else profile.port
            profile = type("AppliedProfile", (), {
                "id": profile.id,
                "title": profile.title,
                "port": int(current_config.get(port_key) or legacy_default),
                "path": str(current_config.get(path_key) or profile.path) if path_key else "",
                "mode": str(current_config.get(mode_key) or getattr(profile, "mode", "")) if mode_key else "",
                "xmux_enabled": True if xmux_key else False,
                "xmux": getattr(profile, "xmux", None),
            })()

    def usable(value: object) -> bool:
        text = str(value or "").strip()
        return bool(text) and "PLACEHOLDER" not in text.upper()

    current_ready = bool(
        usable(current.host)
        and usable(current_config.get("public_key"))
        and usable(current_config.get("short_id"))
    )
    server_config = current_config if current_ready else config
    host = str(
        (current_host if current_ready else "")
        or config.get("host")
        or state.get("host")
        or ""
    )
    user_id = str(config.get("uuid") or "")
    fingerprint = str(server_config.get("fingerprint") or "firefox")
    server_name = str(server_config.get("server_name") or "bing.com")
    public_key = str(server_config.get("public_key") or "")
    short_id = str(server_config.get("short_id") or "")
    vless_encryption = str(server_config.get("vless_encryption") or "").strip()

    if profile_id == "reality_tcp":
        body = reality_tcp_link(
            uuid=user_id,
            host=host,
            port=profile.port,
            title=f"{_label(client, device)} · {profile.title}",
            fingerprint=fingerprint,
            server_name=server_name,
            public_key=public_key,
            short_id=short_id,
        )
    elif profile_id == "xhttp_reality":
        if not vless_encryption or "PLACEHOLDER" in vless_encryption.upper():
            body = ""
        else:
            body = xhttp_reality_link(
                uuid=user_id,
                host=host,
                port=profile.port,
                title=f"{_label(client, device)} · {profile.title}",
                fingerprint=fingerprint,
                server_name=server_name,
                public_key=public_key,
                short_id=short_id,
                path=profile.path,
                encryption=vless_encryption,
                client_mode=getattr(profile, "mode", "") or "stream-one",
                xmux=(
                    getattr(profile, "xmux", None)
                    if getattr(profile, "xmux_enabled", False)
                    else None
                ),
            )
    elif profile_id == "xhttp_tls":
        domain = str(state.get("tls_domain") or "")
        if not vless_encryption or "PLACEHOLDER" in vless_encryption.upper():
            body = ""
        else:
            query_values = {
                    "type": "xhttp",
                    "security": "tls",
                    "flow": REALITY_TCP_FLOW,
                    "encryption": vless_encryption,
                    "fp": fingerprint,
                    "sni": domain,
                    "alpn": "h2",
                    "path": profile.path,
                    "mode": getattr(profile, "mode", "") or "auto",
                }
            if getattr(profile, "xmux_enabled", False) and getattr(profile, "xmux", None):
                query_values["extra"] = json.dumps(
                    {"xmux": dict(profile.xmux)},
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            query = urlencode(query_values)
            body = f"vless://{user_id}@{host}:{profile.port}?{query}#{safe_name}"
    elif profile_id == "hysteria2":
        domain = str(state.get("tls_domain") or "")
        auth = str(config.get("hysteria_auth") or user_id)
        query_values = {
            "sni": domain,
            "insecure": "0",
            "alpn": "h3",
        }
        obfs_mode = str(server_config.get("hysteria2_obfs_mode") or "none").strip().lower()
        obfs_password = str(server_config.get("hysteria2_obfs_password") or "").strip()
        if obfs_mode == "salamander":
            if not obfs_password:
                body = ""
            else:
                query_values["obfs"] = "salamander"
                query_values["obfs-password"] = obfs_password
                scheme = str(server_config.get("hysteria2_uri_scheme") or "hysteria2").strip().lower()
                if scheme not in {"hysteria2", "hy2"}:
                    scheme = "hysteria2"
                query = urlencode(query_values)
                body = f"{scheme}://{quote(auth, safe='')}@{host}:{profile.port}/?{query}#{safe_name}"
        else:
            scheme = str(server_config.get("hysteria2_uri_scheme") or "hysteria2").strip().lower()
            if scheme not in {"hysteria2", "hy2"}:
                scheme = "hysteria2"
            query = urlencode(query_values)
            body = f"{scheme}://{quote(auth, safe='')}@{host}:{profile.port}/?{query}#{safe_name}"
    else:
        body = ""

    return ClientExport(filename, "text/plain; charset=utf-8", body)


def build_xray_link(client: Client, device: Device | None = None) -> ClientExport:
    """Legacy generic Xray export returns the first profile selected for access."""
    selected = _selected_xray_profiles(client, device)
    profile_id = selected[0] if selected else "xhttp_reality"
    return build_xray_profile_link(client, profile_id, device)


def build_mieru_link(client: Client, device: Device | None = None) -> ClientExport:
    config = _deployment_config(client, "mihomo", device)
    settings = get_connection_settings("mihomo")
    mieru = config.get("mieru") if isinstance(config.get("mieru"), dict) else {}
    username = quote(str(mieru.get("username") or ""), safe="")
    password = quote(str(mieru.get("password") or ""), safe="")
    host = str(settings.host or "")
    port = int(settings.config.get("mieru_port", settings.port or 2099))
    transport = str(settings.config.get("mieru_transport", "TCP")).upper()
    multiplexing = str(settings.config.get("mieru_multiplexing", "MULTIPLEXING_LOW"))
    handshake = str(settings.config.get("mieru_handshake", "HANDSHAKE_STANDARD"))
    query = urlencode(
        {
            "profile": "default",
            "port": port,
            "protocol": transport,
            "multiplexing": multiplexing,
            "handshake-mode": handshake,
        }
    )
    body = f"mierus://{username}:{password}@{host}?{query}#{quote(_label(client, device), safe='')}"
    return ClientExport(
        filename=f"sg-gateway-{_slug(client, device)}-mieru.txt",
        media_type="text/plain; charset=utf-8",
        body=body,
    )

def build_mihomo_yaml(client: Client, device: Device | None = None) -> ClientExport:
    resolved = _resolve_device(client, device)
    if resolved is None:
        return ClientExport("", "application/yaml; charset=utf-8", "")
    return ClientExport(
        filename=f"sg-gateway-{_slug(client, device)}-mihomo.yaml",
        media_type="application/yaml; charset=utf-8",
        body=build_device_yaml(resolved.id, _label(client, resolved)),
    )


def build_anytls_link(client: Client, device: Device | None = None) -> ClientExport:
    config = _deployment_config(client, "anytls", device)
    safe_name = quote(f"{_label(client, device)} · AnyTLS", safe="")
    query = urlencode(
        {
            "security": "tls",
            "sni": config.get("server_name", ""),
            "fp": config.get("fingerprint", "firefox"),
            "type": "tcp",
        }
    )
    body = (
        f"anytls://{quote(str(config.get('password') or ''), safe='')}"
        f"@{config.get('host', '')}:{config.get('port', 9443)}?{query}#{safe_name}"
    )
    return ClientExport(
        filename=f"sg-gateway-{_slug(client, device)}-anytls.txt",
        media_type="text/plain; charset=utf-8",
        body=body,
    )

def build_tuic_link(client: Client, device: Device | None = None) -> ClientExport:
    config = _deployment_config(client, "tuic", device)
    safe_name = quote(f"{_label(client, device)} · TUIC v5", safe="")
    query = urlencode(
        {
            "congestion_control": config.get("congestion_control", "bbr"),
            "udp_relay_mode": config.get("udp_relay_mode", "native"),
            "alpn": config.get("alpn", "h3"),
            "sni": config.get("server_name", ""),
        }
    )
    body = (
        f"tuic://{config.get('uuid', '')}:"
        f"{quote(str(config.get('password') or ''), safe='')}"
        f"@{config.get('host', '')}:{config.get('port', 10443)}?{query}#{safe_name}"
    )
    return ClientExport(
        filename=f"sg-gateway-{_slug(client, device)}-tuic-v5.txt",
        media_type="text/plain; charset=utf-8",
        body=body,
    )

def protocol_engine(kind: str) -> str:
    return {
        "amneziawg": "amneziawg",
        "xray": "xray",
        "xray-reality-tcp": "xray",
        "xray-xhttp-reality": "xray",
        "xray-xhttp-tls": "xray",
        "hysteria2": "xray",
        "mieru": "mihomo",
        "mihomo": "mihomo",
        "anytls": "anytls",
        "tuic": "tuic",
        "subscription": "sgclient",
    }.get(kind, "")


def build_protocol_export(
    client: Client,
    kind: str,
    device: Device | None = None,
) -> ClientExport:
    builders = {
        "amneziawg": build_awg_config,
        "xray": build_xray_link,
        "xray-reality-tcp": lambda item, access=None: build_xray_profile_link(item, "reality_tcp", access),
        "xray-xhttp-reality": lambda item, access=None: build_xray_profile_link(item, "xhttp_reality", access),
        "xray-xhttp-tls": lambda item, access=None: build_xray_profile_link(item, "xhttp_tls", access),
        "hysteria2": lambda item, access=None: build_xray_profile_link(item, "hysteria2", access),
        "mieru": build_mieru_link,
        "mihomo": build_mihomo_yaml,
        "anytls": build_anytls_link,
        "tuic": build_tuic_link,
        "subscription": build_subscription,
    }
    builder = builders.get(kind)
    if builder is None:
        return ClientExport("", "text/plain; charset=utf-8", "")
    return builder(client, device)


def protocol_ready(
    client: Client,
    kind: str,
    device: Device | None = None,
) -> bool:
    engine = protocol_engine(kind)
    if not engine or not is_export_ready(client, engine, device):
        return False
    if kind.startswith("xray-") or kind == "hysteria2":
        profile_id = {
            "xray-reality-tcp": "reality_tcp",
            "xray-xhttp-reality": "xhttp_reality",
            "xray-xhttp-tls": "xhttp_tls",
            "hysteria2": "hysteria2",
        }[kind]
        if profile_id not in _selected_xray_profiles(client, device):
            return False
        _, profile = _xray_profile(profile_id)
        return bool(profile and profile.enabled and profile.ready)
    if kind in {"anytls", "tuic"}:
        return bool(tls_overview().get("https_ready"))
    return True

def build_subscription(client: Client, device: Device | None = None) -> ClientExport:
    links: list[str] = []
    if is_export_ready(client, "xray", device):
        for profile_id in _selected_xray_profiles(client, device):
            kind = {
                "reality_tcp": "xray-reality-tcp",
                "xhttp_reality": "xray-xhttp-reality",
                "xhttp_tls": "xray-xhttp-tls",
                "hysteria2": "hysteria2",
            }.get(profile_id)
            if kind and protocol_ready(client, kind, device):
                link = build_protocol_export(client, kind, device).body
                if link:
                    links.append(link)
    if is_export_ready(client, "mihomo", device):
        link = build_mieru_link(client, device).body
        if link:
            links.append(link)
    if is_export_ready(client, "anytls", device):
        links.append(build_anytls_link(client, device).body)
    if is_export_ready(client, "tuic", device):
        links.append(build_tuic_link(client, device).body)

    decoded = "\n".join(item for item in links if item)
    if decoded:
        decoded += "\n"
    body = base64.b64encode(decoded.encode("utf-8")).decode("ascii")
    return ClientExport(
        filename=f"sg-gateway-{_slug(client, device)}-subscription.txt",
        media_type="text/plain; charset=utf-8",
        body=body,
    )
