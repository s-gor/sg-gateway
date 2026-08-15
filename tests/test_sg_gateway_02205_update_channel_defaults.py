from pathlib import Path

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
