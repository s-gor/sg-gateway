from __future__ import annotations

import base64
import json
import secrets
import uuid


def _token(byte_count: int = 32) -> str:
    return base64.b64encode(secrets.token_bytes(byte_count)).decode("ascii")


def build_engine_config(engine: str, client_id: int, client_name: str) -> tuple[str, str]:
    if engine == "amneziawg":
        public_key = _token()
        payload = {
            "client_name": client_name,
            "private_key": _token(),
            "public_key": public_key,
            "address": f"10.66.{client_id}.2/32",
            "dns": "1.1.1.1",
            "server_public_key": "PLACEHOLDER_SERVER_PUBLIC_KEY",
            "endpoint": "vpn.example.com:51820",
            "allowed_ips": "0.0.0.0/0, ::/0",
            "persistent_keepalive": 25,
        }
        return public_key, json.dumps(payload, ensure_ascii=False, sort_keys=True)

    if engine == "xray":
        user_id = str(uuid.uuid4())
        payload = {
            "client_name": client_name,
            "uuid": user_id,
            "host": "vpn.example.com",
            "port": 443,
            "security": "reality",
            "type": "tcp",
            "flow": "xtls-rprx-vision",
            "fingerprint": "chrome",
            "server_name": "www.cloudflare.com",
            "public_key": "PLACEHOLDER_REALITY_PUBLIC_KEY",
            "short_id": "PLACEHOLDER_SHORT_ID",
        }
        return user_id, json.dumps(payload, ensure_ascii=False, sort_keys=True)

    payload = {"client_name": client_name, "engine": engine}
    return f"{engine}-{client_id}", json.dumps(payload, ensure_ascii=False, sort_keys=True)