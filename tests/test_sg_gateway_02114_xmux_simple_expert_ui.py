from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_normal_xray_rows_do_not_show_xhttp_tuning_controls() -> None:
    body = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    parameter_start = body.index('<div class="xps2-parameter-list">')
    expert_start = body.index('Экспертные настройки XHTTP')
    normal = body[parameter_start:expert_start]
    assert "XHTTP mode клиента" not in normal
    assert 'data-xmux-mode' not in normal
    assert "Технические значения пресетов" not in body


def test_xhttp_modes_and_xmux_live_inside_one_expert_line() -> None:
    body = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    expert_start = body.index('Экспертные настройки XHTTP')
    footer = body.index('<footer class="xps2-actions">', expert_start)
    expert = body[expert_start:footer]
    assert 'name="{{ profile.id }}_mode"' in expert
    assert 'name="xhttp_xmux_mode"' in expert
    assert 'data-xmux-manual' in expert
    assert 'Xray Auto — рекомендуемый вариант' in expert


def test_manual_xmux_fields_stay_hidden_until_manual_mode() -> None:
    body = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    assert 'data-xmux-manual {% if xray_profiles.xhttp_xmux_mode != \'expert\' %}hidden{% endif %}' in body
    assert 'xmuxManual.hidden = !manual;' in body
