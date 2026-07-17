from __future__ import annotations

from dataclasses import dataclass

from app.clients.repository import count_clients
from app.config import load_config
from app.connections.service import list_connections
from app.db import get_database_path
from app.maintenance.backups import list_backups
from app.maintenance.operations import count_operations


@dataclass(frozen=True)
class DiagnosticItem:
    label: str
    value: str
    state: str


def collect_diagnostics() -> list[DiagnosticItem]:
    config = load_config()
    database_path = get_database_path()
    connections = list_connections()
    backups = list_backups()

    return [
        DiagnosticItem("Panel mode", config.environment, "ok"),
        DiagnosticItem("Database", "Ready" if database_path.exists() else "Will be created", "ok"),
        DiagnosticItem("Database path", str(database_path), "idle"),
        DiagnosticItem("Clients", str(count_clients()), "idle"),
        DiagnosticItem("AmneziaWG clients", str(connections[0].clients), "idle"),
        DiagnosticItem("Xray clients", str(connections[1].clients), "idle"),
        DiagnosticItem("Backups", str(len(backups)), "ok" if backups else "idle"),
        DiagnosticItem("Operations", str(count_operations()), "ok"),
    ]