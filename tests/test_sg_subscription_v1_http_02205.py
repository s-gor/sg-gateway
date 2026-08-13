from flask import Flask
from app.clients.repository import Client
from app.clients import sg_subscription_http as http


def test_sg_subscription_feed_returns_json(monkeypatch):
    client = Client(7, "Shany", True, None, "applied", "applied", "applied", "applied", "applied", "applied", 1, 1)
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
