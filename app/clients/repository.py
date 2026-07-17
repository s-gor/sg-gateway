from __future__ import annotations

from dataclasses import dataclass

from app.db import connect


@dataclass(frozen=True)
class Client:
    id: int
    name: str
    enabled: bool
    expires_at: str | None
    awg_status: str
    xray_status: str


@dataclass(frozen=True)
class ClientDeployment:
    engine: str
    status: str
    engine_object_id: str | None


def _row_to_client(row) -> Client:
    return Client(
        id=row["id"],
        name=row["name"],
        enabled=bool(row["enabled"]),
        expires_at=row["expires_at"],
        awg_status=row["awg_status"],
        xray_status=row["xray_status"],
    )


def list_clients() -> list[Client]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
                c.id,
                c.name,
                c.enabled,
                c.expires_at,
                COALESCE(awg.status, 'missing') AS awg_status,
                COALESCE(xray.status, 'missing') AS xray_status
            FROM clients c
            LEFT JOIN client_deployments awg
                ON awg.client_id = c.id AND awg.engine = 'amneziawg'
            LEFT JOIN client_deployments xray
                ON xray.client_id = c.id AND xray.engine = 'xray'
            ORDER BY c.id DESC
            """
        ).fetchall()

    return [_row_to_client(row) for row in rows]


def get_client(client_id: int) -> Client | None:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT
                c.id,
                c.name,
                c.enabled,
                c.expires_at,
                COALESCE(awg.status, 'missing') AS awg_status,
                COALESCE(xray.status, 'missing') AS xray_status
            FROM clients c
            LEFT JOIN client_deployments awg
                ON awg.client_id = c.id AND awg.engine = 'amneziawg'
            LEFT JOIN client_deployments xray
                ON xray.client_id = c.id AND xray.engine = 'xray'
            WHERE c.id = ?
            """,
            (client_id,),
        ).fetchone()

    return _row_to_client(row) if row else None


def list_client_deployments(client_id: int) -> list[ClientDeployment]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT engine, status, engine_object_id
            FROM client_deployments
            WHERE client_id = ?
            ORDER BY engine
            """,
            (client_id,),
        ).fetchall()

    return [
        ClientDeployment(
            engine=row["engine"],
            status=row["status"],
            engine_object_id=row["engine_object_id"],
        )
        for row in rows
    ]


def count_clients() -> int:
    with connect() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM clients").fetchone()
    return int(row["total"])


def create_client(name: str, access: str) -> int | None:
    clean_name = name.strip()
    if not clean_name:
        return None

    engines = {
        "recommended": ["amneziawg", "xray"],
        "amneziawg": ["amneziawg"],
        "xray": ["xray"],
    }.get(access, ["amneziawg", "xray"])

    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO clients (name, enabled) VALUES (?, 1)",
            (clean_name,),
        )
        client_id = cursor.lastrowid
        for engine in engines:
            connection.execute(
                """
                INSERT INTO client_deployments (client_id, engine, status)
                VALUES (?, ?, 'pending')
                """,
                (client_id, engine),
            )

    return int(client_id)


def set_client_enabled(client_id: int, enabled: bool) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE clients SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, client_id),
        )


def delete_client(client_id: int) -> None:
    with connect() as connection:
        connection.execute("DELETE FROM clients WHERE id = ?", (client_id,))