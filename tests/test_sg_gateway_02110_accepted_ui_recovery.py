from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_expanded_device_cleanup_is_loaded_last():
    base = (ROOT / "app/web/templates/base.html").read_text(encoding="utf-8")
    css = (ROOT / "app/web/static/sg-device-expanded-cleanup-v1.css").read_text(encoding="utf-8")
    assert "SG_DEVICE_EXPANDED_CLEANUP_V1_LAST_CSS" in base
    assert base.index("SG_DEVICE_COLLAPSE_V4_LAST_CSS") < base.index("SG_DEVICE_EXPANDED_CLEANUP_V1_LAST_CSS")
    assert ".dv16-device > .dv16-technical" in css
    assert "border-top: 0 !important" in css


def test_recovery_has_restore_entry_using_existing_transaction():
    main = (ROOT / "app/main.py").read_text(encoding="utf-8")
    auth = (ROOT / "app/security/auth.py").read_text(encoding="utf-8")
    template = (ROOT / "app/web/templates/recovery.html").read_text(encoding="utf-8")
    assert 'def _restore_backup_response(name: str, destination_endpoint: str):' in main
    assert 'def recovery_restore_backup_route(name: str):' in main
    assert 'return _restore_backup_response(name, "maintenance")' in main
    assert 'return _restore_backup_response(name, "recovery")' in main
    assert '"recovery_restore_backup_route"' in auth
    assert 'data-recovery-restore' in template
    assert 'id="recovery-confirm"' in template
