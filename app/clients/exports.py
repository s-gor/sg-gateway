from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import quote

from app.clients.repository import Client, list_client_deployments


@dataclass(frozen=True)
class ClientExport:
    filename: str
    media_type: str
    body: str


def _deployment_config(client: Client, engine: str) -> dict:
    deployments = {item.engine: item for item in list_client_deployments(client.id)}
    deployment = deployments.get(engine)
    if deployment is None or not deployment.config_json:
        return {}
    return json.loads(deployment.config_json)


def build_awg_config(client: Client) -> ClientExport:
    config = _deployment_config(client, "amneziawg")
    body = f"""# SG-Gateway AmneziaWG
# Client: {client.name}

[Interface]
PrivateKey = {config.get("private_key", "PLACEHOLDER_CLIENT_PRIVATE_KEY")}
Address = {config.get("address", "10.66.0.2/32")}
DNS = {config.get("dns", "1.1.1.1")}

[Peer]
PublicKey = {config.get("server_public_key", "PLACEHOLDER_SERVER_PUBLIC_KEY")}
Endpoint = {config.get("endpoint", "vpn.example.com:51820")}
AllowedIPs = {config.get("allowed_ips", "0.0.0.0/0, ::/0")}
PersistentKeepalive = {config.get("persistent_keepalive", 25)}
"""
    return ClientExport(
        filename=f"sg-gateway-{client.id}-amneziawg.conf",
        media_type="text/plain; charset=utf-8",
        body=body,
    )


def build_xray_link(client: Client) -> ClientExport:
    config = _deployment_config(client, "xray")
    safe_name = quote(client.name)
    body = (
        f"vless://{config.get('uuid', 'PLACEHOLDER_UUID')}"
        f"@{config.get('host', 'vpn.example.com')}:{config.get('port', 443)}"
        f"?type={config.get('type', 'tcp')}"
        f"&security={config.get('security', 'reality')}"
        f"&flow={config.get('flow', 'xtls-rprx-vision')}"
        f"&fp={config.get('fingerprint', 'chrome')}"
        f"&sni={config.get('server_name', 'www.cloudflare.com')}"
        f"&pbk={config.get('public_key', 'PLACEHOLDER_REALITY_PUBLIC_KEY')}"
        f"&sid={config.get('short_id', 'PLACEHOLDER_SHORT_ID')}"
        f"#{safe_name}"
    )
    return ClientExport(
        filename=f"sg-gateway-{client.id}-xray.txt",
        media_type="text/plain; charset=utf-8",
        body=body,
    )


def build_subscription(client: Client) -> ClientExport:
    deployment_names = ", ".join(item.engine for item in list_client_deployments(client.id))
    body = f"""# SG-Gateway subscription
client={client.name}
client_id={client.id}
deployments={deployment_names}

{build_xray_link(client).body}
"""
    return ClientExport(
        filename=f"sg-gateway-{client.id}-subscription.txt",
        media_type="text/plain; charset=utf-8",
        body=body,
    )