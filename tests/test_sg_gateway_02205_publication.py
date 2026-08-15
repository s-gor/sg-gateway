from __future__ import annotations

import json

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_02205_publication_identity_matches_live_release() -> None:
    if _text("VERSION").strip() != "0.1.0-022.05":
        pytest.skip("historical 022.05 publication identity")
    assert _text("VERSION").strip() == "0.1.0-022.05"
    assert _text("BUILD-ID").strip() == "LIVE-02205-SGPANEL-XMUX-WARP-UPDATER-R4"
    manifest = json.loads(_text("release-manifest.json"))
    assert manifest["version"] == "0.1.0-022.05"
    assert manifest["build"] == "LIVE-02205-SGPANEL-XMUX-WARP-UPDATER-R4"
    assert manifest["status"] == "LIVE"
    assert manifest["next_development_line"] == "0.1.0-022.06"
    assert manifest["channel"] == "dev-02205"
    assert manifest["maintenance_updates"]["panel"]["channel"] == "dev-02205"
    assert manifest["publication"]["live_validated_commit"] == "9fbf42aea2bde80a99229de5661a93b6dce4f6c1"
    assert manifest["publication"]["live_validated_tree"] == "c482dc4f158dc1d61c2ba1d683a14e96d24dac68"
    assert manifest["publication"]["runtime_changes_after_live_validation"] is False


def test_full_builder_is_current_and_version_driven() -> None:
    body = _text("build-run.sh")
    assert 'VERSION="$(tr -d' in body
    assert 'BUILD_ID="$(tr -d' in body
    assert 'git -C "$ROOT" archive --format=tar HEAD' in body
    assert '__SG_GATEWAY_BINARY_PAYLOAD_V1__' in body
    assert 'SOURCE-SHA256SUMS' in body
    assert 'SG-Gateway-02112-FULL-CLEAN.run' not in body
    assert 'EXPECTED_VERSION="0.1.0-021.12"' not in body
    wrapper = _text("build-run-vendored.sh")
    assert 'SG-Gateway-${VERSION}-FULL.run' in wrapper
    assert '02112' not in wrapper


def test_main_ci_validates_current_release_not_02112_freeze() -> None:
    body = _text(".github/workflows/ci.yml")
    assert 'Verify source integrity' in body
    assert 'Run full repository suite' in body
    assert 'Build and verify current FULL package' in body
    assert 'manifest["status"] == "LIVE"' in body
    assert '0.1.0-022.06' in body
    assert 'FINAL-AWG2' not in body
    assert 'SG-Gateway-02112-FULL-CLEAN.run' not in body


def test_publication_docs_point_to_current_live_line() -> None:
    readme = _text("README.md")
    assert 'version-0.1.0--022.05' in readme
    assert 'status-LIVE' in readme
    publication = _text("PUBLICATION-02205.md")
    assert "9fbf42aea2bde80a99229de5661a93b6dce4f6c1" in publication
    assert "472 passed, 4 skipped" in publication
