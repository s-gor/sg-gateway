from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_main_readme_puts_no_https_bundle_on_first_page():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    head = "\n".join(text.splitlines()[:80])
    assert "## Что работает сразу, без HTTPS" in head
    for item in (
        "AmneziaWG",
        "VLESS Reality TCP",
        "VLESS XHTTP Reality",
        "Mieru",
        "SG Client subscription",
        "VLESS XHTTP TLS",
        "Hysteria 2",
        "AnyTLS",
        "TUIC v5",
    ):
        assert item in head
    assert "не Linux-пользователь" in head


def test_clients_panel_explains_and_preselects_no_https_bundle():
    text = (ROOT / "app/web/templates/clients.html").read_text(encoding="utf-8")
    assert "Без HTTPS сразу доступны AmneziaWG, VLESS Reality TCP, VLESS XHTTP Reality, Mieru и SG Client" in text
    assert 'value="amneziawg" checked' in text
    assert "profile.id in ['reality_tcp', 'xhttp_reality']" in text
    assert 'value="mihomo" checked' in text
    assert 'value="sgclient" checked' in text
    assert "После HTTPS в Security можно добавить VLESS XHTTP TLS, Hysteria 2, AnyTLS и TUIC v5" in text


def test_device_dialog_uses_same_recommended_bundle():
    text = (ROOT / "app/web/templates/client_detail.html").read_text(encoding="utf-8")
    assert "AmneziaWG, VLESS Reality TCP, VLESS XHTTP Reality, Mieru" in text
    assert 'value="amneziawg" checked' in text
    assert "profile.id in ['reality_tcp', 'xhttp_reality']" in text
    assert 'value="mihomo" checked' in text
    assert 'name="protocols" value="sgclient"' in text


def test_repository_recommended_alias_matches_no_https_bundle():
    text = (ROOT / "app/clients/repository.py").read_text(encoding="utf-8")
    assert '"recommended": "amneziawg,xray_reality_tcp,xray_xhttp_reality,mihomo,sgclient"' in text


def test_help_states_certificate_boundary():
    text = (ROOT / "app/web/templates/help.html").read_text(encoding="utf-8")
    assert "Без HTTPS панель сразу предлагает AmneziaWG, VLESS Reality TCP, VLESS XHTTP Reality, Mieru и SG Client" in text
    assert "VLESS XHTTP TLS, Hysteria 2, AnyTLS и TUIC v5" in text
