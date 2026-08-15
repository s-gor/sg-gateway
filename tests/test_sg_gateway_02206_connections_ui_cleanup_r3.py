from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XMUX_TEMPLATE = (ROOT / "app/web/templates/_xray_xmux_settings.html").read_text(encoding="utf-8")
XMUX_CSS = (ROOT / "app/web/static/sg-xmux-settings-v1.css").read_text(encoding="utf-8")
CONTROLS_CSS = (ROOT / "app/web/static/sg-controls-final-v1.css").read_text(encoding="utf-8")


def test_redundant_xmux_info_cards_are_removed():
    assert 'class="xmux1-contract"' not in XMUX_TEMPLATE
    assert 'Client mode: stream-one' not in XMUX_TEMPLATE
    assert '<strong>Только клиент</strong>' not in XMUX_TEMPLATE


def test_rf_card_keeps_only_useful_parameters():
    assert 'Для РФ · эксперимент 2026' in XMUX_TEMPLATE
    assert 'keepalive 0.' in XMUX_TEMPLATE
    assert 'Это экспериментальный профиль, не upstream default.' not in XMUX_TEMPLATE


def test_xmux_mode_cards_have_equal_geometry():
    assert 'align-items: stretch' in XMUX_CSS
    assert '.xmux1-mode {' in XMUX_CSS
    assert 'display: flex' in XMUX_CSS
    assert 'height: 100%' in XMUX_CSS
    assert 'box-sizing: border-box' in XMUX_CSS
    assert '.xmux1-contract' not in XMUX_CSS


def test_connections_actions_share_one_button_size():
    assert 'Connections action sizing R3' in CONTROLS_CSS
    assert 'width: 180px !important' in CONTROLS_CSS
    assert 'min-height: 42px !important' in CONTROLS_CSS
    assert 'flex-wrap: wrap !important' in CONTROLS_CSS
