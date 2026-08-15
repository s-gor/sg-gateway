from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_wsgi_keeps_all_02205_extensions() -> None:
    body = (ROOT / "app/production.py").read_text(encoding="utf-8")
    assert "from app.main import app" in body
    assert "register_sg_subscription(app)" in body
    assert "register_full_backup_verify(app)" in body
    assert "register_xmux_http(app)" in body


def test_candidate_wsgi_validation_never_imports_candidate_modules() -> None:
    body = (ROOT / "deploy/update-from-github.sh").read_text(encoding="utf-8")
    start = body.index("validate_candidate_wsgi_target()")
    end = body.index("validate_deployed_panel()", start)
    block = body[start:end]
    assert "importlib" not in block
    assert "module_path" in block
    assert "candidate source does not provide installed panel WSGI target" in block
    assert 'validate_candidate_wsgi_target "$SOURCE_DIR"' in body
    assert body.index('validate_candidate_wsgi_target "$SOURCE_DIR"') < body.index(
        'run_stage 2 "Safety Backup: SG state + full /etc/letsencrypt"'
    )


def test_deployed_wsgi_import_uses_isolated_data_and_log_directories() -> None:
    body = (ROOT / "deploy/update-from-github.sh").read_text(encoding="utf-8")
    start = body.index("validate_deployed_panel()")
    end = body.index("preflight()", start)
    block = body[start:end]
    assert "wsgi-validation" in block
    assert 'os.environ["SG_GATEWAY_DATA_DIR"]' in block
    assert 'os.environ["SG_GATEWAY_LOG_DIR"]' in block
    assert "Panel WSGI import: OK" in block
    assert 'chmod 0711 "$TEMP_DIR"' in block
    assert 'chmod 0700 "$TEMP_DIR"' in block
    chmod_open = block.index('chmod 0711 "$TEMP_DIR"')
    wsgi_runuser = block.index('runuser -u sg-gateway', chmod_open)
    chmod_close = block.index('chmod 0700 "$TEMP_DIR"', wsgi_runuser)
    assert chmod_open < wsgi_runuser < chmod_close


def test_wsgi_import_is_after_safety_backup_and_before_restart() -> None:
    body = (ROOT / "deploy/update-from-github.sh").read_text(encoding="utf-8")
    backup = body.index('run_stage 2 "Safety Backup: SG state + full /etc/letsencrypt"')
    validate = body.index('run_stage 4 "Python/UI проверка без изменения runtime" validate_deployed_panel')
    restart = body.index('run_stage 5 "Перезапуск только panel + hostd"')
    assert backup < validate < restart
