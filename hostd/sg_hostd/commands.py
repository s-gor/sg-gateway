from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sg_hostd.operation_jobs import (
    rollback_xray_runtime,
    run_tls_maintenance,
    start_tls_issue_job,
    start_xray_apply_job,
    start_xray_update_job,
)

from sg_hostd.client_runtime import apply_all_clients, apply_xray_runtime, test_xray_candidate

from sg_hostd.privileged_runtime import execute_privileged_action

from sg_hostd.mihomo_runtime import execute_mihomo_action


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



def _mihomo_hostd_result(
    command: str,
    action: str,
) -> HostCommandResult:
    result = execute_mihomo_action(action)
    return HostCommandResult(
        command=command,
        status=result.status,
        message=result.message,
        payload=result.payload,
    )


def _mihomo_apply() -> HostCommandResult:
    return _mihomo_hostd_result("mihomo.apply", "apply")


def _mihomo_test() -> HostCommandResult:
    return _mihomo_hostd_result("mihomo.test", "test")


def _mihomo_restart() -> HostCommandResult:
    return _mihomo_hostd_result("mihomo.restart", "restart")


def _mihomo_rollback() -> HostCommandResult:
    return _mihomo_hostd_result("mihomo.rollback", "rollback")


def _sg_gateway_privileged_result(command: str) -> HostCommandResult:
    result = execute_privileged_action(command)
    return HostCommandResult(
        command=command,
        status=result.status,
        message=result.message,
        payload=result.payload,
    )


def _geofiles_apply() -> HostCommandResult:
    return _sg_gateway_privileged_result("geofiles.apply")


def _geofiles_rollback() -> HostCommandResult:
    return _sg_gateway_privileged_result("geofiles.rollback")


def _routing_apply() -> HostCommandResult:
    return _sg_gateway_privileged_result("routing.apply")


def _routing_rollback() -> HostCommandResult:
    return _sg_gateway_privileged_result("routing.rollback")


def _warp_install() -> HostCommandResult:
    return _sg_gateway_privileged_result("warp.install")


def _warp_recreate() -> HostCommandResult:
    return _sg_gateway_privileged_result("warp.recreate")


def _warp_enable() -> HostCommandResult:
    return _sg_gateway_privileged_result("warp.enable")


def _warp_disable() -> HostCommandResult:
    return _sg_gateway_privileged_result("warp.disable")


def _warp_remove() -> HostCommandResult:
    return _sg_gateway_privileged_result("warp.remove")


def _warp_test() -> HostCommandResult:
    return _sg_gateway_privileged_result("warp.test")


def _warp_export_json() -> HostCommandResult:
    return _sg_gateway_privileged_result("warp.export_json")


def _tls_renew() -> HostCommandResult:
    try:
        payload = run_tls_maintenance("renew")
        return HostCommandResult(
            command="tls.renew",
            status="ok",
            message=str(payload.get("message") or "Сертификат проверен"),
            payload={
                key: value
                for key, value in payload.items()
                if key not in {"ok", "message"}
            },
        )
    except Exception as exc:
        return HostCommandResult(
            command="tls.renew",
            status="error",
            message=str(exc),
            payload={},
        )


def _tls_rollback() -> HostCommandResult:
    try:
        payload = run_tls_maintenance("rollback")
        return HostCommandResult(
            command="tls.rollback",
            status="ok",
            message=str(payload.get("message") or "HTTPS-конфигурация восстановлена"),
            payload={
                key: value
                for key, value in payload.items()
                if key not in {"ok", "message"}
            },
        )
    except Exception as exc:
        return HostCommandResult(
            command="tls.rollback",
            status="error",
            message=str(exc),
            payload={},
        )


def _clients_apply() -> HostCommandResult:
    try:
        payload = apply_all_clients()
    except Exception as exc:
        return HostCommandResult(
            command="clients.apply",
            status="error",
            message=str(exc),
            payload={},
        )

    return HostCommandResult(
        command="clients.apply",
        status="ok" if payload.get("ok") else "error",
        message=str(payload.get("message") or "Client runtime applied"),
        payload={
            key: value
            for key, value in payload.items()
            if key not in {"ok", "message"}
        },
    )


