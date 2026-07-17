from app.db import init_db
from app.maintenance.health import collect_health_checks, health_summary


def test_health_checks_report_expected_sections(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_db()

    checks = collect_health_checks()
    names = {check.name for check in checks}

    assert "Database" in names
    assert "Backup directory" in names
    assert "AmneziaWG settings" in names
    assert health_summary() in {"ok", "warning", "error"}