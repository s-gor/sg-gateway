from pathlib import Path


def test_production_entrypoint_registers_legacy_and_sg_v1_routes():
    from app.production import app

    rules = {rule.rule: rule.endpoint for rule in app.url_map.iter_rules()}
    assert rules["/sub/<token>"] == "subscription_feed"
    assert rules["/sg/sub/v1/<token>"] == "sg_subscription_v1"
    assert rules["/api/clients/<int:client_id>/sg-subscription-v1"] == "sg_subscription_v1_info"


def test_systemd_uses_02205_production_entrypoint():
    service = Path("deploy/systemd/sg-gateway.service").read_text(encoding="utf-8")
    assert "app.production:app" in service
    assert "app.wsgi:app" not in service
