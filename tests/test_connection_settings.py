from app.clients.exports import build_awg_config, build_xray_link
from app.clients.repository import create_client, get_client
from app.connections.service import list_connections
from app.connections.settings import get_connection_settings, update_connection_settings
from app.db import init_db


def test_update_connection_settings_changes_new_exports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_db()

    awg = get_connection_settings("amneziawg")
    awg_config = dict(awg.config)
    awg_config["server_public_key"] = "SERVER_PUBLIC_KEY_TEST"
    update_connection_settings("amneziawg", "vpn.test", 60000, awg_config)

    xray = get_connection_settings("xray")
    xray_config = dict(xray.config)
    xray_config["public_key"] = "REALITY_PUBLIC_KEY_TEST"
    xray_config["short_id"] = "abc123"
    update_connection_settings("xray", "xray.test", 443, xray_config)

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
