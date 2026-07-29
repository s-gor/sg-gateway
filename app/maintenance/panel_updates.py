from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.version import ROOT as APP_ROOT, get_version


GITHUB_REPO = os.getenv("SG_GATEWAY_UPDATE_REPO", "s-gor/sg-gateway").strip() or "s-gor/sg-gateway"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}"
STATE_FILE = Path(os.getenv("SG_GATEWAY_PANEL_UPDATE_STATE", "/var/lib/sg-gateway/updates/panel-state.json"))
CACHE_TTL_SECONDS = 300
_CACHE: tuple[float, dict[str, Any]] | None = None


class PanelUpdateError(RuntimeError):
    pass


def _fingerprint_ignored(relative: Path) -> bool:
    parts = relative.parts
    return (
        ".venv" in parts
        or ".git" in parts
        or ".pytest_cache" in parts
        or "__pycache__" in parts
        or relative.suffix in {".pyc", ".pyo"}
        or ("vendor" in parts and "cores" in parts)
    )


def source_fingerprint(root: Path = APP_ROOT) -> str:
    digest = hashlib.sha256()
    if not root.is_dir():
        return ""
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
        relative = path.relative_to(root)
        if _fingerprint_ignored(relative):
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        try:
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
        except OSError:
            return ""
        digest.update(b"\0")
    return digest.hexdigest()


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SG-Gateway-Panel-Updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _request_json(url: str, timeout: float = 8.0) -> Any:
    request = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise PanelUpdateError(f"Не удалось проверить GitHub main: {exc}") from exc


def _read_state() -> dict[str, Any]:
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def overview(*, refresh: bool = False) -> dict[str, Any]:
    global _CACHE
    now = time.monotonic()
    state = _read_state()
    installed_commit = str(state.get("commit") or "").strip().lower()
    recorded_fingerprint = str(state.get("source_fingerprint") or "").strip().lower()
    current_fingerprint = source_fingerprint()
    baseline_valid = bool(installed_commit and recorded_fingerprint and current_fingerprint and recorded_fingerprint == current_fingerprint)
    installed_version = get_version()

    if not refresh and _CACHE and now - _CACHE[0] < CACHE_TTL_SECONDS:
        cached = dict(_CACHE[1])
        cached["installed_commit"] = installed_commit
        cached["installed_version"] = installed_version
        cached["source_fingerprint"] = current_fingerprint
        cached["baseline_valid"] = baseline_valid
        if not baseline_valid:
            cached["state"] = "uninitialized"
            cached["can_install"] = False
            cached["message"] = "GitHub baseline ещё не привязан к этой локальной базе или после привязки код менялся. Panel Update заблокирован до публикации/синхронизации текущей базы."
        elif installed_commit == cached.get("latest_commit"):
            cached["state"] = "current"
            cached["can_install"] = False
            cached["message"] = "Локальная база уже соответствует проверенному GitHub main."
        elif cached.get("latest_commit"):
            cached["state"] = "available"
            cached["can_install"] = True
            cached["message"] = "GitHub main содержит новый commit. Можно выполнить безопасное обновление панели."
        return cached

    try:
        payload = _request_json(f"{GITHUB_API}/commits/main")
        if not isinstance(payload, dict):
            raise PanelUpdateError("GitHub не вернул commit main")
        sha = str(payload.get("sha") or "").strip().lower()
        if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha):
            raise PanelUpdateError("GitHub вернул некорректный SHA commit")
        commit = payload.get("commit") if isinstance(payload.get("commit"), dict) else {}
        author = commit.get("author") if isinstance(commit.get("author"), dict) else {}
        latest_date = str(author.get("date") or "")
        html_url = str(payload.get("html_url") or "")
        current = bool(baseline_valid and installed_commit == sha)
        can_install = bool(baseline_valid and not current)
        result = {
            "checked": True,
            "error": "",
            "repo": GITHUB_REPO,
            "installed_version": installed_version,
            "installed_commit": installed_commit,
            "source_fingerprint": current_fingerprint,
            "baseline_valid": baseline_valid,
            "latest_commit": sha,
            "latest_short": sha[:8],
            "latest_date": latest_date,
            "html_url": html_url,
            "state": "current" if current else ("available" if baseline_valid else "uninitialized"),
            "can_install": can_install,
            "message": (
                "Локальная база уже соответствует проверенному GitHub main."
                if current
                else (
                    "Доступен новый commit GitHub main. Перед применением будет создана полная страховочная копия кода."
                    if baseline_valid
                    else "GitHub baseline ещё не привязан к этой локальной базе или локальный код изменён после привязки. Panel Update намеренно заблокирован."
                )
            ),
        }
        _CACHE = (now, result)
        return dict(result)
    except PanelUpdateError as exc:
        return {
            "checked": False,
            "error": str(exc),
            "repo": GITHUB_REPO,
            "installed_version": installed_version,
            "installed_commit": installed_commit,
            "source_fingerprint": current_fingerprint,
            "baseline_valid": baseline_valid,
            "latest_commit": "",
            "latest_short": "",
            "latest_date": "",
            "html_url": "",
            "state": "unavailable",
            "can_install": False,
            "message": "Проверка GitHub main не выполнена.",
        }
