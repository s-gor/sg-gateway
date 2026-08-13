import sqlite3

from app.clients.repository import Client
from app.clients import sg_subscription_store as store


def _client():
    return Client(7, "Shany", True, None, "applied", "applied", "applied", "applied", "applied", "applied", 1, 1)


def test_client_token_is_stable_separate_and_revocable(tmp_path, monkeypatch):
    database = tmp_path / "tokens.sqlite"

    def connect():
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    with connect() as connection:
        connection.executescript("""
            CREATE TABLE clients (id INTEGER PRIMARY KEY, name TEXT, enabled INTEGER, expires_at TEXT);
            CREATE TABLE devices (id INTEGER PRIMARY KEY, client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE);
            CREATE TABLE device_credentials (id INTEGER PRIMARY KEY, device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE, engine TEXT, config_json TEXT);
            INSERT INTO clients VALUES (7, 'Shany', 1, NULL);
            INSERT INTO devices VALUES (11, 7);
            INSERT INTO device_credentials VALUES (21, 11, 'sgclient', '{"subscription_token":"legacy-device-token-12345678901234567890"}');
        """)

    monkeypatch.setattr(store, "init_db", lambda: None)
    monkeypatch.setattr(store, "connect", connect)
    monkeypatch.setattr(store, "get_client", lambda _: _client())

    first = store.ensure_client_subscription_token(7)
    second = store.ensure_client_subscription_token(7)
    assert first == second
    assert first.startswith("sg1_")
    assert "legacy-device-token" not in first
    assert store.get_client_by_subscription_token(first).id == 7

    with connect() as connection:
        connection.execute("DELETE FROM device_credentials WHERE engine = 'sgclient'")
    assert store.ensure_client_subscription_token(7) == ""
    assert store.get_client_by_subscription_token(first) is None
