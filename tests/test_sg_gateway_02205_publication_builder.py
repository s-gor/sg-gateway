from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _builder() -> str:
    return (ROOT / "build-run.sh").read_text(encoding="utf-8")


def test_current_builder_keeps_binary_payload_and_self_verification() -> None:
    body = _builder()
    assert 'PAYLOAD_MARKER="__SG_GATEWAY_BINARY_PAYLOAD_V1__"' in body
    assert 'cat "$PAYLOAD" >> "$OUT"' in body
    assert "base64 -d" not in body
    assert '"$OUT" --verify-only' in body
    assert 'RUN_SHA="$(sha256sum "$OUT"' in body
    assert 'zip -q -j "$TRANSFER_ZIP" "$OUT" "$SHA_FILE"' in body


def test_current_builder_acceptance_is_inventory_and_syntax_driven() -> None:
    body = _builder()
    assert '(cd "$STAGE" && sha256sum -c SOURCE-SHA256SUMS' in body
    assert 'actual != listed' in body
    assert 'source inventory mismatch:' in body
    assert "bash -n \"$shell_file\"" in body
    assert 'ast.parse(path.read_text' in body
    assert 'json.loads(path.read_text' in body
    assert 'for required in ("install.sh", "deploy/update-from-github.sh", "deploy/install-from-github.sh")' in body
    assert 'release-manifest VERSION mismatch' in body
    assert 'BUILD-ID mismatch' in body


def test_builder_is_version_driven_not_frozen_to_historical_release() -> None:
    body = _builder()
    assert 'VERSION="$(tr -d' in body
    assert 'BUILD_ID="$(tr -d' in body
    assert 'DEFAULT_BASENAME="SG-Gateway-${VERSION}-FULL"' in body
    assert 'SOURCE_FOLDER="SG-Gateway-${VERSION}-SOURCE"' in body
    assert "SG-Gateway-02112-FULL-CLEAN.run" not in body
    assert "__SG_GATEWAY_02110_BINARY_PAYLOAD_BELOW__" not in body
