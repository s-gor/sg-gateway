from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(body: str, old: str, new: str, label: str) -> str:
    count = body.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 occurrence, got {count}")
    return body.replace(old, new)


# Panel overview: channel-aware, never implicit main.
path = ROOT / "app/maintenance/panel_updates.py"
body = path.read_text(encoding="utf-8")
anchor = 'GITHUB_REPO = os.getenv("SG_GATEWAY_UPDATE_REPO", "s-gor/sg-gateway").strip() or "s-gor/sg-gateway"\n'
body = replace_once(
    body,
    anchor,
    anchor + 'GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02205").strip() or "dev-02205"\n',
    "panel update branch constant",
)
for old, new, label in (
    ('def _latest_main() -> tuple[str, str, str]:', 'def _latest_channel() -> tuple[str, str, str]:', 'latest function'),
    ('f"{GITHUB_API}/commits/main"', 'f"{GITHUB_API}/commits/{GITHUB_BRANCH}"', 'API channel'),
    ('f"https://github.com/{GITHUB_REPO}/commits/main.atom"', 'f"https://github.com/{GITHUB_REPO}/commits/{GITHUB_BRANCH}.atom"', 'Atom channel'),
    ('sha, latest_date, html_url = _latest_main()', 'sha, latest_date, html_url = _latest_channel()', 'overview latest call'),
    ('"Локальная база уже соответствует проверенному GitHub main."', 'f"Локальная база уже соответствует проверенному GitHub {GITHUB_BRANCH}."', 'current message'),
    ('"GitHub main содержит новый commit. Можно выполнить безопасное обновление панели."', 'f"GitHub {GITHUB_BRANCH} содержит новый commit. Можно выполнить безопасное обновление панели."', 'available message'),
    ('"Проверка GitHub main не выполнена."', 'f"Проверка GitHub {GITHUB_BRANCH} не выполнена."', 'error message'),
    ('"GitHub не вернул commit main"', '"GitHub не вернул commit update-channel"', 'API error'),
    ('"GitHub main не удалось определить ни через API, ни через Atom feed"', 'f"GitHub {GITHUB_BRANCH} не удалось определить ни через API, ни через Atom feed"', 'fallback error'),
    ('f"Не удалось проверить GitHub main: {first_exc}; fallback: {second_exc}"', 'f"Не удалось проверить GitHub {GITHUB_BRANCH}: {first_exc}; fallback: {second_exc}"', 'request error'),
):
    body = replace_once(body, old, new, label)
repo_marker = '            "repo": GITHUB_REPO,\n'
if body.count(repo_marker) != 2:
    raise RuntimeError(f"overview repo payload markers: expected 2, got {body.count(repo_marker)}")
body = body.replace(repo_marker, repo_marker + '            "channel": GITHUB_BRANCH,\n')
path.write_text(body, encoding="utf-8", newline="\n")


# New panel-update jobs: execute verified shell updater in the transient systemd job.
path = ROOT / "hostd/sg_hostd/operation_jobs.py"
body = path.read_text(encoding="utf-8")
body = replace_once(
    body,
    'from typing import Any, Sequence\n',
    'from typing import Any, Sequence\n\nfrom app.maintenance.panel_updates import GITHUB_BRANCH\n',
    "operation jobs branch import",
)
body = replace_once(
    body,
    'PANEL_ACCESS_SCRIPT = Path("/opt/sg-gateway/deploy/configure-panel-access.sh")\n',
    'PANEL_ACCESS_SCRIPT = Path("/opt/sg-gateway/deploy/configure-panel-access.sh")\nPANEL_UPDATE_SCRIPT = Path("/opt/sg-gateway/deploy/update-from-github.sh")\n',
    "panel update script constant",
)
start = body.index("def start_panel_update_job() -> dict[str, Any]:")
end = body.index("\ndef start_core_update_job", start)
new_block = '''def start_panel_update_job() -> dict[str, Any]:
    if not PANEL_UPDATE_SCRIPT.is_file():
        raise RuntimeError(f"Не найден {PANEL_UPDATE_SCRIPT}")
    return _start(
        "panel_update_channel",
        f"Безопасное обновление SG-Gateway из GitHub {GITHUB_BRANCH}",
        "/maintenance?tab=updates&refresh=1",
        "/maintenance?tab=updates",
        {"channel": GITHUB_BRANCH, "restart_expected": True},
        command=(
            "/usr/bin/env",
            f"SG_GATEWAY_GITHUB_BRANCH={GITHUB_BRANCH}",
            "/bin/bash",
            str(PANEL_UPDATE_SCRIPT),
        ),
    )

'''
body = body[:start] + new_block + body[end + 1 :]
path.write_text(body, encoding="utf-8", newline="\n")


