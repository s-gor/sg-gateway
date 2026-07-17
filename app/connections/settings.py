from __future__ import annotations

import json
from dataclasses import dataclass

from app.db import connect


@dataclass(frozen=True)
class ConnectionSettings:
    engine: str
    enabled: bool
    host: str
    port: int
    config: dict


def get_connection_settings(engine: str) -> ConnectionSettings:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT engine, enabled, host, port, config_json
            FROM connection_settings
            WHERE engine = ?
            """,
            (engine,),
        ).fetchone()

    if row is None:
        raise KeyError(f"Unknown connection engine: {engine}")

    return ConnectionSettings(
        engine=row["engine"],
        enabled=bool(row["enabled"]),
        host=row["host"],
        port=int(row["port"]),
        config=json.loads(row["config_json"]),
    )


def update_connection_settings(engine: str, host: str, port: int, config: dict) -> None:
    clean_host = host.strip()
    if not clean_host:
        return

    with connect() as connection:
        connection.execute(
            """
            UPDATE connection_settings
            SET host = ?,
                port = ?,
                config_json = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE engine = ?
            """,
            (clean_host, int(port), json.dumps(config, ensure_ascii=False, sort_keys=True), engine),
        )