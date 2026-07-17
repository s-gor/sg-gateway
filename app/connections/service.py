from __future__ import annotations

from dataclasses import dataclass

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

    return [
        ConnectionSummary(
            name="amneziawg",
            label="AmneziaWG",
            status="Not configured",
            port="UDP later",
            clients=counts.get("amneziawg", 0),
            note="Separate .conf and QR for simple clients.",
        ),
        ConnectionSummary(
            name="xray",
            label="Xray Reality",
            status="Not configured",
            port="TCP 443 later",
            clients=counts.get("xray", 0),
            note="VLESS Reality link and subscription export.",
        ),
    ]