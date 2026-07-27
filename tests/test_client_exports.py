import base64

from app.clients.exports import (
    build_mieru_link,
    build_subscription,
    build_xray_link,
)
from app.clients.repository import create_client, get_client, list_devices
from app.connections.settings import (
    get_connection_settings,
    update_connection_settings,
)
from app.db import connect


def test_client_exports_use_xray_in_recovery_baseline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client_id = create_client(
        "Irina iPhone",
        "xray_reality_tcp,sgclient",
    )
    client = get_client(client_id)
    device = list_devices(client_id)[0]

    xray = get_connection_settings("xray")
    config = dict(xray.config)
    config["public_key"] = "REALITY_PUBLIC_KEY_TEST"
    config["short_id"] = "abc123"
    assert update_connection_settings(
        "xray",
        "203.0.113.10",
        443,
        config,
    )

    with connect() as connection:
        connection.execute(
            "UPDATE device_credentials SET status = 'applied'"
        )

    xray_link = build_xray_link(client, device)
    mieru = build_mieru_link(client, device)
    subscription = build_subscription(client, device)
    decoded = base64.b64decode(subscription.body).decode("utf-8")

    assert xray_link.body.startswith("vless://")
    assert "203.0.113.10:443" in xray_link.body
    assert "Irina%20iPhone" in xray_link.body
    assert mieru.body == ""
    assert decoded == ""
