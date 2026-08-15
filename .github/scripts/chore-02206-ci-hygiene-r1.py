from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD_BUILD = "DEV-02206-CONNECTIONS-POLISH-R1"
NEW_BUILD = "DEV-02206-CI-HYGIENE-R1"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8", newline="\n")


assert read("BUILD-ID").strip() == OLD_BUILD
write("BUILD-ID", NEW_BUILD + "\n")

# Remove only development-line leftovers. The frozen dev-02205 branch keeps
# its own copy of ci-02205-dev.yml and remains untouched.
for relative in (
    ".github/workflows/ci-02205-dev.yml",
    ".github/workflows/patch-full-backup-upload-routes.yml",
    "deploy/patch_full_backup_upload_routes.py",
):
    path = ROOT / relative
    assert path.is_file(), relative
    path.unlink()

workflow = read(".github/workflows/ci-02206-dev.yml")
assert workflow.count(OLD_BUILD) == 1
write(".github/workflows/ci-02206-dev.yml", workflow.replace(OLD_BUILD, NEW_BUILD))

identity = read("tests/test_sg_gateway_02206_development_identity.py")
assert identity.count(OLD_BUILD) == 2
write("tests/test_sg_gateway_02206_development_identity.py", identity.replace(OLD_BUILD, NEW_BUILD))

manifest_path = ROOT / "release-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
assert manifest["version"] == "0.1.0-022.06"
assert manifest["build"] == OLD_BUILD
assert manifest["channel"] == "dev-02206"
assert manifest["development_feature"]["id"] == "connections-polish-r1"
manifest["build"] = NEW_BUILD
manifest["development_hygiene"] = {
    "id": "ci-hygiene-r1",
    "scope": "repository-workflows-only",
    "runtime_changes": False,
    "removed": [
        ".github/workflows/ci-02205-dev.yml",
        ".github/workflows/patch-full-backup-upload-routes.yml",
        "deploy/patch_full_backup_upload_routes.py",
    ],
    "preserves_frozen_branch": "dev-02205",
}
manifest_path.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
    newline="\n",
)

changelog = read("CHANGELOG.md")
anchor = "- Connections polish R1 restores the previously CI-verified balanced AmneziaWG/Mihomo layout and compact XHTTP rows as a UI-only change; Gecko, SG-Panel XMUX and VPN runtime are preserved.\n"
assert changelog.count(anchor) == 1
write(
    "CHANGELOG.md",
    changelog.replace(
        anchor,
        anchor
        + "- CI hygiene R1 removes the inherited 022.05 development workflow and the completed Full Backup patch generator/workflow from dev-02206; runtime behavior is unchanged.\n",
        1,
    ),
)

test = r'''from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_02206_has_only_current_and_main_ci_workflows() -> None:
    workflows = {p.name for p in (ROOT / ".github" / "workflows").glob("*.yml")}
    assert workflows == {"ci.yml", "ci-02206-dev.yml"}
    assert "ci-02205-dev.yml" not in workflows
    assert "patch-full-backup-upload-routes.yml" not in workflows


def test_completed_full_backup_patch_generator_is_not_shipped() -> None:
    assert not (ROOT / "deploy" / "patch_full_backup_upload_routes.py").exists()
    runtime = _text("hostd/sg_hostd/full_backup_runtime.py")
    install = _text("install.sh")
    panel_access = _text("deploy/configure-panel-access.sh")
    for marker in (
        "/maintenance/full-backups/restore",
        "/maintenance/full-backups/verify",
    ):
        assert marker in runtime
        assert marker in install
        assert marker in panel_access
    assert "SG_GATEWAY_FULL_BACKUP_UPLOAD_FIX2" in runtime


def test_ci_hygiene_is_declared_non_runtime() -> None:
    assert _text("BUILD-ID").strip() == "DEV-02206-CI-HYGIENE-R1"
    manifest = json.loads(_text("release-manifest.json"))
    assert manifest["build"] == "DEV-02206-CI-HYGIENE-R1"
    hygiene = manifest["development_hygiene"]
    assert hygiene["id"] == "ci-hygiene-r1"
    assert hygiene["scope"] == "repository-workflows-only"
    assert hygiene["runtime_changes"] is False
    assert hygiene["preserves_frozen_branch"] == "dev-02205"
    assert set(hygiene["removed"]) == {
        ".github/workflows/ci-02205-dev.yml",
        ".github/workflows/patch-full-backup-upload-routes.yml",
        "deploy/patch_full_backup_upload_routes.py",
    }
'''
write("tests/test_sg_gateway_02206_ci_hygiene.py", test)
