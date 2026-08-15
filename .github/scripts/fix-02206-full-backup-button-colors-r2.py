from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD_CSS = ROOT / "app/web/static/sg-full-backup-v1.css"
NEW_CSS = ROOT / "app/web/static/sg-full-backup-button-colors-r2.css"
BASE = ROOT / "app/web/templates/base.html"
TEST = ROOT / "tests/test_sg_gateway_02206_full_backup_button_colors_r2.py"

R1_MARKER = "/* SG-Gateway 022.06 · preserve historical Full Backup semantic button colors in Luxury Jade light theme. */"

old_css = OLD_CSS.read_text(encoding="utf-8")
if R1_MARKER in old_css:
    old_css = old_css.split(R1_MARKER, 1)[0].rstrip() + "\n"
OLD_CSS.write_text(old_css, encoding="utf-8", newline="\n")

NEW_CSS.write_text(
    '''/* SG-Gateway 0.1.0-022.06 · Full Backup button colors R2\n"
    "   This file is intentionally loaded LAST on Maintenance, after Luxury Jade. */\n"
    "html[data-theme=\"light\"] body.page-maintenance .sg-full-restore-actions .button.sg-full-verify-button {\n"
    "  border-color: color-mix(in srgb,var(--sg-blue) 42%,var(--sg-line)) !important;\n"
    "  background: color-mix(in srgb,var(--sg-blue) 13%,var(--sg-panel)) !important;\n"
    "  color: color-mix(in srgb,var(--sg-blue) 88%,white) !important;\n"
    "}\n\n"
    "html[data-theme=\"light\"] body.page-maintenance .sg-full-restore-actions .button[data-sg-full-restore-button] {\n"
    "  border-color: color-mix(in srgb,var(--sg-yellow) 58%,#6f4728) !important;\n"
    "  background: linear-gradient(180deg,\n"
    "    color-mix(in srgb,var(--sg-yellow) 44%,#8a5b30),\n"
    "    color-mix(in srgb,var(--sg-yellow) 31%,#6b4427)) !important;\n"
    "  color: #fff5df !important;\n"
    "  box-shadow: 0 8px 18px color-mix(in srgb,#4f321d 24%,transparent) !important;\n"
    "}\n\n"
    "html[data-theme=\"light\"] body.page-maintenance .sg-full-restore-actions .button[data-sg-full-restore-button]:not(:disabled):hover {\n"
    "  border-color: color-mix(in srgb,var(--sg-yellow) 72%,#7a4c28) !important;\n"
    "  filter: brightness(1.06);\n"
    "}\n\n"
    "html[data-theme=\"light\"] body.page-maintenance .sg-full-restore-actions .button.sg-full-restore-button:disabled {\n"
    "  opacity: .46 !important;\n"
    "  filter: saturate(.35) !important;\n"
    "  box-shadow: none !important;\n"
    "}\n'''.replace('"\n    "', ''),
    encoding="utf-8",
    newline="\n",
)

base = BASE.read_text(encoding="utf-8")
link = '''  {% if active_page|default('') == 'maintenance' %}\n  <link rel="stylesheet" href="{{ url_for('static', filename='sg-full-backup-button-colors-r2.css') }}?v={{ app_version }}-full-backup-colors-r2">\n  {% endif %}\n'''
if "sg-full-backup-button-colors-r2.css" not in base:
    if "</head>" not in base:
        raise RuntimeError("base.html </head> anchor missing")
    base = base.replace("</head>", link + "</head>", 1)
BASE.write_text(base, encoding="utf-8", newline="\n")

TEST.write_text(
    '''from __future__ import annotations\n\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nBASE = ROOT / "app/web/templates/base.html"\nOLD_CSS = ROOT / "app/web/static/sg-full-backup-v1.css"\nCOLORS = ROOT / "app/web/static/sg-full-backup-button-colors-r2.css"\nMAINTENANCE = ROOT / "app/web/templates/maintenance.html"\n\n\ndef test_full_backup_color_override_is_loaded_after_global_luxury_jade() -> None:\n    base = BASE.read_text(encoding="utf-8")\n    luxury = base.index("sg-luxury-jade-depth-v2.css")\n    controls = base.index("sg-controls-final-v1.css")\n    colors = base.index("sg-full-backup-button-colors-r2.css")\n    head_end = base.index("</head>")\n    assert luxury < colors < head_end\n    assert controls < colors < head_end\n    assert "active_page|default('') == 'maintenance'" in base[colors - 140:colors]\n    assert "?v={{ app_version }}-full-backup-colors-r2" in base\n\n\ndef test_full_backup_color_override_has_stronger_scoped_selectors_and_exact_historical_values() -> None:\n    css = COLORS.read_text(encoding="utf-8")\n    assert 'html[data-theme="light"] body.page-maintenance .sg-full-restore-actions .button.sg-full-verify-button {' in css\n    assert "var(--sg-blue) 13%,var(--sg-panel)) !important" in css\n    assert 'html[data-theme="light"] body.page-maintenance .sg-full-restore-actions .button[data-sg-full-restore-button] {' in css\n    assert "var(--sg-yellow) 44%,#8a5b30)" in css\n    assert "var(--sg-yellow) 31%,#6b4427)) !important" in css\n    assert "color: #fff5df !important" in css\n    assert '.button.sg-full-restore-button:disabled {' in css\n    assert "opacity: .46 !important" in css\n\n\ndef test_r1_dead_override_is_removed_and_buttons_keep_required_hooks() -> None:\n    old_css = OLD_CSS.read_text(encoding="utf-8")\n    template = MAINTENANCE.read_text(encoding="utf-8")\n    assert "preserve historical Full Backup semantic button colors in Luxury Jade light theme" not in old_css\n    assert 'class="button sg-full-restore-button sg-full-verify-button"' in template\n    assert "data-sg-full-verify-button" in template\n    assert 'class="button mtv2-restore sg-full-restore-button"' in template\n    assert "data-sg-full-restore-button" in template\n''',
    encoding="utf-8",
    newline="\n",
)

print("Full Backup button colors R2 patch applied")
