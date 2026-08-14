from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_connections_restores_balanced_awg_mihomo_pair() -> None:
    css = (ROOT / "app/web/static/sg-preview28-final.css").read_text(encoding="utf-8")
    assert "Mihomo as a separate full-width Connections block" not in css
    assert "grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)" in css
    assert ".cnv1-engine-pair { align-items: stretch; }" in css
    assert ".cnv1-engine-awg .cnv1-form-actions { margin-top: auto; }" in css


def test_xhttp_rows_are_compact_on_wide_desktop() -> None:
    template = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    css = (ROOT / "app/web/static/sg-xray-profiles-v2.css").read_text(encoding="utf-8")
    assert "{{ 'has-xhttp' if profile.mode else '' }}" in template
    assert 'class="xps2-port-field"' in template
    assert 'class="xps2-flow-field xps2-encryption-field"' in template
    assert 'class="xps2-path-field"' in template
    assert ".xps2-parameter-row.has-xhttp" in css
    assert "restore polished Connections geometry" in css


def test_expert_tuning_is_a_single_collapsed_line() -> None:
    template = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    assert 'class="cnv1-advanced sg-ljd-nested xps2-xhttp-expert"' in template
    assert "Экспертные настройки XHTTP" in template
    assert "Обычно не требуются" in template
    assert "Технические значения пресетов" not in template
