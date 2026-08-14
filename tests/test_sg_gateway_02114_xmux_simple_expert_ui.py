from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_xmux_normal_view_is_simple_and_recommended() -> None:
    body = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    assert "Автоматически · рекомендуется" in body
    assert "Для обычной работы ничего менять не нужно." in body
    assert "Экспертные настройки XMUX" in body
    assert body.index("Экспертные настройки XMUX") < body.index('name="xhttp_xmux_mode"')


def test_xmux_technical_values_are_nested_under_expert_controls() -> None:
    body = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    assert "Технические значения пресетов" in body
    assert body.index("Экспертные настройки XMUX") < body.index("Технические значения пресетов")
    assert body.index("Технические значения пресетов") < body.index("Standard · SG-Panel")
    assert 'data-xmux-manual {% if xray_profiles.xhttp_xmux_mode != \'expert\' %}hidden{% endif %}' in body


def test_xmux_custom_mode_reopens_expert_section_without_resetting_choice() -> None:
    body = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    assert '<details class="xps2-xmux-details" {% if xray_profiles.xhttp_xmux_mode != \'auto\' %}open{% endif %}>' in body
    assert 'value="{{ item.value }}" {% if item.value == xray_profiles.xhttp_xmux_mode %}selected{% endif %}' in body
    assert "xmuxManual.hidden = !manual;" in body
