from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
HOSTD = ROOT / "hostd"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HOSTD) not in sys.path:
    sys.path.insert(0, str(HOSTD))

from app.xray import xmux
from app.xray.sg_panel_vless import xhttp_reality_inbound, xhttp_reality_link, xhttp_tls_link
from sg_hostd import client_runtime
from sg_hostd.xhttp_tls_front import (
    INCLUDE_DIRECTIVE,
    MARKER,
    ensure_site_contract,
    render_snippet,
)

SG_PANEL_REFERENCE_COMMIT = "31f1e137d83c02c64bf1039ebbdaf2b02bbfbeae"
ENCRYPTION = "mlkem768x25519plus.native.0rtt.test.CLIENT"
DECRYPTION = "mlkem768x25519plus.native.600s.test.SERVER"


def test_reference_commit_is_pinned() -> None:
    assert SG_PANEL_REFERENCE_COMMIT == "31f1e137d83c02c64bf1039ebbdaf2b02bbfbeae"
    manifest = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))
    parity = manifest["development_vless_parity"]
    assert parity["reference_commit"] == SG_PANEL_REFERENCE_COMMIT
    assert parity["other_protocols_changed"] is False


def test_reality_xhttp_contract_remains_panel_server_auto_client_stream_one() -> None:
    inbound = xhttp_reality_inbound(
        clients=[{"id": "11111111-1111-1111-1111-111111111111", "flow": "xtls-rprx-vision"}],
        port=8444,
        path="/sg-xhttp-reality",
        decryption=DECRYPTION,
        dest="www.bing.com:443",
        server_name="www.bing.com",
        private_key="private",
        short_id="0123456789abcdef",
    )
    assert inbound["settings"]["decryption"] == DECRYPTION
    assert inbound["settings"]["clients"][0]["flow"] == "xtls-rprx-vision"
    assert inbound["streamSettings"]["network"] == "xhttp"
    assert inbound["streamSettings"]["security"] == "reality"
    assert inbound["streamSettings"]["xhttpSettings"]["mode"] == "auto"

    link = xhttp_reality_link(
        uuid="11111111-1111-1111-1111-111111111111",
        host="203.0.113.10",
        port=8444,
        title="Reality",
        fingerprint="firefox",
        server_name="www.bing.com",
        public_key="public",
        short_id="0123456789abcdef",
        path="/sg-xhttp-reality",
        encryption=ENCRYPTION,
    )
    query = parse_qs(urlsplit(link).query)
    assert query["flow"] == ["xtls-rprx-vision"]
    assert query["mode"] == ["stream-one"]
    assert query["encryption"] == [ENCRYPTION]


def test_xmux_presets_stay_exact_current_panel_contract() -> None:
    assert xmux.XMUX_STANDARD_PRESET == {
        "maxConnections": "2-4",
        "cMaxReuseTimes": "300-600",
        "hMaxRequestTimes": "1000-2000",
        "hMaxReusableSecs": "1200-2400",
        "hKeepAlivePeriod": 600,
    }
    assert xmux.XMUX_REDUCED_PRESET == {
        "maxConcurrency": 0,
        "maxConnections": "6",
        "cMaxReuseTimes": 0,
        "hMaxRequestTimes": "600-900",
        "hMaxReusableSecs": "1800-3000",
        "hKeepAlivePeriod": 0,
    }


def _profiles_for_tls(mode: str = "stream-up") -> dict:
    return {
        "profiles": [
            SimpleNamespace(id="reality_tcp", enabled=False, ready=False, tls_required=False, port=443, path="", mode=""),
            SimpleNamespace(id="xhttp_reality", enabled=False, ready=False, tls_required=False, port=8444, path="/sg-xhttp-reality", mode="stream-one"),
            SimpleNamespace(id="xhttp_tls", enabled=True, ready=True, tls_required=True, port=8445, path="/sg-xhttp-tls", mode=mode),
            SimpleNamespace(id="hysteria2", enabled=False, ready=False, tls_required=True, port=8446, path="", mode=""),
        ],
        "tls_ready": True,
        "tls_domain": "vpn.example.com",
    }


def test_xhttp_tls_runtime_matches_panel_local_plain_xray(monkeypatch) -> None:
    monkeypatch.setattr(client_runtime, "normalize_pair", lambda encryption, decryption: (str(encryption), str(decryption), False))
    monkeypatch.setattr(client_runtime, "_read_env", lambda path: {
        "SG_GATEWAY_XRAY_PRIVATE_KEY": "private",
        "SG_GATEWAY_XRAY_SHORT_ID": "0123456789abcdef",
        "SG_GATEWAY_VLESS_ENCRYPTION": ENCRYPTION,
        "SG_GATEWAY_VLESS_DECRYPTION": DECRYPTION,
        "SG_GATEWAY_REALITY_SNI": "www.bing.com",
        "SG_GATEWAY_REALITY_TARGET": "www.bing.com:443",
    })
    monkeypatch.setattr(
        client_runtime,
        "get_connection_settings",
        lambda engine: SimpleNamespace(
            config={"server_name": "www.bing.com", "target": "www.bing.com:443"},
            host="203.0.113.10",
            port=443,
        ),
    )
    monkeypatch.setattr(client_runtime, "xray_profiles_overview", lambda: _profiles_for_tls("stream-up"))
    monkeypatch.setattr(
        client_runtime,
        "_sync_xray_tls_material",
        lambda domain: (_ for _ in ()).throw(AssertionError("XHTTP-TLS must not copy TLS into Xray")),
    )
    row = {
        "client_id": 1,
        "client_name": "Parity",
        "engine_object_id": "11111111-1111-1111-1111-111111111111",
        "config_json": json.dumps({"uuid": "11111111-1111-1111-1111-111111111111", "profiles": ["xhttp_tls"]}),
    }
    payload = json.loads(client_runtime._render_xray_config([row]))
    inbound = next(item for item in payload["inbounds"] if item["tag"] == "sg-vless-xhttp-tls")
    assert inbound["listen"] == "127.0.0.1"
    assert inbound["settings"]["decryption"] == DECRYPTION
    assert inbound["settings"]["clients"][0]["flow"] == "xtls-rprx-vision"
    stream = inbound["streamSettings"]
    assert stream["network"] == "xhttp"
    assert stream["security"] == "none"
    assert "tlsSettings" not in stream
    assert stream["xhttpSettings"] == {"path": "/sg-xhttp-tls", "mode": "stream-up"}
    assert stream["sockopt"] == {"trustedXForwardedFor": ["127.0.0.1"]}


