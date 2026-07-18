from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import load_config

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS client_deployments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    engine TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    engine_object_id TEXT,
    config_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(client_id, engine)
);

CREATE TABLE IF NOT EXISTS connection_settings (
    engine TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 1,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    config_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS operation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ok',
    message TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


DEFAULT_CONNECTIONS = {
    "amneziawg": {
        "host": "vpn.example.com",
        "port": 51820,
        "config_json": (
            '{"dns":"1.1.1.1","country_code":"nl","server_public_key":"PLACEHOLDER_SERVER_PUBLIC_KEY",'
            '"allowed_ips":"0.0.0.0/0, ::/0","persistent_keepalive":25}'
        ),
    },
    "xray": {
        "host": "vpn.example.com",
        "port": 443,
        "config_json": (
            '{"security":"reality","country_code":"nl","type":"tcp","flow":"xtls-rprx-vision",'
            '"fingerprint":"chrome","server_name":"www.cloudflare.com",'
            '"public_key":"PLACEHOLDER_REALITY_PUBLIC_KEY","short_id":"PLACEHOLDER_SHORT_ID"}'
        ),
    },
}


def get_database_path() -> Path:
    return load_config().data_dir / "sg-gateway.sqlite"


def connect() -> sqlite3.Connection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _column_exists(connection: sqlite3.Connection, table: str, column: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _seed_connection_settings(connection: sqlite3.Connection) -> None:
    for engine, values in DEFAULT_CONNECTIONS.items():
        connection.execute(
            """
            INSERT OR IGNORE INTO connection_settings (engine, enabled, host, port, config_json)
            VALUES (?, 1, ?, ?, ?)
            """,
            (engine, values["host"], values["port"], values["config_json"]),
        )


def init_db() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)
        if not _column_exists(connection, "client_deployments", "config_json"):
            connection.execute("ALTER TABLE client_deployments ADD COLUMN config_json TEXT")
        _seed_connection_settings(connection)