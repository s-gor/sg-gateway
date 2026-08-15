from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS_PATH = ROOT / "app/web/static/sg-full-backup-v1.css"
TEST_PATH = ROOT / "tests/test_sg_gateway_02205_full_backup_verify_ui.py"

css = CSS_PATH.read_text(encoding="utf-8")
marker = "/* SG-Gateway 022.06 · preserve historical Full Backup semantic button colors in Luxury Jade light theme. */"
assert marker not in css
assert ".sg-full-restore-actions .sg-full-verify-button{" in css
assert "color-mix(in srgb,var(--sg-blue) 13%,var(--sg-panel))" in css
assert "color-mix(in srgb,var(--sg-yellow) 44%,#8a5b30)" in css
assert "color-mix(in srgb,var(--sg-yellow) 31%,#6b4427)" in css

# The historical colors were introduced in 0db7ec7d3c389c63b6b5a77339d31ade812ae6d1.
# Luxury Jade later added generic light-theme .button rules with !important, so
# the values still existed in this file but lost the cascade. Re-assert the
# exact historical values only for Full Backup, with enough specificity and
# !important to beat the generic material rule.
css += r'''

/* SG-Gateway 022.06 · preserve historical Full Backup semantic button colors in Luxury Jade light theme. */
html[data-theme="light"] .sg-full-restore-actions .sg-full-verify-button {
  border-color: color-mix(in srgb,var(--sg-blue) 42%,var(--sg-line)) !important;
  background: color-mix(in srgb,var(--sg-blue) 13%,var(--sg-panel)) !important;
  color: color-mix(in srgb,var(--sg-blue) 88%,white) !important;
}

html[data-theme="light"] .sg-full-restore-actions [data-sg-full-restore-button] {
  border-color: color-mix(in srgb,var(--sg-yellow) 58%,#6f4728) !important;
  background: linear-gradient(180deg,
    color-mix(in srgb,var(--sg-yellow) 44%,#8a5b30),
    color-mix(in srgb,var(--sg-yellow) 31%,#6b4427)) !important;
  color: #fff5df !important;
  box-shadow: 0 8px 18px color-mix(in srgb,#4f321d 24%,transparent) !important;
}

html[data-theme="light"] .sg-full-restore-actions [data-sg-full-restore-button]:not(:disabled):hover {
  border-color: color-mix(in srgb,var(--sg-yellow) 72%,#7a4c28) !important;
  filter: brightness(1.06);
}

html[data-theme="light"] .sg-full-restore-actions .sg-full-restore-button:disabled {
  opacity: .46 !important;
  filter: saturate(.35) !important;
  box-shadow: none !important;
}
'''
CSS_PATH.write_text(css, encoding="utf-8", newline="\n")

test = TEST_PATH.read_text(encoding="utf-8")
anchor = '''    assert "#6b4427" in css\n\n    # Narrow layouts retain a visible divider and mobile vertical actions.\n'''
insert = '''    assert "#6b4427" in css\n\n    # Luxury Jade uses generic light-theme button rules with !important. The\n    # historical Full Backup semantic colors must explicitly win that cascade.\n    assert 'html[data-theme="light"] .sg-full-restore-actions .sg-full-verify-button {' in css\n    assert "var(--sg-blue) 13%,var(--sg-panel)) !important" in css\n    assert 'html[data-theme="light"] .sg-full-restore-actions [data-sg-full-restore-button] {' in css\n    assert "var(--sg-yellow) 44%,#8a5b30)" in css\n    assert "var(--sg-yellow) 31%,#6b4427)) !important" in css\n    assert "color: #fff5df !important" in css\n    assert 'html[data-theme="light"] .sg-full-restore-actions .sg-full-restore-button:disabled {' in css\n    assert "opacity: .46 !important" in css\n\n    # Narrow layouts retain a visible divider and mobile vertical actions.\n'''
assert test.count(anchor) == 1
test = test.replace(anchor, insert, 1)
TEST_PATH.write_text(test, encoding="utf-8", newline="\n")
