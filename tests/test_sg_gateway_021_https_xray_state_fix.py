from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_https_rollback_state_survives_exit_trap() -> None:
    script = read("deploy/configure-panel-access.sh")
    assert 'SG_HTTPS_BACKUP_DIR=""' in script
    assert "SG_HTTPS_COMMITTED=0" in script
    assert "${SG_HTTPS_COMMITTED:-0}" in script
    assert 'restore_backup "$SG_HTTPS_BACKUP_DIR"' in script
    assert "SG_HTTPS_COMMITTED=1" in script
    assert "committed=0" not in script
    assert "$committed" not in script


def test_tls_profiles_do_not_claim_https_is_missing_when_it_is_ready() -> None:
    clients = read("app/web/templates/clients.html")
    connections = read("app/web/templates/connections.html")

    assert "profile.tls_required and not xray_profiles.tls_ready" in clients
    assert "Сначала включите профиль в Connections" in clients
    assert "Готов к включению" in connections
    assert "profile.tls_required and xray_profiles.tls_ready" in connections
