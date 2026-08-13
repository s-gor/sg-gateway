from app.clients.exports import ClientExport
from app.clients.repository import Client, Device
from app.clients import sg_subscription as subscription


def _client():
    return Client(7, "Shany", True, None, "applied", "applied", "applied", "applied", "applied", "applied", 2, 2)


def _device(device_id, name, primary):
    return Device(device_id, 7, name, True, None, primary, "2026-08-13 00:00:00")


def test_document_contains_all_devices_and_assigned_profiles(monkeypatch):
    primary = _device(11, "Основной доступ", True)
    phone = _device(12, "Телефон", False)
    monkeypatch.setattr(subscription, "list_devices", lambda _: [primary, phone])
    all_tokens = [
        "xray_reality_tcp", "xray_xhttp_reality", "xray_xhttp_tls",
        "xray_hysteria2", "amneziawg", "amneziawg3", "mihomo",
        "anytls", "tuic", "sgclient",
    ]
    monkeypatch.setattr(
        subscription,
        "device_access_tokens",
        lambda device_id: all_tokens if device_id == 11 else ["xray_reality_tcp", "mihomo", "tuic"],
    )
    monkeypatch.setattr(subscription, "protocol_ready", lambda *args: True)

    def fake_export(_client, kind, _device):
        if kind in {"amneziawg", "amneziawg3"}:
            return ClientExport(f"{kind}.conf", "text/plain", "[Interface]\n")
        if kind == "anytls":
            body = "anytls://pw@example.com:9443?sni=example.com#Shany"
        elif kind == "tuic":
            body = "tuic://uuid:pw@example.com:10443?congestion_control=bbr&udp_relay_mode=native&alpn=h3&sni=example.com#Shany"
        elif kind == "mieru":
            body = "mierus://u:p@example.com?profile=default#Shany"
        elif kind == "hysteria2":
            body = "hysteria2://auth@example.com:8446/?sni=example.com#Shany"
        else:
            body = f"vless://uuid@example.com:443?type=tcp#{kind}"
        return ClientExport(f"{kind}.txt", "text/plain", body)

    monkeypatch.setattr(subscription, "build_protocol_export", fake_export)
    document = subscription.build_sg_subscription_document(_client())

    assert document["format"] == "sg-subscription"
    assert document["version"] == 1
    assert document["scope"] == "client"
    assert document["summary"] == {
        "devices": 2,
        "profiles_assigned": 12,
        "profiles_ready": 12,
    }
    assert len(document["devices"][0]["profiles"]) == 9
    assert len(document["devices"][1]["profiles"]) == 3
    assert document["devices"][0]["profiles"][4]["format"] == "config"
    assert document["devices"][0]["profiles"][5]["format"] == "config"