# Legacy queued panel_update_main jobs: also delegate to the verified shell updater.
path = ROOT / "hostd/sg_hostd/operation_job_runner.py"
body = path.read_text(encoding="utf-8")
body = replace_once(body, "import os\n", "import os\nimport subprocess\n", "runner subprocess import")
start = body.index("def run_panel_update() -> int:")
end = body.index("\ndef run_core_update", start)
new_block = '''def run_panel_update() -> int:
    from app.maintenance.panel_updates import GITHUB_BRANCH

    script = _PROJECT_ROOT / "deploy" / "update-from-github.sh"
    if not script.is_file():
        raise RuntimeError(f"Не найден {script}")
    env = dict(os.environ)
    env["SG_GATEWAY_GITHUB_BRANCH"] = GITHUB_BRANCH
    print(f"[SG-Gateway Update] Запускаю проверенный updater · channel {GITHUB_BRANCH}", flush=True)
    completed = subprocess.run(
        ["/bin/bash", str(script)],
        cwd=str(_PROJECT_ROOT),
        env=env,
        check=False,
    )
    return int(completed.returncode)

'''
body = body[:start] + new_block + body[end + 1 :]
path.write_text(body, encoding="utf-8", newline="\n")


# Legacy Python runtime: make every remaining helper channel-aware and its staged import isolated.
path = ROOT / "hostd/sg_hostd/panel_update_runtime.py"
body = path.read_text(encoding="utf-8")
body = replace_once(
    body,
    'from app.maintenance.panel_updates import GITHUB_API, GITHUB_REPO, STATE_FILE, source_fingerprint\n',
    'from app.maintenance.panel_updates import GITHUB_API, GITHUB_BRANCH, GITHUB_REPO, STATE_FILE, source_fingerprint\n',
    "legacy runtime branch import",
)
for old, new, label in (
    ('def _latest_main_commit() -> str:', 'def _latest_channel_commit() -> str:', 'legacy latest function'),
    ('f"{GITHUB_API}/commits/main"', 'f"{GITHUB_API}/commits/{GITHUB_BRANCH}"', 'legacy API channel'),
    ('"GitHub не вернул commit main"', '"GitHub не вернул commit update-channel"', 'legacy API error'),
    ('"GitHub вернул некорректный SHA main"', '"GitHub вернул некорректный SHA update-channel"', 'legacy SHA error'),
    ('f"https://github.com/{GITHUB_REPO}/commits/main.atom"', 'f"https://github.com/{GITHUB_REPO}/commits/{GITHUB_BRANCH}.atom"', 'legacy Atom channel'),
    ('f"GitHub main недоступен: {exc}"', 'f"GitHub {GITHUB_BRANCH} недоступен: {exc}"', 'legacy unavailable message'),
    ('"GitHub main не удалось определить ни через API, ни через Atom feed"', 'f"GitHub {GITHUB_BRANCH} не удалось определить ни через API, ни через Atom feed"', 'legacy fallback message'),
):
    body = replace_once(body, old, new, label)
