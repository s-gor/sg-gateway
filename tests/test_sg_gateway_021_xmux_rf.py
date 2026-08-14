from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from app.xray import profiles as profiles_module
from app.xray.profiles import XHTTP_XMUX_REDUCED, XHTTP_XMUX_STANDARD, _values
from app.xray.sg_panel_vless import reality_tcp_link, xhttp_reality_link

ROOT = Path(__file__).resolve().parents[1]


def test_standard_xmux_values_match_sg_panel_exactly():
    assert XHTTP_XMUX_STANDARD == {
        "maxConnections": "2-4",
        "cMaxReuseTimes": "300-600",
        "hMaxRequestTimes": "1000-2000",
        "hMaxReusableSecs": "1200-2400",
        "hKeepAlivePeriod": 600,
    }


def test_reduced_xmux_is_retained_as_non_default_reference_preset():
    assert XHTTP_XMUX_REDUCED == {
        "maxConcurrency": 0,
        "maxConnections": 6,
        "cMaxReuseTimes": 0,
        "hMaxRequestTimes": "600-900",
        "hMaxReusableSecs": "1800-3000",
        "hKeepAlivePeriod": 0,
    }


def test_standard_xmux_is_enabled_by_default_for_both_xhttp_profiles(monkeypatch):
    values = _values({}, 443)
    assert values["xhttp_reality_xmux_enabled"] is True
    assert values["xhttp_tls_xmux_enabled"] is True

    settings = SimpleNamespace(host="203.0.113.10", port=443)
    config = {
        "public_key": "public-key",
        "short_id": "0123456789abcdef",
        "vless_encryption": "mlkem768x25519plus.native.0rtt.example",
    }
    monkeypatch.setattr(
        profiles_module,
        "_config",
        lambda: (settings, config, {"https_ready": True, "domain": "vpn.example"}),
    )
    monkeypatch.setattr(profiles_module, "_service_active", lambda: False)
    monkeypatch.setattr(profiles_module, "_installed_xray_version", lambda: "26.6.27")
    monkeypatch.setattr(profiles_module, "_vless_encryption_ready", lambda value: True)

    state = profiles_module.overview()
    by_id = {item.id: item for item in state["profiles"]}
    assert by_id["xhttp_reality"].xmux == XHTTP_XMUX_STANDARD
    assert by_id["xhttp_tls"].xmux == XHTTP_XMUX_STANDARD
    assert state["xhttp_xmux_standard"] == XHTTP_XMUX_STANDARD
    assert state["xhttp_xmux_reduced"] == XHTTP_XMUX_REDUCED


def test_xhttp_reality_link_contains_standard_url_encoded_json_extra(monkeypatch):
    monkeypatch.delenv("SG_GATEWAY_PUBLIC_ADDRESS", raising=False)
    link = xhttp_reality_link(
        uuid="11111111-1111-4111-8111-111111111111",
        host="203.0.113.10",
        port=8444,
        title="XMUX Standard",
        fingerprint="firefox",
        server_name="www.microsoft.com",
        public_key="public-key",
        short_id="0123456789abcdef",
        path="/sg-xhttp-reality",
        encryption="mlkem768x25519plus.native.0rtt.example",
        client_mode="stream-one",
        xmux=XHTTP_XMUX_STANDARD,
    )
    query = parse_qs(urlsplit(link).query)
    assert json.loads(query["extra"][0]) == {"xmux": XHTTP_XMUX_STANDARD}


def test_reality_links_prefer_direct_public_address_over_passed_domain(monkeypatch):
    direct_ip = "203.0.113.77"
    monkeypatch.setenv("SG_GATEWAY_PUBLIC_ADDRESS", direct_ip)

    tcp = reality_tcp_link(
        uuid="11111111-1111-4111-8111-111111111111",
        host="vpn.example",
        port=443,
        title="Reality TCP",
        fingerprint="firefox",
        server_name="www.bing.com",
        public_key="public-key",
        short_id="0123456789abcdef",
    )
    xhttp = xhttp_reality_link(
        uuid="11111111-1111-4111-8111-111111111111",
        host="vpn.example",
        port=8444,
        title="XHTTP Reality",
        fingerprint="firefox",
        server_name="www.bing.com",
        public_key="public-key",
        short_id="0123456789abcdef",
        path="/sg-xhttp-reality",
        encryption="mlkem768x25519plus.native.0rtt.example",
        client_mode="stream-one",
        xmux=XHTTP_XMUX_STANDARD,
    )

    assert urlsplit(tcp).hostname == direct_ip
    assert urlsplit(xhttp).hostname == direct_ip
    assert "vpn.example" not in tcp
    assert "vpn.example" not in xhttp


def test_reality_links_keep_explicit_host_when_direct_address_is_unset(monkeypatch):
    monkeypatch.delenv("SG_GATEWAY_PUBLIC_ADDRESS", raising=False)
    link = reality_tcp_link(
        uuid="11111111-1111-4111-8111-111111111111",
        host="vpn.example",
        port=443,
        title="Reality TCP",
        fingerprint="firefox",
        server_name="www.bing.com",
        public_key="public-key",
        short_id="0123456789abcdef",
    )
    assert urlsplit(link).hostname == "vpn.example"


def test_xmux_is_client_only_and_standard_is_the_default_source():
    template = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    profiles = (ROOT / "app/xray/profiles.py").read_text(encoding="utf-8")
    inbound = (ROOT / "app/xray/sg_panel_vless.py").read_text(encoding="utf-8")
    exports = (ROOT / "app/clients/exports.py").read_text(encoding="utf-8")

    assert "Клиентский XMUX" in template
    assert "xps2-xmux-switch" not in template
    assert "_xmux_enabled" not in template
    assert "Показать параметры" in template
    assert "Максимальная параллельность" in template
    assert "XHTTP_XMUX_STANDARD" in profiles
    assert "xmux=dict(XHTTP_XMUX_STANDARD)" in profiles
    for key in (
        "maxConcurrency",
        "maxConnections",
        "cMaxReuseTimes",
        "hMaxRequestTimes",
        "hMaxReusableSecs",
        "hKeepAlivePeriod",
    ):
        assert key in template
        assert key in profiles
    assert '"xmux": dict(xmux)' in inbound
    assert 'query_values["extra"]' in exports
    server_function = inbound.split("def xhttp_reality_inbound", 1)[1].split(
        "def reality_tcp_link", 1
    )[0]
    assert '"xmux"' not in server_function
