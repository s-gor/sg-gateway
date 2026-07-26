from __future__ import annotations

import json
import sys
import traceback


def _dump(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str), flush=True)


def run_tls() -> int:
    from app.security.tls import root_issue
    print("[HTTPS 1/7] Проверяю подготовленный запрос и DNS", flush=True)
    _dump(root_issue())
    print("[HTTPS 6/7] Применяю клиентские runtime после появления сертификата", flush=True)
    try:
        from sg_hostd.client_runtime import apply_all_clients
        result = apply_all_clients()
        _dump(result)
        if not result.get("ok"):
            print("[HTTPS] Сертификат установлен, но не все клиентские runtime применились.", flush=True)
    except Exception as exc:
        print(f"[HTTPS] Предупреждение runtime: {exc}", flush=True)
    print("[HTTPS 7/7] Панель переведена на HTTPS", flush=True)
    return 0


def run_xray() -> int:
    from app.xray.profiles import overview
    from sg_hostd.client_runtime import _apply_xray
    state = overview()
    print("[Xray 1/4] Независимые профили:", flush=True)
    for item in state["profiles"]:
        flow = f"; flow {item.flow}" if getattr(item, "flow", "") else ""
        print(f"  - {item.title}: {item.status}; {item.transport}; порт {item.port}{flow}", flush=True)
    print("[Xray 2/4] Собираю единый candidate config.json", flush=True)
    print("[Xray 3/4] Выполняю xray run -test и атомарное применение", flush=True)
    result = _apply_xray()
    _dump(result.__dict__ if hasattr(result, "__dict__") else result)
    if not getattr(result, "ok", False):
        raise RuntimeError(getattr(result, "message", "Xray apply failed"))
    print("[Xray 4/4] Служба Xray проверена", flush=True)
    return 0




def run_xray_update(channel: str) -> int:
    from sg_hostd.xray_update_runtime import update_xray
    print("[Xray Update] Подготавливаю безопасное обновление", flush=True)
    result = update_xray(channel)
    _dump(result)
    return 0

def main() -> int:
    if len(sys.argv) != 3:
        return 2
    try:
        if sys.argv[1] == "tls_issue":
            return run_tls()
        if sys.argv[1] == "xray_apply":
            return run_xray()
        if sys.argv[1] == "xray_update_stable":
            return run_xray_update("stable")
        if sys.argv[1] == "xray_update_prerelease":
            return run_xray_update("prerelease")
        raise RuntimeError(f"Неизвестный тип задачи: {sys.argv[1]}")
    except Exception as exc:
        print(f"[SG-Gateway] ОШИБКА: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