old_env = '''    env["SG_GATEWAY_ENV"] = "production"
    env["SG_GATEWAY_DATA_DIR"] = "/var/lib/sg-gateway"
    env["SG_GATEWAY_LOG_DIR"] = "/var/log/sg-gateway"
    check = subprocess.run(
'''
new_env = '''    env["SG_GATEWAY_ENV"] = "production"
    validation_root = root.parent / "wsgi-validation"
    (validation_root / "data").mkdir(parents=True, exist_ok=True)
    (validation_root / "log").mkdir(parents=True, exist_ok=True)
    env["SG_GATEWAY_DATA_DIR"] = str(validation_root / "data")
    env["SG_GATEWAY_LOG_DIR"] = str(validation_root / "log")
    check = subprocess.run(
'''
body = replace_once(body, old_env, new_env, "isolated legacy staged import")
start = body.index("def update_panel() -> dict[str, Any]:")
safe_update = '''def update_panel() -> dict[str, Any]:
    """Compatibility entrypoint: delegate to the verified full-state shell updater."""
    script = LIVE_ROOT / "deploy" / "update-from-github.sh"
    if not script.is_file():
        raise PanelUpdateRuntimeError(f"Не найден безопасный updater: {script}")
    env = dict(os.environ)
    env["SG_GATEWAY_GITHUB_BRANCH"] = GITHUB_BRANCH
    completed = subprocess.run(
        ["/bin/bash", str(script)],
        cwd=str(LIVE_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
        check=False,
    )
    output = "\\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part and part.strip()
    )
    if output:
        print(output, flush=True)
    if completed.returncode:
        raise PanelUpdateRuntimeError(
            output.splitlines()[-1] if output else f"safe updater failed: rc={completed.returncode}"
        )
    version = (LIVE_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    return {
        "ok": True,
        "message": f"SG-Gateway безопасно обновлён из GitHub {GITHUB_BRANCH}; VERSION {version}",
        "channel": GITHUB_BRANCH,
        "version": version,
    }
'''
body = body[:start] + safe_update
path.write_text(body, encoding="utf-8", newline="\n")


# Manifest: record the actually validated update architecture with a minimal JSON rewrite.
path = ROOT / "release-manifest.json"
data = json.loads(path.read_text(encoding="utf-8"))
data["client_access_model"]["sg_panel_transfer_status"] = "live-validated-2026-08-15"
panel = data["maintenance_updates"]["panel"]
panel["source"] = "github-channel-via-verified-shell-updater"
panel["channel"] = "dev-02205"
panel["staged_import_data"] = "isolated-temp-data-log"
panel["state_backup"] = "full-shell-updater-safety-backup"
data["source_integrity"]["mode"] = "sha256-file-inventory"
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


# Historical 021 maintenance tests: retain useful semantics, remove obsolete unsafe implementation pins.
path = ROOT / "tests/test_sg_gateway_021_maintenance_updates_v1.py"
body = path.read_text(encoding="utf-8")
body = body.replace(
    "def test_panel_update_overview_pins_exact_main_commit_but_blocks_unbound_baseline",
    "def test_panel_update_overview_pins_exact_channel_commit_but_blocks_unbound_baseline",
)
old = '''def test_panel_runtime_blocks_dependency_changes_and_has_rollback():
    runtime = (ROOT / "hostd/sg_hostd/panel_update_runtime.py").read_text(encoding="utf-8")
    assert "requirements.txt изменён" in runtime
    assert "_backup_live" in runtime
    assert "_deploy_source(backup)" in runtime
    assert "commits/main" in runtime
    assert "archive/{commit}.tar.gz" in runtime
    assert ".venv" in runtime
    assert "_baseline_mode" in runtime
    assert "Автоматическое обновление сейчас недоступно." in runtime
    assert "локальный исходник не совпадает" not in runtime
'''
new = '''def test_panel_runtime_blocks_dependency_changes_and_delegates_full_state_rollback():
    runtime = (ROOT / "hostd/sg_hostd/panel_update_runtime.py").read_text(encoding="utf-8")
    assert "requirements.txt изменён" in runtime
    assert "_baseline_mode" in runtime
    assert "Автоматическое обновление сейчас недоступно." in runtime
    assert 'validation_root = root.parent / "wsgi-validation"' in runtime
    update = runtime[runtime.index("def update_panel() -> dict[str, Any]:"):]
    assert 'deploy" / "update-from-github.sh"' in update
    assert 'SG_GATEWAY_GITHUB_BRANCH' in update
    assert '_deploy_source(backup)' not in update
    assert "локальный исходник не совпадает" not in runtime
'''
body = replace_once(body, old, new, "historical rollback test")
if body.count('monkeypatch.setattr(panel_updates, "_latest_main"') != 2:
    raise RuntimeError("expected two historical _latest_main monkeypatches")
