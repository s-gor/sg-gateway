from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_connections_restores_balanced_awg_mihomo_pair() -> None:
    css = _text("app/web/static/sg-preview28-final.css")
    assert "Mihomo as a separate full-width Connections block" not in css
    assert "grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);" in css
    assert ".cnv1-engine-pair { align-items: stretch; }" in css
    assert ".cnv1-engine-awg .cnv1-form-actions { margin-top: auto; }" in css


def test_xhttp_rows_are_compact_without_losing_current_xmux_ui() -> None:
    template = _text("app/web/templates/connections.html")
    css = _text("app/web/static/sg-xray-profiles-v2.css")
    xmux_css = _text("app/web/static/sg-xmux-settings-v1.css")
    row_start = template.index('<div class="xps2-parameter-list">')
    row_end = template.index('<p class="xps2-empty-note"', row_start)
    row_block = template[row_start:row_end]
    assert "{{ 'has-xhttp' if profile.mode else '' }}" in row_block
    assert 'class="xps2-port-field"' in row_block
    assert 'class="xps2-flow-field xps2-encryption-field"' in row_block
    assert 'class="xps2-path-field"' in row_block
    assert "XHTTP mode клиента" not in row_block
    assert "xps2-xmux" in row_block
    assert "restored Connections polish over accepted XMUX/Gecko UI" in css
    assert ".xps2-parameter-row.has-xhttp" in css
    assert '{% include "_xray_xmux_settings.html" %}' in template
    assert ".xps2-xmux" in xmux_css and "display: none" in xmux_css


def test_xhttp_mode_moves_to_single_collapsed_expert_section() -> None:
    template = _text("app/web/templates/connections.html")
    assert template.count('class="cnv1-advanced sg-ljd-nested xps2-xhttp-expert"') == 1
    assert "Экспертные настройки XHTTP" in template
    assert "Обычно не требуются" in template
    assert 'data-xhttp-mode-profile="{{ profile.id }}"' in template
    assert 'select name="{{ profile.id }}_mode"' in template
    assert "xps2-xhttp-mode-grid" in _text("app/web/static/sg-xray-profiles-v2.css")


def test_current_gecko_and_sg_panel_xmux_contract_survive_polish() -> None:
    template = _text("app/web/templates/connections.html")
    js = _text("app/web/static/sg-xmux-settings-v1.js")
    partial = _text("app/web/templates/_xray_xmux_settings.html")
    assert "Hysteria2 Obfuscation" in template
    assert 'value="gecko"' in template
    assert "Gecko · рекомендуется" in template
    assert "XMUX для XHTTP" in partial
    assert "Стандартный" in partial
    assert "Для РФ — уменьшенный" in partial
    assert "Ручной" in partial
    assert "stream-one" in js
    assert "hidden.name = 'xhttp_reality_mode'" in js


def test_connections_polish_is_declared_ui_only() -> None:
    manifest = json.loads(_text("release-manifest.json"))
    feature = manifest["development_feature"]
    assert feature["id"] == "connections-polish-r1"
    assert feature["scope"] == "ui-only"
    assert feature["runtime_changes"] is False
    assert feature["source_branch"] == "agent/restore-connections-polish-20260814"
    assert feature["source_ci_run"] == 31818719737
    assert set(feature["preserves"]) == {"gecko", "sg-panel-xmux", "vpn-runtime"}
