from app.clients.exports import build_awg_config, build_xray_link
from app.clients.repository import create_client, get_client
from app.connections.service import list_connections
from app.connections.settings import get_connection_settings, update_connection_settings
from app.db import init_db
from app.main import create_app
from app.maintenance.operations import list_operations


def test_update_connection_settings_changes_new_exports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_db()

    awg = get_connection_settings("amneziawg")
    awg_config = dict(awg.config)
    awg_config["server_public_key"] = "SERVER_PUBLIC_KEY_TEST"
    updated = update_connection_settings("amneziawg", "vpn.test", 60000, awg_config)
    assert updated is True

    xray = get_connection_settings("xray")
    xray_config = dict(xray.config)
    xray_config["public_key"] = "REALITY_PUBLIC_KEY_TEST"
    xray_config["short_id"] = "abc123"
    updated = update_connection_settings("xray", "xray.test", 443, xray_config)
    assert updated is True

    client_id = create_client("Irina", "recommended")
    client = get_client(client_id)

    assert "Endpoint = vpn.test:60000" in build_awg_config(client).body
    assert "@xray.test:443" in build_xray_link(client).body
    assert "REALITY_PUBLIC_KEY_TEST" in build_xray_link(client).body


def test_connection_summaries_are_ru_ready(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_db()

    connections = list_connections()

    assert connections[0].status == "Настроено"
    assert connections[0].note.startswith("Адрес: ")
    assert connections[1].status == "Настроено"
    assert connections[1].note.startswith("Адрес: ")


def test_invalid_connection_settings_are_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_db()

    original = get_connection_settings("xray")
    updated = update_connection_settings("xray", "xray.test", "not-a-port", original.config)

    current = get_connection_settings("xray")
    operations = list_operations()

    assert updated is False
    assert current.host == original.host
    assert current.port == original.port
    assert operations[0].status == "error"
    assert "Rejected invalid connection settings" in operations[0].message


def test_invalid_connection_port_does_not_crash_route(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SG_GATEWAY_ADMIN_PASSWORD", "secret")
    app = create_app()
    client = app.test_client()
    client.post("/login", data={"password": "secret"})

    response = client.post(
        "/connections/xray",
        data={
            "host": "xray.test",
            "port": "not-a-port",
            "server_name": "www.cloudflare.com",
            "public_key": "REALITY_PUBLIC_KEY_TEST",
            "short_id": "abc123",
        },
    )

    current = get_connection_settings("xray")
    assert response.status_code == 302
    assert current.host == "vpn.example.com"
    assert current.port == 443



def test_invalid_connection_port_shows_feedback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SG_GATEWAY_ADMIN_PASSWORD", "secret")
    app = create_app()
    client = app.test_client()
    client.post("/login", data={"password": "secret"})

    response = client.post(
        "/connections/xray",
        data={
            "host": "xray.test",
            "port": "not-a-port",
            "server_name": "www.cloudflare.com",
            "public_key": "REALITY_PUBLIC_KEY_TEST",
            "short_id": "abc123",
        },
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Настройки Xray не применены" in body
    assert "Проверьте хост и порт" in body
