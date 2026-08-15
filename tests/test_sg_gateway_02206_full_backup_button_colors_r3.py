from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "app/web/templates/base.html"
OLD_CSS = ROOT / "app/web/static/sg-full-backup-v1.css"
R2_CSS = ROOT / "app/web/static/sg-full-backup-button-colors-r2.css"
COLORS = ROOT / "app/web/static/sg-full-backup-button-colors-r3.css"
MAINTENANCE = ROOT / "app/web/templates/maintenance.html"


def test_r3_is_loaded_last_on_maintenance_with_new_cache_key() -> None:
    base = BASE.read_text(encoding="utf-8")
    luxury = base.index("sg-luxury-jade-depth-v2.css")
    controls = base.index("sg-controls-final-v1.css")
    colors = base.index("sg-full-backup-button-colors-r3.css")
    head_end = base.index("</head>")
    assert luxury < colors < head_end
    assert controls < colors < head_end
    assert "active_page|default('') == 'maintenance'" in base[colors - 160:colors]
    assert "?v={{ app_version }}-full-backup-colors-r3" in base
    assert "sg-full-backup-button-colors-r2.css" not in base


def test_r3_defines_real_semantic_colours_for_both_themes() -> None:
    css = COLORS.read_text(encoding="utf-8")
    assert 'html[data-theme="light"] body.page-maintenance {' in css
    assert 'html[data-theme="dark"] body.page-maintenance {' in css
    assert "--sg-full-verify-line: #6f9bc7" in css
    assert "--sg-full-verify-top: #edf5fd" in css
    assert "--sg-full-verify-text: #2f669b" in css
    assert "--sg-full-restore-top: #9d6b3b" in css
    assert "--sg-full-restore-bottom: #744a24" in css
    assert "--sg-full-verify-line: #5f91c2" in css
    assert "--sg-full-verify-top: #294f76" in css
    assert "--sg-full-verify-bottom: #1d3b5a" in css
    assert "--sg-full-restore-line: #bf8b48" in css
    assert "--sg-full-restore-top: #7a522b" in css
    assert "--sg-full-restore-bottom: #57391f" in css
    assert "var(--sg-blue)" not in css
    assert "var(--sg-yellow)" not in css


def test_r3_rules_beat_global_button_contract_and_disabled_state_keeps_colour() -> None:
    css = COLORS.read_text(encoding="utf-8")
    assert "body.page-maintenance .sg-full-restore-actions .button.sg-full-verify-button {" in css
    assert "background: linear-gradient(180deg," in css
    assert "var(--sg-full-verify-top)" in css
    assert "var(--sg-full-verify-bottom)) !important" in css
    assert "body.page-maintenance .sg-full-restore-actions .button[data-sg-full-restore-button] {" in css
    assert "var(--sg-full-restore-top)" in css
    assert "var(--sg-full-restore-bottom)) !important" in css
    assert ".button.sg-full-restore-button:disabled {" in css
    assert "opacity: .62 !important" in css
    assert "filter: saturate(.72) brightness(.96) !important" in css


def test_r2_dead_asset_is_removed_and_required_button_hooks_remain() -> None:
    old_css = OLD_CSS.read_text(encoding="utf-8")
    template = MAINTENANCE.read_text(encoding="utf-8")
    assert not R2_CSS.exists()
    assert "preserve historical Full Backup semantic button colors in Luxury Jade light theme" not in old_css
    assert 'class="button sg-full-restore-button sg-full-verify-button"' in template
    assert "data-sg-full-verify-button" in template
    assert 'class="button mtv2-restore sg-full-restore-button"' in template
    assert "data-sg-full-restore-button" in template
