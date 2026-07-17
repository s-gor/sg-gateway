from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from app.clients.repository import Client, list_client_deployments


@dataclass(frozen=True)
class ClientExport:
    filename: str
    media_type: str
    body: str


def build_awg_config(client: Client) -> ClientExport:
    body = f"""# SG-Gateway AmneziaWG placeholder
# Client: {client.name}
# This will be replaced by generated keys and server endpoint.

[Interface]
PrivateKey = PLACEHOLDER_CLIENT_PRIVATE_KEY
Address = 10.66.{client.id}.2/32
DNS = 1.1.1.1

[Peer]
PublicKey = PLACEHOLDER_SERVER_PUBLIC_KEY
Endpoint = vpn.example.com:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
    return ClientExport(
        filename=f"sg-gateway-{client.id}-amneziawg.conf",
        media_type="text/plain; charset=utf-8",
        body=body,
    )


def build_xray_link(client: Client) -> ClientExport:
    safe_name = quote(client.name)
    body = (
        f"vless://placeholder-{client.id}@vpn.example.com:443"
        f"?type=tcp&security=reality&flow=xtls-rprx-vision"
        f"&fp=chrome&sni=www.cloudflare.com&pbk=PLACEHOLDER_PUBLIC_KEY"
        f"#{safe_name}"
    )
    return ClientExport(
        filename=f"sg-gateway-{client.id}-xray.txt",
        media_type="text/plain; charset=utf-8",
        body=body,
    )


def build_subscription(client: Client) -> ClientExport:
    deployment_names = ", ".join(item.engine for item in list_client_deployments(client.id))
    body = f"""# SG-Gateway subscription placeholder
client={client.name}
client_id={client.id}
deployments={deployment_names}
"""
    return ClientExport(
        filename=f"sg-gateway-{client.id}-subscription.txt",
        media_type="text/plain; charset=utf-8",
        body=body,
    )