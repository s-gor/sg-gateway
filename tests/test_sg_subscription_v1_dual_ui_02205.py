from pathlib import Path
import os
import subprocess

from flask import Flask, render_template_string

from app.clients.repository import Client
from app.clients import sg_subscription_http_v4 as http


ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / "deploy" / "sg-gateway-sg-subscription-native-ui.sh"
PARTIAL = ROOT / "app" / "web" / "templates" / "_sg_subscription_dual.html"
CSS = ROOT / "app" / "web" / "static" / "sg-subscription-verified-v1.css"


def _client():
    return Client(7, "Shany", True, None, "applied", "applied", "applied", "applied", "applied", "applied", 1, 1)


def _document(client):
    return {
        "format": "sg-subscription",
        "version": 1,
        "scope": "client",
        "client": {"id": client.id, "name": client.name},
        "summary": {"devices": 1, "profiles_assigned": 9, "profiles_ready": 9},
        "devices": [],
    }


def _app(monkeypatch, base="https://vpn.example/sg/sub/v1/sg1_clientwide"):
    client = _client()
    monkeypatch.setattr(http, "get_client", lambda client_id: client if client_id == client.id else None)
    monkeypatch.setattr(http, "get_client_by_subscription_token", lambda token: client)
    monkeypatch.setattr(http, "build_sg_subscription_url", lambda item: base)
    monkeypatch.setattr(http, "build_sg_subscription_document", _document)
    app = Flask(__name__)
    http.register_sg_subscription(app)
    return app, client, base


def test_v4_serves_bare_compatible_and_explicit_sg_native(monkeypatch):
    app, _, _ = _app(monkeypatch)
    monkeypatch.setattr(http, "build_compatible_subscription_body", lambda item: "Q09NUEFUSUJMRQo=")
    monkeypatch.setattr(http, "build_sg_subscription_text", lambda item: "# SG-SUBSCRIPTION/1\n")

    client = app.test_client()
    bare = client.get("/sg/sub/v1/sg1_example")
    native = client.get("/sg/sub/v1/sg1_example?format=sg")
    structured = client.get("/sg/sub/v1/sg1_example?format=json")

    assert bare.status_code == 200
    assert bare.get_data(as_text=True) == "Q09NUEFUSUJMRQo="
    assert native.status_code == 200
    assert native.get_data(as_text=True) == "# SG-SUBSCRIPTION/1\n"
    assert structured.status_code == 200
    assert structured.get_json()["summary"]["profiles_ready"] == 9


def test_v4_info_exposes_both_urls_without_breaking_historical_fields(monkeypatch):
    app, client, base = _app(monkeypatch)

    response = app.test_client().get(f"/api/clients/{client.id}/sg-subscription-v1")
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["universal_url"] == base
    assert payload["compat_url"] == base
    assert payload["native_url"] == base + "?format=sg"
    assert payload["url"] == base + "?format=sg"
    assert payload["json_url"] == base + "?format=json"


def test_v4_has_separate_universal_and_native_qr_contracts(monkeypatch):
    app, client, base = _app(monkeypatch)
    monkeypatch.setattr(http, "build_qr_svg", lambda value: f"<svg>{value}</svg>")

    browser = app.test_client()
    universal = browser.get(f"/clients/{client.id}/sg-subscription-v1/qr/universal")
    native = browser.get(f"/clients/{client.id}/sg-subscription-v1/qr")

    assert universal.status_code == 200
    assert base.encode() in universal.data
    assert b"?format=sg" not in universal.data

    assert native.status_code == 200
    assert (base + "?format=sg").encode() in native.data

    with app.test_request_context("/"):
        rendered = render_template_string(
            "{{ sg_subscription_universal_url(client) }}|{{ sg_subscription_native_url(client) }}",
            client=client,
        )
    assert rendered == base + "|" + base + "?format=sg"


def test_dual_ui_partial_has_exact_two_subscription_formats_and_distinct_actions():
    html = PARTIAL.read_text(encoding="utf-8")

    assert 'data-sg-subscription-format="universal"' in html
    assert 'data-sg-subscription-format="native"' in html
    assert html.count("data-sg-subscription-format=") == 2
    assert "Универсальная подписка" in html
    assert "SG Client / SG Mobile" in html
    assert "sg-subscription-copy-universal" in html
    assert "sg-subscription-copy-native" in html
    assert '/clients/{{ client.id }}/sg-subscription-v1/qr/universal' in html
    assert '/clients/{{ client.id }}/sg-subscription-v1/qr' in html
    assert "url_for('sg_subscription_v1" not in html
    assert 'url_for("sg_subscription_v1' not in html
    assert "SG-CONFIG" in html


def test_live_ui_patcher_removes_old_large_single_block_even_when_dual_ui_already_exists(tmp_path):
    template_dir = tmp_path / "app" / "web" / "templates"
    template_dir.mkdir(parents=True)
    (template_dir / "_sg_subscription_dual.html").write_text(
        PARTIAL.read_text(encoding="utf-8"), encoding="utf-8"
    )
    template = template_dir / "client_detail.html"
    template.write_text(
        (
            '{% extends "base.html" %}\n'
            '  {% set client_sg_subscription = sg_subscription_url(client) %}\n'
            '  {% if client_sg_subscription %}\n'
            '  <section class="dv16-subscription state-applied" data-sg-subscription-v1>\n'
            '    <strong>SG Subscription</strong>\n'
            '    <span>Одна подписка клиента для всех его устройств.</span>\n'
            '    <button>Скопировать SG Subscription</button>\n'
            '  </section>\n'
            '  {% endif %}\n\n'
            '  <!-- SG_SUBSCRIPTION_DUAL_UI_V1 -->\n'
            '  {% include "_sg_subscription_dual.html" %}\n\n'
            '  <section class="dv16-devices" aria-label="Устройства клиента">\n'
            '    <strong>Подписка устройства</strong>\n'
            '  </section>\n'
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["SG_GATEWAY_ROOT"] = str(tmp_path)
    result = subprocess.run(
        ["bash", str(PATCHER)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    patched = template.read_text(encoding="utf-8")
    assert patched.count("SG_SUBSCRIPTION_DUAL_UI_V1") == 1
    assert patched.count('{% include "_sg_subscription_dual.html" %}') == 1
    assert "client_sg_subscription = sg_subscription_url(client)" not in patched
    assert "Скопировать SG Subscription" not in patched
    assert "data-sg-subscription-v1" not in patched
    assert "Legacy SUB устройства" in patched


def test_dual_subscription_css_is_responsive_and_actions_have_distinct_colors():
    css = CSS.read_text(encoding="utf-8")
    assert ".sg-subscription-dual" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in css
    assert ".sg-subscription-copy-universal" in css
    assert ".sg-subscription-copy-native" in css
    assert "var(--sg-ok, #4f8f75)" in css
    assert "var(--sg-blue, #5b82a8)" in css
    assert "@media (max-width: 980px)" in css
    assert "@media (max-width: 760px)" in css
