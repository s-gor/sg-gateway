from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCHER_PATH = ROOT / "deploy" / "patch_full_backup_verify_ui.py"
TEMPLATE_PATH = ROOT / "app" / "web" / "templates" / "maintenance.html"


def _load_patcher():
    spec = importlib.util.spec_from_file_location("patch_full_backup_verify_ui", PATCHER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_backup_verify_ui_patch_is_complete_and_idempotent():
    patcher = _load_patcher()
    original = TEMPLATE_PATH.read_text(encoding="utf-8")

    patched = patcher.patch_text(original)
    patched_twice = patcher.patch_text(patched)

    assert patched == patched_twice
    assert patched.count("data-sg-full-verify-button") == 2
    assert "url_for('verify_full_backup_route')" in patched
    assert "Проверить backup" in patched
    assert "Проверка ничего не меняет." in patched
    assert "готов к проверке / восстановлению" in patched
    assert "'backup.full.verify': 'Проверен полный backup'" in patched
    assert "data-sg-confirm-title=\"Полное восстановление SG-Gateway\"" in patched