def _tls_issue_start() -> HostCommandResult:
    try:
        payload = start_tls_issue_job()
        return HostCommandResult(
            command="tls.issue.start",
            status="ok",
            message=str(payload.get("message") or "HTTPS job started"),
            payload=payload,
        )
    except Exception as exc:
        return HostCommandResult(
            command="tls.issue.start",
            status="error",
            message=str(exc),
            payload={},
        )


def _xray_apply() -> HostCommandResult:
    try:
        payload = apply_xray_runtime()
    except Exception as exc:
        return HostCommandResult(
            command="xray.apply",
            status="error",
            message=str(exc),
            payload={},
        )
    return HostCommandResult(
        command="xray.apply",
        status="ok" if payload.get("ok") else "error",
        message=str(payload.get("message") or "Xray runtime applied"),
        payload={
            key: value
            for key, value in payload.items()
            if key not in {"ok", "message"}
        },
    )


def _xray_restore_apply() -> HostCommandResult:
    try:
        payload = apply_xray_runtime(force_profiles=True)
    except Exception as exc:
        return HostCommandResult(
            command="xray.restore.apply",
            status="error",
            message=str(exc),
            payload={},
        )
    return HostCommandResult(
        command="xray.restore.apply",
        status="ok" if payload.get("ok") else "error",
        message=str(payload.get("message") or "Restored Xray runtime applied"),
        payload={key: value for key, value in payload.items() if key not in {"ok", "message"}},
    )


def _xray_apply_start() -> HostCommandResult:
    try:
        payload = start_xray_apply_job()
        return HostCommandResult(command="xray.apply.start", status="ok", message=str(payload.get("message") or "Xray job started"), payload=payload)
    except Exception as exc:
        return HostCommandResult(command="xray.apply.start", status="error", message=str(exc), payload={})


def _xray_update_start(channel: str) -> HostCommandResult:
    command = f"xray.update.{channel}.start"
    try:
        payload = start_xray_update_job(channel)
        return HostCommandResult(
            command=command,
            status="ok",
            message=str(payload.get("message") or "Xray update job started"),
            payload=payload,
        )
    except Exception as exc:
        return HostCommandResult(command=command, status="error", message=str(exc), payload={})


def _xray_update_stable_start() -> HostCommandResult:
    return _xray_update_start("stable")


def _xray_update_prerelease_start() -> HostCommandResult:
    return _xray_update_start("prerelease")


def _xray_runtime_test() -> HostCommandResult:
    payload = test_xray_candidate()
    return HostCommandResult(command="xray.test", status="ok" if payload.get("ok") else "error", message=str(payload.get("message") or "Xray test"), payload=payload)


def _xray_runtime_rollback() -> HostCommandResult:
    try:
        payload = rollback_xray_runtime()
        return HostCommandResult(command="xray.rollback", status="ok", message=str(payload.get("message") or "Xray rollback complete"), payload=payload)
    except Exception as exc:
        return HostCommandResult(command="xray.rollback", status="error", message=str(exc), payload={})

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
    "tls.issue.start": _tls_issue_start,
    "xray.apply": _xray_apply,
    "xray.restore.apply": _xray_restore_apply,
    "xray.apply.start": _xray_apply_start,
    "xray.update.stable.start": _xray_update_stable_start,
    "xray.update.prerelease.start": _xray_update_prerelease_start,
    "xray.test": _xray_runtime_test,
    "xray.rollback": _xray_runtime_rollback,
    "clients.apply": _clients_apply,
    "geofiles.apply": _geofiles_apply,
    "geofiles.rollback": _geofiles_rollback,
    "routing.apply": _routing_apply,
    "routing.rollback": _routing_rollback,
    "warp.install": _warp_install,
    "warp.recreate": _warp_recreate,
    "warp.enable": _warp_enable,
    "warp.disable": _warp_disable,
    "warp.remove": _warp_remove,
    "warp.test": _warp_test,
    "warp.export_json": _warp_export_json,
    "tls.renew": _tls_renew,
    "tls.rollback": _tls_rollback,
    "mihomo.apply": _mihomo_apply,
    "mihomo.test": _mihomo_test,
    "mihomo.restart": _mihomo_restart,
    "mihomo.rollback": _mihomo_rollback,
    "awg.status": _awg_status,
    "xray.status": _xray_status,
    "nftables.status": _nftables_status,
    "system.diagnostics": _system_diagnostics,
}