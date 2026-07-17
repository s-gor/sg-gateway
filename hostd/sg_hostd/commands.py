from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class HostCommandResult:
    command: str
    status: str
    message: str
    payload: dict


def list_allowed_commands() -> list[str]:
    return sorted(_COMMANDS)


def execute_command(command: str) -> HostCommandResult:
    handler = _COMMANDS.get(command)
    if handler is None:
        return HostCommandResult(
            command=command,
            status="error",
            message="Command is not allowed",
            payload={},
        )

    return handler()


def _awg_status() -> HostCommandResult:
    return HostCommandResult(
        command="awg.status",
        status="warning",
        message="AmneziaWG host integration is not connected yet",
        payload={"interface": "awg0", "connected": False},
    )


def _xray_status() -> HostCommandResult:
    return HostCommandResult(
        command="xray.status",
        status="warning",
        message="Xray runtime status is currently reported by Docker/Compose later",
        payload={"connected": False},
    )


def _nftables_status() -> HostCommandResult:
    return HostCommandResult(
        command="nftables.status",
        status="warning",
        message="nftables integration is not connected yet",
        payload={"connected": False},
    )


def _system_diagnostics() -> HostCommandResult:
    return HostCommandResult(
        command="system.diagnostics",
        status="ok",
        message="Host helper mock diagnostics are available",
        payload={
            "mode": "mock",
            "shell": "disabled",
            "arbitrary_commands": False,
        },
    )


_COMMANDS: dict[str, Callable[[], HostCommandResult]] = {
    "awg.status": _awg_status,
    "xray.status": _xray_status,
    "nftables.status": _nftables_status,
    "system.diagnostics": _system_diagnostics,
}