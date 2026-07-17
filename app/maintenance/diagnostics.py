from __future__ import annotations

import json
import platform
from datetime import datetime, timezone

from app.clients.repository import count_clients, list_clients
from app.config import load_config
from app.connections.service import list_connections
from app.db import get_database_path
from app.hostd.client import hostd_health
from app.maintenance.backups import list_backups
from app.maintenance.health import collect_health_checks, health_summary
from app.maintenance.operations import list_operations, log_operation


def build_diagnostic_report() -> dict:
    config = load_config()
    database_path = get_database_path()
    clients = list_clients()
    connections = list_connections()
    backups = list_backups()
    operations = list_operations(limit=50)
    health_checks = collect_health_checks()
    hostd = hostd_health()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "service": "sg-gateway-panel",
        "environment": config.environment,
        "health": health_summary(),
        "hostd": {
            "url": config.hostd_url,
            "status": hostd.status,
            "message": hostd.message,
            "payload": hostd.payload,
        },
        "runtime": {
            "python": platform.python_version(),
            "system": platform.system(),
            "release": platform.release(),
        },
        "paths": {
            "data_dir": str(config.data_dir),
            "log_dir": str(config.log_dir),
            "database": str(database_path),
            "database_exists": database_path.exists(),
        },
        "summary": {
            "clients": count_clients(),
            "backups": len(backups),
            "operations": len(operations),
        },
        "health_checks": [
            {
                "name": item.name,
                "status": item.status,
                "message": item.message,
            }
            for item in health_checks
        ],
        "connections": [
            {
                "name": item.name,
                "label": item.label,
                "status": item.status,
                "port": item.port,
                "clients": item.clients,
                "note": item.note,
            }
            for item in connections
        ],
        "clients": [
            {
                "id": item.id,
                "name": item.name,
                "enabled": item.enabled,
                "expires_at": item.expires_at,
                "amneziawg": item.awg_status,
                "xray": item.xray_status,
            }
            for item in clients
        ],
        "backups": [
            {
                "name": item.name,
                "size_bytes": item.size_bytes,
                "created_at": item.created_at,
            }
            for item in backups
        ],
        "operations": [
            {
                "id": item.id,
                "action": item.action,
                "target": item.target,
                "status": item.status,
                "message": item.message,
                "created_at": item.created_at,
            }
            for item in operations
        ],
    }


def build_diagnostic_report_json() -> str:
    report = build_diagnostic_report()
    log_operation(
        action="diagnostics.download",
        target="diagnostics:report",
        message="Downloaded diagnostic report",
    )
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)