from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD_VERSION = "0.1.0-022.05"
NEW_VERSION = "0.1.0-022.06"
OLD_CHANNEL = "dev-02205"
NEW_CHANNEL = "dev-02206"
NEW_BUILD = "DEV-02206-BASE-R1"
PUBLICATION_COMMIT = "a0c2537b6c55d1fd974afe3aab586a7d41777cd8"
PUBLICATION_TREE = "044d3c166015f8250a1d800584c898ca927da33f"
LIVE_COMMIT = "9fbf42aea2bde80a99229de5661a93b6dce4f6c1"
LIVE_TREE = "c482dc4f158dc1d61c2ba1d683a14e96d24dac68"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


write("VERSION", NEW_VERSION + "\n")
write("BUILD-ID", NEW_BUILD + "\n")

install = read("install.sh")
assert 'VERSION="0.1.0-022.05"' in install
assert 'INSTALLER_BUILD="02205-sgpanel-xmux-warp-updater-r1"' in install
assert 'INSTALL_LOG="/var/log/sg-gateway-installer-02205.log"' in install
assert 'RESUME_FILE="/root/sg-gateway-02205-installer-resume.env"' in install
assert 'before-sg-gateway-02205' in install
install = install.replace(OLD_VERSION, NEW_VERSION).replace("02205", "02206")
assert OLD_VERSION not in install
assert "02205" not in install
write("install.sh", install)

production = read("app/production.py")
assert 'SG-Gateway 0.1.0-022.05+.' in production
production = production.replace('SG-Gateway 0.1.0-022.05+.', 'SG-Gateway 0.1.0-022.06 development.')
write("app/production.py", production)

for relative in ("deploy/install-from-github.sh", "deploy/update-from-github.sh"):
    body = read(relative)
    expected = 'BRANCH="${SG_GATEWAY_GITHUB_BRANCH:-${SG_GATEWAY_UPDATE_BRANCH:-dev-02205}}"'
    replacement = 'BRANCH="${SG_GATEWAY_GITHUB_BRANCH:-${SG_GATEWAY_UPDATE_BRANCH:-dev-02206}}"'
    assert body.count(expected) == 1, (relative, body.count(expected))
    body = body.replace(expected, replacement)
    write(relative, body)

panel_updates = read("app/maintenance/panel_updates.py")
old_line = 'GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02205").strip() or "dev-02205"'
new_line = 'GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02206").strip() or "dev-02206"'
assert panel_updates.count(old_line) == 1
panel_updates = panel_updates.replace(old_line, new_line)
write("app/maintenance/panel_updates.py", panel_updates)

