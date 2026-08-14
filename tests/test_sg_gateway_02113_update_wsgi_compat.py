from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_production_wsgi_entrypoint_is_kept_for_existing_units() -> None:
    body = (ROOT / "app/production.py").read_text(encoding="utf-8")
    assert "from app.main import app, create_app" in body
    assert "application = app" in body


def test_panel_only_updater_checks_installed_wsgi_target_before_mutation() -> None:
    body = (ROOT / "deploy/update-from-github.sh").read_text(encoding="utf-8")
    assert "panel_wsgi_target()" in body
    assert "validate_candidate_wsgi_target()" in body
    assert 'validate_candidate_wsgi_target "$SOURCE_DIR"' in body
    assert body.index('validate_candidate_wsgi_target "$SOURCE_DIR"') < body.index(
        'run_stage 2 "Safety Backup: SG state + full /etc/letsencrypt"'
    )


def test_panel_only_updater_imports_effective_wsgi_target_before_restart() -> None:
    body = (ROOT / "deploy/update-from-github.sh").read_text(encoding="utf-8")
    assert "validate_deployed_panel()" in body
    assert "Panel WSGI import: OK" in body
    assert 'run_stage 4 "Python/UI проверка без изменения runtime" validate_deployed_panel' in body
    assert body.index('run_stage 4 "Python/UI проверка без изменения runtime" validate_deployed_panel') < body.index(
        'run_stage 5 "Перезапуск только panel + hostd"'
    )
