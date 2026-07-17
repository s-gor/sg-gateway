from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import load_config
from app.db import get_database_path, init_db


@dataclass(frozen=True)
class BackupInfo:
    name: str
    path: Path
    size_bytes: int
    created_at: str


def get_backup_dir() -> Path:
    directory = load_config().data_dir / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def create_backup() -> BackupInfo:
    init_db()
    source = get_database_path()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    destination = get_backup_dir() / f"sg-gateway-{timestamp}.sqlite"
    shutil.copy2(source, destination)
    return _backup_info(destination)


def list_backups() -> list[BackupInfo]:
    backups = [_backup_info(path) for path in get_backup_dir().glob("sg-gateway-*.sqlite")]
    return sorted(backups, key=lambda item: item.name, reverse=True)


def get_backup(name: str) -> BackupInfo | None:
    if "/" in name or "\\" in name or ".." in name:
        return None

    path = get_backup_dir() / name
    if not path.exists() or not path.is_file():
        return None

    return _backup_info(path)


def restore_backup(name: str) -> bool:
    backup = get_backup(name)
    if backup is None:
        return False

    target = get_database_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        safety_name = datetime.now(timezone.utc).strftime("pre-restore-%Y%m%d-%H%M%S.sqlite")
        shutil.copy2(target, get_backup_dir() / safety_name)

    shutil.copy2(backup.path, target)
    init_db()
    return True


def _backup_info(path: Path) -> BackupInfo:
    stat = path.stat()
    created_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return BackupInfo(
        name=path.name,
        path=path,
        size_bytes=stat.st_size,
        created_at=created_at,
    )