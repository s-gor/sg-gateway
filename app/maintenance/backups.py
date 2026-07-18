from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import load_config
from app.db import get_database_path, init_db
from app.maintenance.operations import log_operation


@dataclass(frozen=True)
class BackupInfo:
    name: str
    path: Path
    size_bytes: int
    created_at: str
    kind: str


def get_backup_dir() -> Path:
    directory = load_config().data_dir / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _next_backup_path(prefix: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup_dir = get_backup_dir()
    candidate = backup_dir / f"{prefix}-{timestamp}.sqlite"
    counter = 1
    while candidate.exists():
        candidate = backup_dir / f"{prefix}-{timestamp}-{counter}.sqlite"
        counter += 1
    return candidate


def create_backup() -> BackupInfo:
    init_db()
    source = get_database_path()
    destination = _next_backup_path("sg-gateway")
    shutil.copy2(source, destination)
    backup = _backup_info(destination)
    log_operation("backup.create", f"backup:{backup.name}", f"Создана резервная копия {backup.name}")
    return backup


def list_backups() -> list[BackupInfo]:
    backup_dir = get_backup_dir()
    paths = [
        *backup_dir.glob("sg-gateway-*.sqlite"),
        *backup_dir.glob("pre-restore-*.sqlite"),
    ]
    backups = [_backup_info(path) for path in paths]
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
        log_operation("backup.restore", f"backup:{name}", "Резервная копия не найдена", status="error")
        return False

    target = get_database_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        shutil.copy2(target, _next_backup_path("pre-restore"))

    shutil.copy2(backup.path, target)
    init_db()
    log_operation("backup.restore", f"backup:{backup.name}", f"Восстановлена резервная копия {backup.name}")
    return True


def _backup_kind(path: Path) -> str:
    if path.name.startswith("pre-restore-"):
        return "Страховочная копия перед восстановлением"
    return "Ручная резервная копия"


def _backup_info(path: Path) -> BackupInfo:
    stat = path.stat()
    created_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return BackupInfo(
        name=path.name,
        path=path,
        size_bytes=stat.st_size,
        created_at=created_at,
        kind=_backup_kind(path),
    )
