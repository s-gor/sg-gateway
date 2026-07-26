from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_connections_uses_compact_xmux_and_full_width_mihomo():
    template = (ROOT / "app/web/templates/connections.html").read_text(
        encoding="utf-8"
    )
    xray_css = (ROOT / "app/web/static/sg-xray-profiles-v2.css").read_text(
        encoding="utf-8"
    )
    layout_css = (ROOT / "app/web/static/sg-preview28-final.css").read_text(
        encoding="utf-8"
    )

    assert "<strong>XMUX для РФ</strong>" in template
    assert "Показать параметры" in template
    assert "xps2-xmux-switch" not in template
    assert "compact client-only XMUX preset for Russian networks" in xray_css
    assert "Mihomo as a separate full-width Connections block" in layout_css
    assert "grid-template-columns: minmax(0, 1fr) !important" in layout_css


def test_client_detail_uses_routing_frame_and_title_size():
    css = (ROOT / "app/web/static/sg-page-frame-routing-v1.css").read_text(
        encoding="utf-8"
    )

    assert "client detail uses the exact Routing page frame" in css
    assert ".dv16-page" in css
    assert ".dv16-heading h1" in css
    assert "font-size: 27px !important" in css


def test_russian_publication_files_are_present():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    docs = (ROOT / "docs/README.md").read_text(encoding="utf-8")

    for marker in (
        "Самостоятельная веб-панель",
        "Установка из GitHub",
        "Обновление",
        "Полное удаление",
        "XMUX для РФ",
        "Документация",
    ):
        assert marker in readme

    assert "Документация SG-Gateway" in docs
    assert "INSTALLATION.md" in docs
    assert "security.md" in docs
