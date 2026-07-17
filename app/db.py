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
"""


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


def init_db() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)
        if not _column_exists(connection, "client_deployments", "config_json"):
            connection.execute("ALTER TABLE client_deployments ADD COLUMN config_json TEXT")