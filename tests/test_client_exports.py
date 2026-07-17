from app.clients.exports import build_awg_config, build_subscription, build_xray_link
from app.clients.repository import create_client, get_client


def test_client_exports_include_client_identity(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client_id = create_client("Irina iPhone", "recommended")
    client = get_client(client_id)

    awg = build_awg_config(client)
    xray = build_xray_link(client)
    subscription = build_subscription(client)

    assert "Irina iPhone" in awg.body
    assert "vless://" in xray.body
    assert "deployments=amneziawg, xray" in subscription.body