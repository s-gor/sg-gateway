from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_02206_development_identity_is_consistent() -> None:
    assert _text("VERSION").strip() == "0.1.0-022.06"
    assert _text("BUILD-ID").strip() == "DEV-02206-SGPANEL-VLESS-PARITY-R1"
    manifest = json.loads(_text("release-manifest.json"))
    assert manifest["version"] == "0.1.0-022.06"
    assert manifest["build"] == "DEV-02206-SGPANEL-VLESS-PARITY-R1"
    assert manifest["status"] == "DEVELOPMENT"
    assert manifest["next_development_line"] == "0.1.0-022.07"
    assert manifest["channel"] == "dev-02206"
    assert manifest["maintenance_updates"]["panel"]["channel"] == "dev-02206"
    assert "publication" not in manifest
    base = manifest["development_base"]
    assert base["version"] == "0.1.0-022.05"
    assert base["publication_commit"] == "a0c2537b6c55d1fd974afe3aab586a7d41777cd8"
    assert base["publication_tree"] == "044d3c166015f8250a1d800584c898ca927da33f"
    assert base["live_validated_commit"] == "9fbf42aea2bde80a99229de5661a93b6dce4f6c1"
    assert base["live_validated_tree"] == "c482dc4f158dc1d61c2ba1d683a14e96d24dac68"
    assert base["frozen_update_channel"] == "dev-02205"


def test_02206_installer_identity_is_consistent_and_ten_stage() -> None:
    body = _text("install.sh")
    main = body[body.index("main() {"):]
    assert 'VERSION="0.1.0-022.06"' in body
    assert 'INSTALLER_BUILD="02206-sgpanel-xmux-warp-updater-r1"' in body
    assert 'INSTALL_LOG="/var/log/sg-gateway-installer-02206.log"' in body
    assert 'RESUME_FILE="/root/sg-gateway-02206-installer-resume.env"' in body
    assert 'before-sg-gateway-02206"' in main
    assert "02205" not in body
    assert "TOTAL_STAGES=10" in body
    for stage in range(1, 11):
        assert f"run_stage {stage} " in main
    assert 'run_stage 10 "Запуск и проверка" stage10_start_and_verify' in main


def test_02206_is_based_on_published_02205_without_claiming_live_status() -> None:
    changelog = _text("CHANGELOG.md")
    assert changelog.startswith("# SG-Gateway 0.1.0-022.06 — DEVELOPMENT")
    assert "Base publication: `a0c2537b6c55d1fd974afe3aab586a7d41777cd8`" in changelog
    assert "Live-validated runtime base: `9fbf42aea2bde80a99229de5661a93b6dce4f6c1`" in changelog
