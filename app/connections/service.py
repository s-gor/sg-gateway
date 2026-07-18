from __future__ import annotations

from dataclasses import dataclass

from app.connections.settings import get_connection_settings
from app.db import connect


@dataclass(frozen=True)
class ConnectionSummary:
    name: str
    label: str
    status: str
    port: str
    clients: int
    note: str


def list_connections() -> list[ConnectionSummary]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT engine, COUNT(*) AS total
            FROM client_deployments
            GROUP BY engine
            """
        ).fetchall()

    counts = {row["engine"]: int(row["total"]) for row in rows}
    awg = get_connection_settings("amneziawg")
    xray = get_connection_settings("xray")

    return [
        ConnectionSummary(
            name="amneziawg",
            label="AmneziaWG",
            status="Настроено" if awg.enabled else "Отключено",
            port=f"UDP {awg.port}",
            clients=counts.get("amneziawg", 0),
            note=f"Адрес: {awg.host}:{awg.port}",
        ),
        ConnectionSummary(
            name="xray",
            label="Xray Reality",
            status="Настроено" if xray.enabled else "Отключено",
            port=f"TCP {xray.port}",
            clients=counts.get("xray", 0),
            note=f"Адрес: {xray.host}:{xray.port}",
        ),
    ]
