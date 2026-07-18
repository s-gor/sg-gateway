from __future__ import annotations

from dataclasses import dataclass

from app.clients.repository import Client, list_client_deployments


@dataclass(frozen=True)
class AccessCard:
    title: str
    status: str
    description: str
    primary_action: str
    secondary_action: str
    export_url: str
    qr_url: str
    payload: str


def build_access_cards(client: Client) -> list[AccessCard]:
    deployments = {item.engine: item for item in list_client_deployments(client.id)}
    cards: list[AccessCard] = []

    if "amneziawg" in deployments:
        cards.append(
            AccessCard(
                title="AmneziaWG",
                status=deployments["amneziawg"].status,
                description="Отдельная конфигурация для AmneziaWG-клиента.",
                primary_action="Скачать конфигурацию",
                secondary_action="QR",
                export_url=f"/clients/{client.id}/exports/amneziawg",
                qr_url=f"/clients/{client.id}/qr/amneziawg",
                payload=f"# SG-Gateway AmneziaWG access for {client.name}",
            )
        )

    if "xray" in deployments:
        cards.append(
            AccessCard(
                title="Xray Reality",
                status=deployments["xray"].status,
                description="Ссылка для совместимого Xray-клиента.",
                primary_action="Скопировать ссылку",
                secondary_action="QR",
                export_url=f"/clients/{client.id}/exports/xray",
                qr_url=f"/clients/{client.id}/qr/xray",
                payload=f"vless://client-{client.id}@configured-endpoint#{client.name}",
            )
        )

    cards.append(
        AccessCard(
            title="SG Client",
            status="planned",
            description="Единая подписка появится после подключения генераторов AWG и Xray.",
            primary_action="Скачать подписку",
            secondary_action="QR",
            export_url=f"/clients/{client.id}/exports/subscription",
            qr_url=f"/clients/{client.id}/qr/subscription",
            payload=f"sg://client/{client.id}",
        )
    )

    return cards
