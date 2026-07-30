from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_subscription_qr_uses_compact_public_url() -> None:
    source = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert 'if kind == "subscription":' in source
    assert '"public_device_subscription"' in source
    assert 'path = url_for(' in source
    assert 'public_base = f"http://{address}{suffix}"' in source
    assert 'tls_state.get("public_url")' in source
    assert 'build_qr_svg(qr_payload)' in source


def test_public_subscription_endpoint_is_token_protected_and_auth_exempt() -> None:
    main = (ROOT / "app/main.py").read_text(encoding="utf-8")
    auth = (ROOT / "app/security/auth.py").read_text(encoding="utf-8")
    tokens = (ROOT / "app/clients/subscription_tokens.py").read_text(encoding="utf-8")
    assert '@app.get("/s/<int:client_id>/<int:device_id>/<token>")' in main
    assert 'verify_device_subscription_token(client_id, device_id, token)' in main
    assert 'protocol_ready(client, "subscription", device)' in main
    assert '"Cache-Control": "no-store"' in main
    assert '"public_device_subscription"' in auth
    assert 'hmac.new(_key(), message, hashlib.sha256)' in tokens
    assert 'hmac.compare_digest' in tokens


def test_subscription_payload_itself_is_not_changed_by_qr_fix() -> None:
    exports = (ROOT / "app/clients/exports.py").read_text(encoding="utf-8")
    assert 'body = base64.b64encode(decoded.encode("utf-8")).decode("ascii")' in exports
    assert 'filename=f"sg-gateway-{_slug(client, device)}-subscription.txt"' in exports
