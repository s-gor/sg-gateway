from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from app.xray import profiles as profiles_module
from app.xray.profiles import _values
from app.xray.sg_panel_vless import reality_tcp_link, xhttp_reality_link
from app.xray.xmux import (
    XHTTP_XMUX_REDUCED,
    XHTTP_XMUX_STANDARD,
    XmuxError,
    normalise_expert,
    resolve,
)

ROOT = Path(__file__).resolve().parents[1]


def test_sg_panel_compatibility_presets_are_exact():
    assert XHTTP_XMUX_STANDARD == {
        "maxConnections": "2-4",
        "cMaxReuseTimes": "300-600",
        "hMaxRequestTimes": "1000-2000",
        "hMaxReusableSecs": "1200-2400",
        "hKeepAlivePeriod": 600,
    }
    assert XHTTP_XMUX_REDUCED == {
        "maxConcurrency": 0,
        "maxConnections": 6,
        "cMaxReuseTimes": 0,
        "hMaxRequestTimes": "600-900",
        "hMaxReusableSecs": "1800-3000",
        "hKeepAlivePeriod": 0,
    }


def test_native_xray_auto_is_default_and_does_not_force_extra_xmux():
    values = _values({}, 443)
    assert values["xhttp_xmux_mode"] == "auto"
    assert values["xhttp_xmux_effective"] is None


def test_overview_uses_no_client_xmux_in_native_auto(monkeypatch):
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
    assert state["xhttp_xmux_mode"] == "auto"
    assert state["xhttp_xmux_effective"] is None
    assert by_id["xhttp_reality"].xmux_enabled is False
    assert by_id["xhttp_reality"].xmux is None
    assert by_id["xhttp_tls"].xmux_enabled is False
    assert by_id["xhttp_tls"].xmux is None


def test_optional_presets_resolve_only_when_selected():
    assert resolve({"xhttp_xmux_mode": "standard"})[2] == XHTTP_XMUX_STANDARD
    assert resolve({"xhttp_xmux_mode": "reduced"})[2] == XHTTP_XMUX_REDUCED


def test_manual_xmux_accepts_ranges_and_blocks_conflicting_positive_controllers():
    manual = normalise_expert(
        {
            "maxConcurrency": 0,
            "maxConnections": "2-4",
            "cMaxReuseTimes": "300-600",
            "hMaxRequestTimes": "600-900",
            "hMaxReusableSecs": "1800-3000",
            "hKeepAlivePeriod": 0,
        },
        require_non_empty=True,
    )
    assert manual["maxConnections"] == "2-4"
    assert manual["hKeepAlivePeriod"] == 0

    with pytest.raises(XmuxError, match="положительные maxConnections и maxConcurrency"):
        normalise_expert(
            {"maxConcurrency": "8-16", "maxConnections": 6},
            require_non_empty=True,
        )


def test_xhttp_reality_native_auto_link_has_no_extra(monkeypatch):
    monkeypatch.delenv("SG_GATEWAY_PUBLIC_ADDRESS", raising=False)
    link = xhttp_reality_link(
        uuid="11111111-1111-4111-8111-111111111111",
        host="203.0.113.10",
        port=8444,
        title="XMUX Native Auto",
        fingerprint="firefox",
        server_name="www.microsoft.com",
        public_key="public-key",
        short_id="0123456789abcdef",
        path="/sg-xhttp-reality",
        encryption="mlkem768x25519plus.native.0rtt.example",
        client_mode="stream-one",
        xmux=None,
    )
    query = parse_qs(urlsplit(link).query)
    assert "extra" not in query


def test_xhttp_reality_selected_standard_link_contains_extra(monkeypatch):
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
        xmux=None,
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


def test_xmux_ui_exposes_auto_presets_and_manual_without_forcing_rf():
    template = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    inbound = (ROOT / "app/xray/sg_panel_vless.py").read_text(encoding="utf-8")

    xmux_model = (ROOT / "app/xray/xmux.py").read_text(encoding="utf-8")
    assert 'name="xhttp_xmux_mode"' in template
    assert "xhttp_xmux_mode_options" in template
    for label in ("Xray Auto", "Standard", "Для РФ — уменьшенный", "Ручной"):
        assert label in xmux_model
    for key in (
        "maxConcurrency",
        "maxConnections",
        "cMaxReuseTimes",
        "hMaxRequestTimes",
        "hMaxReusableSecs",
        "hKeepAlivePeriod",
    ):
        assert key in template
    assert "Рекомендуемый профиль для российских сетей" not in template
    assert "XMUX для РФ</strong>" not in template
    server_function = inbound.split("def xhttp_reality_inbound", 1)[1].split(
        "def reality_tcp_link", 1
    )[0]
    assert '"xmux"' not in server_function
