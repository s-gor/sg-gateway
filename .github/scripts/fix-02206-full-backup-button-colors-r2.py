from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD_CSS = ROOT / "app/web/static/sg-full-backup-v1.css"
NEW_CSS = ROOT / "app/web/static/sg-full-backup-button-colors-r2.css"
BASE = ROOT / "app/web/templates/base.html"
LEGACY_TEST = ROOT / "tests/test_sg_gateway_02205_full_backup_verify_ui.py"
TEST = ROOT / "tests/test_sg_gateway_02206_full_backup_button_colors_r2.py"

R1_MARKER = "/* SG-Gateway 022.06 · preserve historical Full Backup semantic button colors in Luxury Jade light theme. */"

old_css = OLD_CSS.read_text(encoding="utf-8")
if R1_MARKER in old_css:
    old_css = old_css.split(R1_MARKER, 1)[0].rstrip() + "\n"
OLD_CSS.write_text(old_css, encoding="utf-8", newline="\n")

legacy_test = LEGACY_TEST.read_text(encoding="utf-8")
r1_test_block = '''    # Luxury Jade uses generic light-theme button rules with !important. The
    # historical Full Backup semantic colors must explicitly win that cascade.
    assert 'html[data-theme="light"] .sg-full-restore-actions .sg-full-verify-button {' in css
    assert "var(--sg-blue) 13%,var(--sg-panel)) !important" in css
    assert 'html[data-theme="light"] .sg-full-restore-actions [data-sg-full-restore-button] {' in css
    assert "var(--sg-yellow) 44%,#8a5b30)" in css
    assert "var(--sg-yellow) 31%,#6b4427)) !important" in css
    assert "color: #fff5df !important" in css
    assert 'html[data-theme="light"] .sg-full-restore-actions .sg-full-restore-button:disabled {' in css
    assert "opacity: .46 !important" in css

'''
if r1_test_block in legacy_test:
    legacy_test = legacy_test.replace(r1_test_block, "", 1)
LEGACY_TEST.write_text(legacy_test, encoding="utf-8", newline="\n")

NEW_CSS.write_text(
    """/* SG-Gateway 0.1.0-022.06 · Full Backup button colors R2
   This file is intentionally loaded LAST on Maintenance, after Luxury Jade. */
html[data-theme="light"] body.page-maintenance .sg-full-restore-actions .button.sg-full-verify-button {
  border-color: color-mix(in srgb,var(--sg-blue) 42%,var(--sg-line)) !important;
  background: color-mix(in srgb,var(--sg-blue) 13%,var(--sg-panel)) !important;
  color: color-mix(in srgb,var(--sg-blue) 88%,white) !important;
}

html[data-theme="light"] body.page-maintenance .sg-full-restore-actions .button[data-sg-full-restore-button] {
  border-color: color-mix(in srgb,var(--sg-yellow) 58%,#6f4728) !important;
  background: linear-gradient(180deg,
    color-mix(in srgb,var(--sg-yellow) 44%,#8a5b30),
    color-mix(in srgb,var(--sg-yellow) 31%,#6b4427)) !important;
  color: #fff5df !important;
  box-shadow: 0 8px 18px color-mix(in srgb,#4f321d 24%,transparent) !important;
}

html[data-theme="light"] body.page-maintenance .sg-full-restore-actions .button[data-sg-full-restore-button]:not(:disabled):hover {
  border-color: color-mix(in srgb,var(--sg-yellow) 72%,#7a4c28) !important;
  filter: brightness(1.06);
}

html[data-theme="light"] body.page-maintenance .sg-full-restore-actions .button.sg-full-restore-button:disabled {
  opacity: .46 !important;
  filter: saturate(.35) !important;
  box-shadow: none !important;
}
""",
    encoding="utf-8",
    newline="\n",
)

base = BASE.read_text(encoding="utf-8")
link = """  {% if active_page|default('') == 'maintenance' %}
  <link rel="stylesheet" href="{{ url_for('static', filename='sg-full-backup-button-colors-r2.css') }}?v={{ app_version }}-full-backup-colors-r2">
  {% endif %}
"""
if "sg-full-backup-button-colors-r2.css" not in base:
    if "</head>" not in base:
        raise RuntimeError("base.html </head> anchor missing")
    base = base.replace("</head>", link + "</head>", 1)
BASE.write_text(base, encoding="utf-8", newline="\n")

TEST.write_text(
    """from __future__ import annotations

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
""",
    encoding="utf-8",
    newline="\n",
)

print("Full Backup button colors R2 patch applied")
