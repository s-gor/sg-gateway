from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = 'BRANCH="${SG_GATEWAY_GITHUB_BRANCH:-main}"'
NEW = 'BRANCH="${SG_GATEWAY_GITHUB_BRANCH:-${SG_GATEWAY_UPDATE_BRANCH:-dev-02205}}"'

for relative in ("deploy/update-from-github.sh", "deploy/install-from-github.sh"):
    path = ROOT / relative
    body = path.read_text(encoding="utf-8")
    count = body.count(OLD)
    if count != 1:
        raise RuntimeError(f"{relative}: expected one implicit-main branch default, got {count}")
    body = body.replace(OLD, NEW)
    path.write_text(body, encoding="utf-8", newline="\n")

# Current regression: all active 022.05 panel/bootstrap paths must share the same
# explicit update channel and must never silently fall back to main.
test = ROOT / "tests/test_sg_gateway_02205_update_channel_defaults.py"
test.write_text(
    '''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_active_shell_wrappers_default_to_02205_channel() -> None:
    expected = 'BRANCH="${SG_GATEWAY_GITHUB_BRANCH:-${SG_GATEWAY_UPDATE_BRANCH:-dev-02205}}"'
    for relative in ("deploy/update-from-github.sh", "deploy/install-from-github.sh"):
        body = (ROOT / relative).read_text(encoding="utf-8")
        assert expected in body
        assert 'SG_GATEWAY_GITHUB_BRANCH:-main' not in body
        assert 'SG_GATEWAY_UPDATE_BRANCH:-main' not in body


def test_panel_overview_and_jobs_use_same_02205_channel() -> None:
    overview = (ROOT / "app/maintenance/panel_updates.py").read_text(encoding="utf-8")
    jobs = (ROOT / "hostd/sg_hostd/operation_jobs.py").read_text(encoding="utf-8")
    runner = (ROOT / "hostd/sg_hostd/operation_job_runner.py").read_text(encoding="utf-8")
    assert 'GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02205")' in overview
    assert 'SG_GATEWAY_GITHUB_BRANCH={GITHUB_BRANCH}' in jobs
    assert 'env["SG_GATEWAY_GITHUB_BRANCH"] = GITHUB_BRANCH' in runner


def test_release_manifest_declares_02205_update_channel() -> None:
    import json

    manifest = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["channel"] == "dev-02205"
    assert manifest["maintenance_updates"]["panel"]["channel"] == "dev-02205"
''',
    encoding="utf-8",
    newline="\n",
)

print("022.05 update-channel defaults patch: applied")
