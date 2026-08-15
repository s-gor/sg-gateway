from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOSTD_ROOT = ROOT / "hostd"
if str(HOSTD_ROOT) not in sys.path:
    sys.path.insert(0, str(HOSTD_ROOT))

from sg_hostd.full_backup_runtime import _normalize_full_backup_upload_nginx_text


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_no_python_or_ui_512mib_upload_cap_remains() -> None:
    upload = _text("app/maintenance/full_backups.py")
    template = _text("app/web/templates/maintenance.html")
    assert "MAX_UPLOAD_BYTES" not in upload
    assert "допустимых 512 MiB" not in upload
    assert "максимум 512 MiB" not in template
    assert "без ограничения размера" in template


def test_install_and_panel_access_templates_use_unlimited_upload_contract() -> None:
    for path in ("install.sh", "deploy/configure-panel-access.sh"):
        body = _text(path)
        assert "client_max_body_size 1024m;" not in body
        assert body.count("client_max_body_size 0;") >= 2
        assert "/maintenance/full-backups/restore" in body
        assert "/maintenance/full-backups/verify" in body


def test_live_upload_contract_normalizer_migrates_old_1024m_blocks() -> None:
    old = """server {
    listen 63443;
    location = /maintenance/full-backups/restore {
        client_max_body_size 1024m;
        proxy_pass http://127.0.0.1:18080;
    }
    location = /maintenance/full-backups/verify {
        client_max_body_size 1024m;
        proxy_pass http://127.0.0.1:18080;
    }
    location / {
        proxy_pass http://127.0.0.1:18080;
    }
}
"""
    normalized = _normalize_full_backup_upload_nginx_text(old)
    assert "client_max_body_size 1024m;" not in normalized
    assert normalized.count("client_max_body_size 0;") == 2
    assert _normalize_full_backup_upload_nginx_text(normalized) == normalized


def test_live_upload_contract_normalizer_can_create_missing_exact_blocks() -> None:
    old = """server {
    listen 63443;
    location / {
        proxy_pass http://127.0.0.1:18080;
    }
}
"""
    normalized = _normalize_full_backup_upload_nginx_text(old)
    assert "/maintenance/full-backups/restore" in normalized
    assert "/maintenance/full-backups/verify" in normalized
    assert normalized.count("client_max_body_size 0;") == 2


def test_safe_updater_applies_and_verifies_only_upload_contract_migration() -> None:
    updater = _text("deploy/update-from-github.sh")
    assert "_ensure_full_restore_upload_nginx" in updater
    assert "nginx-static-before.sha256" in updater
    assert "nginx-site-before.conf" in updater
    assert "_normalize_full_backup_upload_nginx_text" in updater
    assert "Full Backup upload contract migration: OK" in updater
    assert "Full Backup upload contract changed outside the expected normalization" in updater


def test_02206_manifest_declares_integrated_verify_and_unlimited_upload() -> None:
    manifest = json.loads(_text("release-manifest.json"))
    full = manifest["portable_full_backup"]
    assert "max_upload_mib" not in full
    assert full["upload_size_limit"] == "unlimited"
    assert full["verify_button_integrated"] is True
    fix = manifest["development_fix"]
    assert fix["id"] == "full-backup-verify-unlimited-r1"
    assert fix["legacy_upload_limit_migration"] is True
    assert fix["panel_update_migration_scope"] == "full-backup-upload-contract-only"