manifest_path = ROOT / "release-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
assert manifest["version"] == OLD_VERSION
assert manifest["build"] == "LIVE-02205-SGPANEL-XMUX-WARP-UPDATER-R4"
assert manifest["status"] == "LIVE"
assert manifest["channel"] == OLD_CHANNEL
assert manifest["maintenance_updates"]["panel"]["channel"] == OLD_CHANNEL
publication = manifest.pop("publication")
assert publication["live_validated_commit"] == LIVE_COMMIT
assert publication["live_validated_tree"] == LIVE_TREE
manifest["version"] = NEW_VERSION
manifest["build"] = NEW_BUILD
manifest["status"] = "DEVELOPMENT"
manifest["next_development_line"] = "0.1.0-022.07"
manifest["channel"] = NEW_CHANNEL
manifest["maintenance_updates"]["panel"]["channel"] = NEW_CHANNEL
manifest["installer_update"]["version"] = "02206-base-r1"
manifest["development_base"] = {
    "version": OLD_VERSION,
    "publication_commit": PUBLICATION_COMMIT,
    "publication_tree": PUBLICATION_TREE,
    "live_validated_commit": LIVE_COMMIT,
    "live_validated_tree": LIVE_TREE,
    "stable_branch": "stable-02205",
    "release_branch": "release-02205-live",
    "frozen_update_channel": OLD_CHANNEL,
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

# Preserve frozen 022.05 tests as historical contracts rather than rewriting their expectations.
for relative, reason in (
    ("tests/test_sg_gateway_02205_update_channel_defaults.py", "historical 022.05 update-channel contract"),
    ("tests/test_sg_gateway_02205_installer_identity.py", "historical 022.05 installer identity contract"),
):
    body = read(relative)
    if "import pytest\n" not in body:
        body = body.replace("from pathlib import Path\n", "from pathlib import Path\n\nimport pytest\n", 1)
    marker = "ROOT = Path(__file__).resolve().parents[1]\n"
    assert marker in body
    guard = (
        marker
        + "CURRENT_VERSION = (ROOT / \"VERSION\").read_text(encoding=\"utf-8\").strip()\n"
        + f"pytestmark = pytest.mark.skipif(CURRENT_VERSION != \"{OLD_VERSION}\", reason=\"{reason}\")\n"
    )
    body = body.replace(marker, guard, 1)
    write(relative, body)

# The publication identity assertion is intentionally frozen to 022.05; other publication/build tests remain useful.
publication_test = read("tests/test_sg_gateway_02205_publication.py")
if "import pytest\n" not in publication_test:
    publication_test = publication_test.replace("import json\n", "import json\n\nimport pytest\n", 1)
needle = "def test_02205_publication_identity_matches_live_release() -> None:\n"
assert needle in publication_test
publication_test = publication_test.replace(
    needle,
    needle + f"    if _text(\"VERSION\").strip() != \"{OLD_VERSION}\":\n        pytest.skip(\"historical 022.05 publication identity\")\n",
    1,
)
write("tests/test_sg_gateway_02205_publication.py", publication_test)

# Safety tests stay active and follow the current development channel.
safety = read("tests/test_sg_gateway_02205_panel_update_safety.py")
safety = safety.replace("test_panel_update_overview_uses_02205_channel_not_main", "test_panel_update_overview_uses_current_development_channel_not_main")
assert safety.count('GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02205")') == 1
safety = safety.replace('GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02205")', 'GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02206")')
write("tests/test_sg_gateway_02205_panel_update_safety.py", safety)

maintenance = read("tests/test_sg_gateway_021_maintenance_updates_v1.py")
assert maintenance.count('GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02205")') == 1
maintenance = maintenance.replace('GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02205")', 'GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02206")')
write("tests/test_sg_gateway_021_maintenance_updates_v1.py", maintenance)

write(
    "tests/test_sg_gateway_02206_update_channel_defaults.py",
    '''from pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\n\n\ndef test_active_shell_wrappers_default_to_02206_channel() -> None:\n    expected = 'BRANCH="${SG_GATEWAY_GITHUB_BRANCH:-${SG_GATEWAY_UPDATE_BRANCH:-dev-02206}}"'\n    for relative in ("deploy/update-from-github.sh", "deploy/install-from-github.sh"):\n        body = (ROOT / relative).read_text(encoding="utf-8")\n        assert expected in body\n        assert 'SG_GATEWAY_GITHUB_BRANCH:-main' not in body\n        assert 'SG_GATEWAY_UPDATE_BRANCH:-main' not in body\n        assert ':-dev-02205' not in body\n\n\ndef test_panel_overview_and_jobs_use_same_02206_channel() -> None:\n    overview = (ROOT / "app/maintenance/panel_updates.py").read_text(encoding="utf-8")\n    jobs = (ROOT / "hostd/sg_hostd/operation_jobs.py").read_text(encoding="utf-8")\n    runner = (ROOT / "hostd/sg_hostd/operation_job_runner.py").read_text(encoding="utf-8")\n    assert 'GITHUB_BRANCH = os.getenv("SG_GATEWAY_UPDATE_BRANCH", "dev-02206")' in overview\n    assert 'SG_GATEWAY_GITHUB_BRANCH={GITHUB_BRANCH}' in jobs\n    assert 'env["SG_GATEWAY_GITHUB_BRANCH"] = GITHUB_BRANCH' in runner\n\n\ndef test_release_manifest_declares_02206_update_channel() -> None:\n    import json\n\n    manifest = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))\n    assert manifest["channel"] == "dev-02206"\n    assert manifest["maintenance_updates"]["panel"]["channel"] == "dev-02206"\n''',
)

write(
    "tests/test_sg_gateway_02206_development_identity.py",
    f'''from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\n\n\ndef _text(path: str) -> str:\n    return (ROOT / path).read_text(encoding="utf-8")\n\n\ndef test_02206_development_identity_is_consistent() -> None:\n    assert _text("VERSION").strip() == "{NEW_VERSION}"\n    assert _text("BUILD-ID").strip() == "{NEW_BUILD}"\n    manifest = json.loads(_text("release-manifest.json"))\n    assert manifest["version"] == "{NEW_VERSION}"\n    assert manifest["build"] == "{NEW_BUILD}"\n    assert manifest["status"] == "DEVELOPMENT"\n    assert manifest["next_development_line"] == "0.1.0-022.07"\n    assert manifest["channel"] == "{NEW_CHANNEL}"\n    assert manifest["maintenance_updates"]["panel"]["channel"] == "{NEW_CHANNEL}"\n    assert "publication" not in manifest\n    base = manifest["development_base"]\n    assert base["version"] == "{OLD_VERSION}"\n    assert base["publication_commit"] == "{PUBLICATION_COMMIT}"\n    assert base["publication_tree"] == "{PUBLICATION_TREE}"\n    assert base["live_validated_commit"] == "{LIVE_COMMIT}"\n    assert base["live_validated_tree"] == "{LIVE_TREE}"\n    assert base["frozen_update_channel"] == "{OLD_CHANNEL}"\n\n\ndef test_02206_installer_identity_is_consistent_and_ten_stage() -> None:\n    body = _text("install.sh")\n    main = body[body.index("main() {{"):]\n    assert 'VERSION="{NEW_VERSION}"' in body\n    assert 'INSTALLER_BUILD="02206-sgpanel-xmux-warp-updater-r1"' in body\n    assert 'INSTALL_LOG="/var/log/sg-gateway-installer-02206.log"' in body\n    assert 'RESUME_FILE="/root/sg-gateway-02206-installer-resume.env"' in body\n    assert 'before-sg-gateway-02206"' in main\n    assert "02205" not in body\n    assert "TOTAL_STAGES=10" in body\n    for stage in range(1, 11):\n        assert f"run_stage {{stage}} " in main\n    assert 'run_stage 10 "Запуск и проверка" stage10_start_and_verify' in main\n\n\ndef test_02206_is_based_on_published_02205_without_claiming_live_status() -> None:\n    changelog = _text("CHANGELOG.md")\n    assert changelog.startswith("# SG-Gateway 0.1.0-022.06 — DEVELOPMENT")\n    assert "Base publication: `{PUBLICATION_COMMIT}`" in changelog\n    assert "Live-validated runtime base: `{LIVE_COMMIT}`" in changelog\n''',
)

ci_02206 = r'''name: CI 022.06 Development

on:
  push:
    branches: [dev-02206]
  pull_request:
    branches: [dev-02206]

jobs:
  development-contracts:
    runs-on: ubuntu-24.04
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements-dev.txt

      - name: Verify 022.06 identity and source integrity
        run: |
          test "$(tr -d '[:space:]' < VERSION)" = "0.1.0-022.06"
          test "$(tr -d '\r\n' < BUILD-ID)" = "DEV-02206-BASE-R1"
          bash -n install.sh
          bash -n build-run.sh
          bash -n build-run-vendored.sh
          bash -n deploy/install-from-github.sh
          bash -n deploy/update-from-github.sh
          python -m pytest -q tests/test_sg_gateway_02206_development_identity.py tests/test_sg_gateway_02206_update_channel_defaults.py tests/test_version.py
          python -m pytest -q tests/test_sg_gateway_02112_final_cumulative_cleanup_r5.py::test_source_checksum_inventory_is_strict_and_complete

      - name: Preserve inherited 022.05 runtime contracts
        run: |
          python -m pytest -q tests/test_sg_gateway_02205_xmux_sgpanel_contract.py
          python -m pytest -q tests/test_sg_gateway_02205_optional_warp_install.py
          python -m pytest -q tests/test_sg_gateway_02205_update_wsgi_isolation.py
          python -m pytest -q tests/test_sg_gateway_02205_panel_update_state_binding.py
          python -m pytest -q tests/test_sg_subscription_v1_*_02205.py
          python -m pytest -q tests/test_sg_gateway_02205_full_backup_verify.py tests/test_sg_gateway_02205_full_backup_verify_ui.py tests/test_sg_gateway_02205_full_backup_verify_mux.py

      - name: Run complete repository suite
        run: python -m pytest -q

      - name: Build and verify development FULL package
        run: |
          command -v zip
          command -v unzip
          OUT=/tmp/SG-Gateway-0.1.0-022.06-FULL.run
          bash build-run.sh "$OUT"
          "$OUT" --verify-only
          test -s /tmp/SG-Gateway-0.1.0-022.06-FULL-SHA256.txt
          test -s /tmp/SG-Gateway-0.1.0-022.06-FULL-TRANSFER.zip
          unzip -t /tmp/SG-Gateway-0.1.0-022.06-FULL-TRANSFER.zip
'''
write(".github/workflows/ci-02206-dev.yml", ci_02206)

changelog = read("CHANGELOG.md")
prefix = f'''# SG-Gateway 0.1.0-022.06 — DEVELOPMENT\n\n- Development branch: `dev-02206`.\n- Base publication: `{PUBLICATION_COMMIT}` / tree `{PUBLICATION_TREE}`.\n- Live-validated runtime base: `{LIVE_COMMIT}` / tree `{LIVE_TREE}`.\n- Initial 022.06 commit changes development identity/channel/CI only; no new VPN/runtime behavior is introduced.\n- Frozen 022.05 updater channel remains `dev-02205`.\n\n'''
if not changelog.startswith("# SG-Gateway 0.1.0-022.06 — DEVELOPMENT"):
    changelog = prefix + changelog
write("CHANGELOG.md", changelog)
