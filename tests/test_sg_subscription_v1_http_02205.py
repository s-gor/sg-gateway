from flask import Flask, render_template_string
from app.clients.repository import Client
from app.clients import sg_subscription_http as http


def _client():
    return Client(7, "Shany", True, None, "applied", "applied", "applied", "applied", "applied", "applied", 1, 1)


def test_sg_subscription_feed_returns_json(monkeypatch):
    client = _client()
    monkeypatch.setattr(http, "get_client_by_subscription_token", lambda token: client)
    monkeypatch.setattr(http, "build_sg_subscription_document", lambda item: {
        "format": "sg-subscription", "version": 1, "scope": "client",
        "client": {"id": item.id, "name": item.name},
        "summary": {"devices": 1, "profiles_assigned": 9, "profiles_ready": 9},
        "devices": [],
    })
    app = Flask(__name__)
    http.register_sg_subscription(app)
    response = app.test_client().get("/sg/sub/v1/sg1_example")
    assert response.status_code == 200
    assert response.get_json()["format"] == "sg-subscription"
    assert response.headers["X-SG-Subscription-Version"] == "1"
    assert response.headers["Cache-Control"] == "no-store, max-age=0"


def test_sg_subscription_client_qr_uses_sg_v1_url(monkeypatch):
    client = _client()
    expected = "https://vpn.example/sg/sub/v1/sg1_clientwide"
    monkeypatch.setattr(http, "get_client", lambda client_id: client if client_id == client.id else None)
    monkeypatch.setattr(http, "build_sg_subscription_url", lambda item: expected)
    monkeypatch.setattr(http, "build_qr_svg", lambda value: f"<svg>{value}</svg>")

    app = Flask(__name__)
    http.register_sg_subscription(app)

    response = app.test_client().get(f"/clients/{client.id}/sg-subscription-v1/qr")
    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert expected.encode() in response.data

    with app.test_request_context("/"):
        rendered = render_template_string("{{ sg_subscription_url(client) }}", client=client)
    assert rendered == expected
