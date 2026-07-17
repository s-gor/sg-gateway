from __future__ import annotations

from dataclasses import dataclass

from app.config import load_config
from app.connections.settings import get_connection_settings
from app.db import get_database_path
from app.maintenance.backups import get_backup_dir


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: str
    message: str


def collect_health_checks() -> list[HealthCheck]:
    config = load_config()
    database_path = get_database_path()
    backup_dir = get_backup_dir()
    checks = [
        HealthCheck(
            name="Database",
            status="ok" if database_path.exists() else "warning",
            message=str(database_path) if database_path.exists() else "Database will be created on first use",
        ),
        HealthCheck(
            name="Backup directory",
            status="ok" if backup_dir.exists() else "error",
            message=str(backup_dir),
        ),
        HealthCheck(
            name="Data directory",
            status="ok" if config.data_dir.exists() else "warning",
            message=str(config.data_dir),
        ),
    ]

    checks.extend(_connection_checks())
    return checks


def health_summary() -> str:
    statuses = {check.status for check in collect_health_checks()}
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "ok"


def _connection_checks() -> list[HealthCheck]:
    checks: list[HealthCheck] = []

    awg = get_connection_settings("amneziawg")
    awg_key = awg.config.get("server_public_key", "")
    checks.append(
        HealthCheck(
            name="AmneziaWG settings",
            status="warning" if "PLACEHOLDER" in awg_key else "ok",
            message=f"{awg.host}:{awg.port}",
        )
    )

    xray = get_connection_settings("xray")
    xray_key = xray.config.get("public_key", "")
    xray_short_id = xray.config.get("short_id", "")
    xray_ready = "PLACEHOLDER" not in xray_key and "PLACEHOLDER" not in xray_short_id
    checks.append(
        HealthCheck(
            name="Xray Reality settings",
            status="ok" if xray_ready else "warning",
            message=f"{xray.host}:{xray.port}, SNI {xray.config.get('server_name', 'not set')}",
        )
    )

    return checks