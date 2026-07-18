from __future__ import annotations

from dataclasses import dataclass

from app.db import connect, init_db
from app.engines.provisioning import build_engine_config
from app.maintenance.operations import log_operation


MAX_CLIENT_NAME_LENGTH = 80


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
    config_json: str | None


def _row_to_client(row) -> Client:
    return Client(
        id=row["id"],
        name=row["name"],
        enabled=bool(row["enabled"]),
        expires_at=row["expires_at"],
        awg_status=row["awg_status"],
        xray_status=row["xray_status"],
    )


def _clean_client_name(name: str) -> str | None:
    clean_name = " ".join(name.split())
    if not clean_name:
        return None
    if len(clean_name) > MAX_CLIENT_NAME_LENGTH:
        return None
    return clean_name


def _client_name_exists(connection, clean_name: str) -> bool:
    rows = connection.execute("SELECT name FROM clients").fetchall()
    wanted = clean_name.casefold()
    return any(row["name"].casefold() == wanted for row in rows)


def list_clients() -> list[Client]:
    init_db()
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
    init_db()
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
    init_db()
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT engine, status, engine_object_id, config_json
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
            config_json=row["config_json"],
        )
        for row in rows
    ]


def count_clients() -> int:
    init_db()
    with connect() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM clients").fetchone()
    return int(row["total"])


def create_client(name: str, access: str, expires_at: str | None = None) -> int | None:
    init_db()
    clean_name = _clean_client_name(name)
    if clean_name is None:
        log_operation(
            action="client.create",
            target="client:new",
            status="error",
            message="Отклонено недопустимое имя клиента",
        )
        return None

    engines = {
        "recommended": ["amneziawg", "xray"],
        "amneziawg": ["amneziawg"],
        "xray": ["xray"],
    }.get(access, ["amneziawg", "xray"])

    with connect() as connection:
        if _client_name_exists(connection, clean_name):
            log_operation(
                action="client.create",
                target="client:new",
                status="error",
                message=f"Отклонено повторяющееся имя клиента: {clean_name}",
            )
            return None

        cursor = connection.execute(
            "INSERT INTO clients (name, enabled, expires_at) VALUES (?, 1, ?)",
            (clean_name, expires_at or None),
        )
        client_id = int(cursor.lastrowid)
        for engine in engines:
            engine_object_id, config_json = build_engine_config(engine, client_id, clean_name)
            connection.execute(
                """
                INSERT INTO client_deployments (
                    client_id,
                    engine,
                    status,
                    engine_object_id,
                    config_json
                )
                VALUES (?, ?, 'generated', ?, ?)
                """,
                (client_id, engine, engine_object_id, config_json),
            )

    log_operation(
        action="client.create",
        target=f"client:{client_id}",
        message=f"Создан клиент {clean_name}; доступ: {', '.join(engines)}",
    )
    return client_id


def set_client_enabled(client_id: int, enabled: bool) -> bool:
    init_db()
    with connect() as connection:
        cursor = connection.execute(
            "UPDATE clients SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, client_id),
        )

    action = "client.enable" if enabled else "client.disable"
    if cursor.rowcount == 0:
        log_operation(
            action=action,
            target=f"client:{client_id}",
            status="error",
            message="Клиент не найден",
        )
        return False

    log_operation(
        action=action,
        target=f"client:{client_id}",
        message="Клиент включён" if enabled else "Клиент отключён",
    )
    return True


def delete_client(client_id: int) -> bool:
    init_db()
    with connect() as connection:
        cursor = connection.execute("DELETE FROM clients WHERE id = ?", (client_id,))

    if cursor.rowcount == 0:
        log_operation(
            action="client.delete",
            target=f"client:{client_id}",
            status="error",
            message="Клиент не найден",
        )
        return False

    log_operation(
        action="client.delete",
        target=f"client:{client_id}",
        message="Клиент удалён",
    )
    return True
