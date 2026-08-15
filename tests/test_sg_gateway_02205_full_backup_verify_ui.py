from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCHER_PATH = ROOT / "deploy" / "patch_full_backup_verify_ui.py"
TEMPLATE_PATH = ROOT / "app" / "web" / "templates" / "maintenance.html"
FULL_BACKUP_CSS_PATH = ROOT / "app" / "web" / "static" / "sg-full-backup-v1.css"


def _load_patcher():
    spec = importlib.util.spec_from_file_location("patch_full_backup_verify_ui", PATCHER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module



def test_full_backup_verify_button_is_integrated_in_product_template():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert template.count("data-sg-full-verify-button") == 2
    assert 'name="backup_action" value="verify"' in template
    assert "Проверить backup" in template
    assert "Проверка ничего не меняет." in template
    assert "готов к проверке / восстановлению" in template
    assert 'verifyButton.addEventListener("click", () => {' in template
    assert 'form.dataset.sgConfirmBypass = "1"' in template
    assert "максимум 512 MiB" not in template
    assert "без ограничения размера" in template

def test_full_backup_verify_ui_patch_is_complete_and_idempotent():
    patcher = _load_patcher()
    original = TEMPLATE_PATH.read_text(encoding="utf-8")

    patched = patcher.patch_text(original)
    patched_twice = patcher.patch_text(patched)

    assert patched == patched_twice
    assert patched.count("data-sg-full-verify-button") == 2
    assert 'name="backup_action" value="verify"' in patched
    assert "verify_full_backup_route" not in patched
    assert "Проверить backup" in patched
    assert "Проверка ничего не меняет." in patched
    assert "готов к проверке / восстановлению" in patched
    assert 'verifyButton.addEventListener("click", () => {' in patched
    assert 'form.dataset.sgConfirmBypass = "1"' in patched
    assert 'delete form.dataset.sgConfirmBypass' in patched
    assert "'backup.full.verify': 'Проверен полный backup'" in patched
    assert "data-sg-confirm-title=\"Полное восстановление SG-Gateway\"" in patched


def test_old_verify_formaction_is_migrated_to_restore_submit_action():
    patcher = _load_patcher()
    original = TEMPLATE_PATH.read_text(encoding="utf-8")
    patched = patcher.patch_text(original)
    legacy = patched.replace(
        'name="backup_action" value="verify"',
        'formaction="{{ url_for(\'verify_full_backup_route\') }}" formmethod="post"',
        1,
    )

    migrated = patcher.patch_text(legacy)

    assert 'name="backup_action" value="verify"' in migrated
    assert "verify_full_backup_route" not in migrated


def test_full_backup_verify_and_restore_actions_cannot_overflow_restore_area():
    css = FULL_BACKUP_CSS_PATH.read_text(encoding="utf-8")

    assert ".sg-full-restore-actions{" in css
    assert "flex-wrap:wrap;" in css
    assert "justify-content:flex-start;" in css
    assert ".sg-full-restore-note{" in css
    assert "flex:1 0 100%;" in css
    assert "max-width:none;" in css
    assert ".sg-full-restore-actions .sg-full-restore-button{" in css
    assert "flex:1 1 168px;" in css
    assert "min-width:0;" in css
    assert "max-width:100%;" in css


def test_full_backup_restore_area_matches_compact_action_zone_contract():
    css = FULL_BACKUP_CSS_PATH.read_text(encoding="utf-8")

    # No decorative state-like stripe on a static backup card.
    assert ".sg-full-backup-card::before{display:none!important;content:none!important}" in css

    # Right side behaves like an action zone rather than a second nested card.
    assert ".sg-full-backup-grid{" in css
    assert "align-items:start;" in css
    assert ".sg-full-restore-box{" in css
    assert "background:transparent!important;" in css
    assert "border:0!important;" in css
    assert "box-shadow:none!important;" in css

    # Safe Verify stays cool; Restore gets an amber/brown warning treatment.
    assert ".sg-full-restore-actions .sg-full-verify-button{" in css
    assert "var(--sg-blue) 13%" in css
    assert ".sg-full-restore-actions [data-sg-full-restore-button]{" in css
    assert "var(--sg-yellow) 44%" in css
    assert "#8a5b30" in css
    assert "#6b4427" in css

    # Luxury Jade uses generic light-theme button rules with !important. The
    # historical Full Backup semantic colors must explicitly win that cascade.
    assert 'html[data-theme="light"] .sg-full-restore-actions .sg-full-verify-button {' in css
    assert "var(--sg-blue) 13%,var(--sg-panel)) !important" in css
    assert 'html[data-theme="light"] .sg-full-restore-actions [data-sg-full-restore-button] {' in css
    assert "var(--sg-yellow) 44%,#8a5b30)" in css
    assert "var(--sg-yellow) 31%,#6b4427)) !important" in css
    assert "color: #fff5df !important" in css
    assert 'html[data-theme="light"] .sg-full-restore-actions .sg-full-restore-button:disabled {' in css
    assert "opacity: .46 !important" in css

    # Narrow layouts retain a visible divider and mobile vertical actions.
    assert "border-top:1px solid var(--sg-line-soft)!important;" in css
    assert ".sg-full-restore-actions{align-items:stretch;flex-direction:column}" in css
