from __future__ import annotations

from dataclasses import dataclass

from app.config import load_config
from app.connections.settings import get_connection_settings
from app.db import get_database_path
from app.hostd.client import hostd_health, run_hostd_command
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
            name="База данных",
            status="ok" if database_path.exists() else "warning",
            message=str(database_path) if database_path.exists() else "База данных будет создана при первом использовании",
        ),
        HealthCheck(
            name="Каталог резервных копий",
            status="ok" if backup_dir.exists() else "error",
            message=str(backup_dir),
        ),
        HealthCheck(
            name="Каталог данных",
            status="ok" if config.data_dir.exists() else "warning",
            message=str(config.data_dir),
        ),
        _hostd_check(),
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


def _hostd_check() -> HealthCheck:
    result = hostd_health()
    return HealthCheck(
        name="sg-hostd",
        status=result.status,
        message=result.message,
    )


def _connection_checks() -> list[HealthCheck]:
    checks: list[HealthCheck] = []

    awg = get_connection_settings("amneziawg")
    awg_key = awg.config.get("server_public_key", "")
    awg_host = run_hostd_command("awg.status")
    checks.append(
        HealthCheck(
            name="Настройки AmneziaWG",
            status="warning" if "PLACEHOLDER" in awg_key else awg_host.status,
            message=f"{awg.host}:{awg.port}; hostd: {awg_host.message}",
        )
    )

    xray = get_connection_settings("xray")
    xray_key = xray.config.get("public_key", "")
    xray_short_id = xray.config.get("short_id", "")
    xray_ready = "PLACEHOLDER" not in xray_key and "PLACEHOLDER" not in xray_short_id
    xray_host = run_hostd_command("xray.status")
    checks.append(
        HealthCheck(
            name="Настройки Xray Reality",
            status=xray_host.status if xray_ready else "warning",
            message=(
                f"{xray.host}:{xray.port}, "
                f"SNI {xray.config.get('server_name', 'не задано')}; "
                f"hostd: {xray_host.message}"
            ),
        )
    )

    return checks