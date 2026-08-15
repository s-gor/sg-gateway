from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "app/web/templates/base.html"
OLD_CSS = ROOT / "app/web/static/sg-full-backup-v1.css"
COLORS = ROOT / "app/web/static/sg-full-backup-button-colors-r2.css"
MAINTENANCE = ROOT / "app/web/templates/maintenance.html"


def test_full_backup_color_override_is_loaded_after_global_luxury_jade() -> None:
    base = BASE.read_text(encoding="utf-8")
    luxury = base.index("sg-luxury-jade-depth-v2.css")
    controls = base.index("sg-controls-final-v1.css")
    colors = base.index("sg-full-backup-button-colors-r2.css")
    head_end = base.index("</head>")
    assert luxury < colors < head_end
    assert controls < colors < head_end
    assert "active_page|default('') == 'maintenance'" in base[colors - 160:colors]
    assert "?v={{ app_version }}-full-backup-colors-r2" in base


def test_full_backup_color_override_has_stronger_scoped_selectors_and_exact_historical_values() -> None:
    css = COLORS.read_text(encoding="utf-8")
    assert 'html[data-theme="light"] body.page-maintenance .sg-full-restore-actions .button.sg-full-verify-button {' in css
    assert "var(--sg-blue) 13%,var(--sg-panel)) !important" in css
    assert 'html[data-theme="light"] body.page-maintenance .sg-full-restore-actions .button[data-sg-full-restore-button] {' in css
    assert "var(--sg-yellow) 44%,#8a5b30)" in css
    assert "var(--sg-yellow) 31%,#6b4427)) !important" in css
    assert "color: #fff5df !important" in css
    assert '.button.sg-full-restore-button:disabled {' in css
    assert "opacity: .46 !important" in css


def test_r1_dead_override_is_removed_and_buttons_keep_required_hooks() -> None:
    old_css = OLD_CSS.read_text(encoding="utf-8")
    template = MAINTENANCE.read_text(encoding="utf-8")
    assert "preserve historical Full Backup semantic button colors in Luxury Jade light theme" not in old_css
    assert 'class="button sg-full-restore-button sg-full-verify-button"' in template
    assert "data-sg-full-verify-button" in template
    assert 'class="button mtv2-restore sg-full-restore-button"' in template
    assert "data-sg-full-restore-button" in template