body = body.replace(
    'monkeypatch.setattr(panel_updates, "_latest_main"',
    'monkeypatch.setattr(panel_updates, "_latest_channel"',
)
old = '''def test_panel_runtime_has_bootstrap_path_and_atom_fallback():
    runtime = (ROOT / "hostd/sg_hostd/panel_update_runtime.py").read_text(encoding="utf-8")
    assert "def _baseline_mode" in runtime
    assert 'return "bootstrap", {}' in runtime
    assert "строго более новую VERSION" in runtime
    assert "updater-baseline" not in runtime
    assert "commits/main.atom" in runtime
'''
new = '''def test_panel_update_has_bootstrap_gate_and_channel_atom_fallback():
    overview = (ROOT / "app/maintenance/panel_updates.py").read_text(encoding="utf-8")
    runtime = (ROOT / "hostd/sg_hostd/panel_update_runtime.py").read_text(encoding="utf-8")
    assert "def _baseline_mode" in runtime
    assert 'return "bootstrap", {}' in runtime
    assert "updater-baseline" not in runtime
    assert 'GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02205")' in overview
    assert 'commits/{GITHUB_BRANCH}.atom' in overview
    assert "commits/main.atom" not in overview
'''
body = replace_once(body, old, new, "historical bootstrap test")
path.write_text(body, encoding="utf-8", newline="\n")


# Current 022.05 regression: explicitly pins the safe architecture.
path = ROOT / "tests/test_sg_gateway_02205_panel_update_safety.py"
path.write_text(
    '''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _function_block(body: str, name: str) -> str:
    start = body.index(f"def {name}(")
    next_def = body.find("\\ndef ", start + 5)
    return body[start:] if next_def < 0 else body[start:next_def]


def test_panel_update_overview_uses_02205_channel_not_main() -> None:
    body = (ROOT / "app/maintenance/panel_updates.py").read_text(encoding="utf-8")
    assert 'GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02205")' in body
    latest = _function_block(body, "_latest_channel")
    assert 'commits/{GITHUB_BRANCH}' in latest
    assert 'commits/main' not in latest


def test_panel_update_job_delegates_to_verified_shell_updater() -> None:
    body = (ROOT / "hostd/sg_hostd/operation_jobs.py").read_text(encoding="utf-8")
    block = _function_block(body, "start_panel_update_job")
    assert "PANEL_UPDATE_SCRIPT" in block
    assert "SG_GATEWAY_GITHUB_BRANCH={GITHUB_BRANCH}" in block
    assert "command=(" in block
    assert "panel_update_channel" in block


def test_legacy_panel_update_runner_is_also_safe() -> None:
    body = (ROOT / "hostd/sg_hostd/operation_job_runner.py").read_text(encoding="utf-8")
    block = _function_block(body, "run_panel_update")
    assert "update-from-github.sh" in block
    assert "SG_GATEWAY_GITHUB_BRANCH" in block
    assert "panel_update_runtime" not in block


def test_old_python_staging_import_cannot_touch_production_db() -> None:
    body = (ROOT / "hostd/sg_hostd/panel_update_runtime.py").read_text(encoding="utf-8")
    block = _function_block(body, "_validate_snapshot")
    assert 'validation_root = root.parent / "wsgi-validation"' in block
    assert 'env["SG_GATEWAY_DATA_DIR"] = str(validation_root / "data")' in block
    assert 'env["SG_GATEWAY_LOG_DIR"] = str(validation_root / "log")' in block
    assert 'env["SG_GATEWAY_DATA_DIR"] = "/var/lib/sg-gateway"' not in block


def test_python_update_entrypoint_delegates_instead_of_mutating_source_itself() -> None:
    body = (ROOT / "hostd/sg_hostd/panel_update_runtime.py").read_text(encoding="utf-8")
    block = _function_block(body, "update_panel")
    assert 'deploy" / "update-from-github.sh"' in block
    assert "SG_GATEWAY_GITHUB_BRANCH" in block
    assert "_backup_live(" not in block
    assert "_deploy_source(" not in block


def test_legacy_runtime_helpers_are_channel_aware() -> None:
    body = (ROOT / "hostd/sg_hostd/panel_update_runtime.py").read_text(encoding="utf-8")
    latest = _function_block(body, "_latest_channel_commit")
    assert 'commits/{GITHUB_BRANCH}' in latest
    assert "commits/main" not in latest
''',
    encoding="utf-8",
    newline="\n",
)

print("022.05 panel update safety patch: applied")