def test_xhttp_tls_auto_mode_is_server_default_not_forced_field(monkeypatch) -> None:
    monkeypatch.setattr(client_runtime, "normalize_pair", lambda encryption, decryption: (str(encryption), str(decryption), False))
    monkeypatch.setattr(client_runtime, "_read_env", lambda path: {
        "SG_GATEWAY_XRAY_PRIVATE_KEY": "private",
        "SG_GATEWAY_XRAY_SHORT_ID": "0123456789abcdef",
        "SG_GATEWAY_VLESS_ENCRYPTION": ENCRYPTION,
        "SG_GATEWAY_VLESS_DECRYPTION": DECRYPTION,
    })
    monkeypatch.setattr(
        client_runtime,
        "get_connection_settings",
        lambda engine: SimpleNamespace(config={}, host="203.0.113.10", port=443),
    )
    monkeypatch.setattr(client_runtime, "xray_profiles_overview", lambda: _profiles_for_tls("auto"))
    row = {
        "client_id": 1,
        "client_name": "Parity",
        "engine_object_id": "11111111-1111-1111-1111-111111111111",
        "config_json": json.dumps({"uuid": "11111111-1111-1111-1111-111111111111", "profiles": ["xhttp_tls"]}),
    }
    payload = json.loads(client_runtime._render_xray_config([row]))
    inbound = next(item for item in payload["inbounds"] if item["tag"] == "sg-vless-xhttp-tls")
    assert inbound["streamSettings"]["xhttpSettings"] == {"path": "/sg-xhttp-tls"}


def test_xhttp_tls_client_uri_matches_panel_fields() -> None:
    link = xhttp_tls_link(
        uuid="11111111-1111-1111-1111-111111111111",
        host="vpn.example.com",
        port=443,
        title="TLS",
        fingerprint="firefox",
        server_name="vpn.example.com",
        path="/sg-xhttp-tls",
        encryption=ENCRYPTION,
        client_mode="stream-up",
        xmux=xmux.XMUX_STANDARD_PRESET,
    )
    parsed = urlsplit(link)
    query = parse_qs(parsed.query)
    assert parsed.hostname == "vpn.example.com"
    assert parsed.port == 443
    assert query["type"] == ["xhttp"]
    assert query["security"] == ["tls"]
    assert query["flow"] == ["xtls-rprx-vision"]
    assert query["sni"] == ["vpn.example.com"]
    assert query["host"] == ["vpn.example.com"]
    assert query["path"] == ["/sg-xhttp-tls"]
    assert query["mode"] == ["stream-up"]
    assert query["encryption"] == [ENCRYPTION]
    assert "alpn" not in query
    extra = json.loads(query["extra"][0])
    assert extra["xmux"] == xmux.XMUX_STANDARD_PRESET


def test_nginx_front_is_panel_style_h2_path_to_local_xray() -> None:
    snippet = render_snippet(enabled=True, path="/sg-xhttp-tls", port=8445)
    assert MARKER in snippet
    assert "location /sg-xhttp-tls/ {" in snippet
    assert "grpc_socket_keepalive on;" in snippet
    assert "grpc_pass grpc://127.0.0.1:8445;" in snippet
    assert "proxy_pass" not in snippet

    site = """server {
    listen 127.0.0.1:7444 ssl;
    server_name vpn.example.com;
    location / { return 404; }
}
server { listen 63443 ssl; }
"""
    updated = ensure_site_contract(site, enable_http2=True)
    assert "listen 127.0.0.1:7444 ssl http2;" in updated
    assert updated.count(INCLUDE_DIRECTIVE) == 1
    first_server = updated.split("server { listen 63443 ssl; }", 1)[0]
    assert INCLUDE_DIRECTIVE in first_server
    assert ensure_site_contract(updated, enable_http2=True) == updated


def test_https_generator_and_updater_carry_parity_contract() -> None:
    access = (ROOT / "deploy/configure-panel-access.sh").read_text(encoding="utf-8")
    assert 'XHTTP_TLS_SNIPPET="/etc/nginx/snippets/sg-gateway-xhttp-tls.conf"' in access
    assert "listen 127.0.0.1:$PLACEHOLDER_TLS_INTERNAL_PORT ssl http2;" in access
    assert "include /etc/nginx/snippets/sg-gateway-xhttp-tls.conf;" in access
    updater = (ROOT / "deploy/update-from-github.sh").read_text(encoding="utf-8")
    assert updater.splitlines()[:5] == ["#!/usr/bin/env bash", "set -Eeuo pipefail", "", "# The updater replaces /opt/sg-gateway. Never inherit a cwd inside that tree.", "cd /"]
