from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_02206_has_only_current_and_main_ci_workflows() -> None:
    workflows = {p.name for p in (ROOT / ".github" / "workflows").glob("*.yml")}
    assert workflows == {"ci.yml", "ci-02206-dev.yml"}
    assert "ci-02205-dev.yml" not in workflows
    assert "patch-full-backup-upload-routes.yml" not in workflows


def test_completed_full_backup_patch_generator_is_not_shipped() -> None:
    assert not (ROOT / "deploy" / "patch_full_backup_upload_routes.py").exists()
    runtime = _text("hostd/sg_hostd/full_backup_runtime.py")
    install = _text("install.sh")
    panel_access = _text("deploy/configure-panel-access.sh")
    for marker in (
        "/maintenance/full-backups/restore",
        "/maintenance/full-backups/verify",
    ):
        assert marker in runtime
        assert marker in install
        assert marker in panel_access
    assert "SG_GATEWAY_FULL_BACKUP_UPLOAD_FIX2" in runtime


def test_ci_hygiene_is_declared_non_runtime() -> None:
    assert _text("BUILD-ID").strip() == "DEV-02206-CI-HYGIENE-R1"
    manifest = json.loads(_text("release-manifest.json"))
    assert manifest["build"] == "DEV-02206-CI-HYGIENE-R1"
    hygiene = manifest["development_hygiene"]
    assert hygiene["id"] == "ci-hygiene-r1"
    assert hygiene["scope"] == "repository-workflows-only"
    assert hygiene["runtime_changes"] is False
    assert hygiene["preserves_frozen_branch"] == "dev-02205"
    assert set(hygiene["removed"]) == {
        ".github/workflows/ci-02205-dev.yml",
        ".github/workflows/patch-full-backup-upload-routes.yml",
        "deploy/patch_full_backup_upload_routes.py",
    }
