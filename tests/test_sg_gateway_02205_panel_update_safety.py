from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _function_block(body: str, name: str) -> str:
    start = body.index(f"def {name}(")
    next_def = body.find("\ndef ", start + 5)
    return body[start:] if next_def < 0 else body[start:next_def]


def test_panel_update_overview_uses_current_development_channel_not_main() -> None:
    body = (ROOT / "app/maintenance/panel_updates.py").read_text(encoding="utf-8")
    assert 'GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02206")' in body
    latest = _function_block(body, "_latest_channel")
    assert 'commits/{GITHUB_BRANCH}' in latest
    assert 'commits/main' not in latest


def test_panel_update_job_delegates_to_verified_shell_updater() -> None:
    body = (ROOT / "hostd/sg_hostd/operation_jobs.py").read_text(encoding="utf-8")
    block = _function_block(body, "start_panel_update_job")
    assert "PANEL_UPDATE_SCRIPT" in block
    assert "SG_GATEWAY_GITHUB_BRANCH={GITHUB_BRANCH}" in block
    assert "command=(" in block
    assert "panel_update_channel" in block


def test_legacy_panel_update_runner_is_also_safe() -> None:
    body = (ROOT / "hostd/sg_hostd/operation_job_runner.py").read_text(encoding="utf-8")
    block = _function_block(body, "run_panel_update")
    assert "update-from-github.sh" in block
    assert "SG_GATEWAY_GITHUB_BRANCH" in block
    assert "panel_update_runtime" not in block


def test_old_python_staging_import_cannot_touch_production_db() -> None:
    body = (ROOT / "hostd/sg_hostd/panel_update_runtime.py").read_text(encoding="utf-8")
    block = _function_block(body, "_validate_snapshot")
    assert 'validation_root = root.parent / "wsgi-validation"' in block
    assert 'env["SG_GATEWAY_DATA_DIR"] = str(validation_root / "data")' in block
    assert 'env["SG_GATEWAY_LOG_DIR"] = str(validation_root / "log")' in block
    assert 'env["SG_GATEWAY_DATA_DIR"] = "/var/lib/sg-gateway"' not in block


def test_python_update_entrypoint_delegates_instead_of_mutating_source_itself() -> None:
    body = (ROOT / "hostd/sg_hostd/panel_update_runtime.py").read_text(encoding="utf-8")
    block = _function_block(body, "update_panel")
    assert 'deploy" / "update-from-github.sh"' in block
    assert "SG_GATEWAY_GITHUB_BRANCH" in block
    assert "_backup_live(" not in block
    assert "_deploy_source(" not in block


def test_legacy_runtime_helpers_are_channel_aware() -> None:
    body = (ROOT / "hostd/sg_hostd/panel_update_runtime.py").read_text(encoding="utf-8")
    latest = _function_block(body, "_latest_channel_commit")
    assert 'commits/{GITHUB_BRANCH}' in latest
    assert "commits/main" not in latest
