from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R2_CSS = ROOT / "app/web/static/sg-full-backup-button-colors-r2.css"
R3_CSS = ROOT / "app/web/static/sg-full-backup-button-colors-r3.css"
BASE = ROOT / "app/web/templates/base.html"
R2_TEST = ROOT / "tests/test_sg_gateway_02206_full_backup_button_colors_r2.py"
R3_TEST = ROOT / "tests/test_sg_gateway_02206_full_backup_button_colors_r3.py"

R3_CSS.write_text(
    """/* SG-Gateway 0.1.0-022.06 · Full Backup semantic button colors R3
   Loaded LAST on Maintenance. Uses dedicated semantic colours so Luxury Jade
   cannot remap Verify blue into jade, and both light/dark themes stay distinct. */

html[data-theme="light"] body.page-maintenance {
  --sg-full-verify-line: #6f9bc7;
  --sg-full-verify-top: #edf5fd;
  --sg-full-verify-bottom: #d8e9f8;
  --sg-full-verify-text: #2f669b;
  --sg-full-verify-shadow: 0 8px 18px rgba(47, 102, 155, .14);
  --sg-full-restore-line: #b78343;
  --sg-full-restore-top: #9d6b3b;
  --sg-full-restore-bottom: #744a24;
  --sg-full-restore-text: #fff5df;
  --sg-full-restore-shadow: 0 8px 18px rgba(79, 50, 29, .24);
}

html[data-theme="dark"] body.page-maintenance {
  --sg-full-verify-line: #5f91c2;
  --sg-full-verify-top: #294f76;
  --sg-full-verify-bottom: #1d3b5a;
  --sg-full-verify-text: #e3f1ff;
  --sg-full-verify-shadow: 0 8px 18px rgba(4, 15, 28, .34);
  --sg-full-restore-line: #bf8b48;
  --sg-full-restore-top: #7a522b;
  --sg-full-restore-bottom: #57391f;
  --sg-full-restore-text: #fff1d7;
  --sg-full-restore-shadow: 0 8px 18px rgba(0, 0, 0, .30);
}

body.page-maintenance .sg-full-restore-actions .button.sg-full-verify-button {
  border-color: var(--sg-full-verify-line) !important;
  background: linear-gradient(180deg,
    var(--sg-full-verify-top),
    var(--sg-full-verify-bottom)) !important;
  color: var(--sg-full-verify-text) !important;
  box-shadow: var(--sg-full-verify-shadow) !important;
}

body.page-maintenance .sg-full-restore-actions .button.sg-full-verify-button:not(:disabled):hover {
  border-color: var(--sg-full-verify-line) !important;
  background: linear-gradient(180deg,
    var(--sg-full-verify-top),
    var(--sg-full-verify-bottom)) !important;
  color: var(--sg-full-verify-text) !important;
  filter: brightness(1.07) !important;
}

body.page-maintenance .sg-full-restore-actions .button[data-sg-full-restore-button] {
  border-color: var(--sg-full-restore-line) !important;
  background: linear-gradient(180deg,
    var(--sg-full-restore-top),
    var(--sg-full-restore-bottom)) !important;
  color: var(--sg-full-restore-text) !important;
  box-shadow: var(--sg-full-restore-shadow) !important;
}

body.page-maintenance .sg-full-restore-actions .button[data-sg-full-restore-button]:not(:disabled):hover {
  border-color: var(--sg-full-restore-line) !important;
  background: linear-gradient(180deg,
    var(--sg-full-restore-top),
    var(--sg-full-restore-bottom)) !important;
  color: var(--sg-full-restore-text) !important;
  filter: brightness(1.08) !important;
}

/* Keep disabled controls visibly semantic without making them look actionable. */
body.page-maintenance .sg-full-restore-actions .button.sg-full-restore-button:disabled {
  opacity: .62 !important;
  filter: saturate(.72) brightness(.96) !important;
  box-shadow: none !important;
  cursor: not-allowed !important;
  transform: none !important;
}
""",
    encoding="utf-8",
    newline="\n",
)

base = BASE.read_text(encoding="utf-8")
old_link = "{{ url_for('static', filename='sg-full-backup-button-colors-r2.css') }}?v={{ app_version }}-full-backup-colors-r2"
new_link = "{{ url_for('static', filename='sg-full-backup-button-colors-r3.css') }}?v={{ app_version }}-full-backup-colors-r3"
if old_link not in base:
    raise RuntimeError("R2 Full Backup color link is missing from base.html")
if base.count(old_link) != 1:
    raise RuntimeError("R2 Full Backup color link is not unique in base.html")
base = base.replace(old_link, new_link, 1)
BASE.write_text(base, encoding="utf-8", newline="\n")

if R2_CSS.exists():
    R2_CSS.unlink()
if R2_TEST.exists():
    R2_TEST.unlink()

R3_TEST.write_text(
    """from __future__ import annotations

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
""",
    encoding="utf-8",
    newline="\n",
)

print("Full Backup button colors R3 dual-theme patch applied")
