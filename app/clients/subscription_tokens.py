from __future__ import annotations

import base64
import hashlib
import hmac

from app.config import load_config


def _key() -> bytes:
    return load_config().secret_key.encode("utf-8")


def device_subscription_token(client_id: int, device_id: int) -> str:
    message = f"subscription:{int(client_id)}:{int(device_id)}".encode("ascii")
    digest = hmac.new(_key(), message, hashlib.sha256).digest()[:24]
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def verify_device_subscription_token(client_id: int, device_id: int, token: str) -> bool:
    expected = device_subscription_token(client_id, device_id)
    return hmac.compare_digest(expected, str(token or ""))
