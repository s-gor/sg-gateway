from app.clients.repository import count_clients, create_client
from app.db import init_db
from app.maintenance.backups import create_backup, list_backups, restore_backup


def test_create_and_restore_backup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_db()
    create_client("Before", "recommended")

    backup = create_backup()
    create_client("After", "recommended")

    assert backup.name in {item.name for item in list_backups()}
    assert count_clients() == 2

    assert restore_backup(backup.name) is True
    assert count_clients() == 1


def test_create_backup_uses_unique_names(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_db()

    first = create_backup()
    second = create_backup()

    assert first.name != second.name
    assert first.path.exists()
    assert second.path.exists()
