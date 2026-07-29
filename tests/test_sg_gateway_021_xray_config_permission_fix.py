from __future__ import annotations

import json
import stat
from pathlib import Path
from types import SimpleNamespace

from app.routing import runtime, warp_helper


def _fake_nobody(monkeypatch, gid: int = 65534) -> None:
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="nobody\n", returncode=0),
    )
    monkeypatch.setattr(
        runtime.pwd,
        "getpwnam",
        lambda name: SimpleNamespace(pw_gid=gid),
    )


def test_atomic_xray_write_keeps_service_readable_permissions(monkeypatch, tmp_path):
    config = tmp_path / "config.json"
    monkeypatch.setenv("SG_GATEWAY_XRAY_CONFIG", str(config))
    _fake_nobody(monkeypatch)
    ownership = []
    monkeypatch.setattr(runtime.os, "chown", lambda path, uid, gid: ownership.append((Path(path), uid, gid)))

    runtime.atomic_write_json(config, {"inbounds": [], "outbounds": []}, 0o600)

    assert json.loads(config.read_text(encoding="utf-8"))["inbounds"] == []
    assert stat.S_IMODE(config.stat().st_mode) == 0o640
    assert ownership and ownership[-1][1:] == (0, 65534)


def test_warp_rollback_keeps_xray_config_service_readable(monkeypatch, tmp_path):
    config = tmp_path / "config.json"
    monkeypatch.setenv("SG_GATEWAY_XRAY_CONFIG", str(config))
    _fake_nobody(monkeypatch, gid=1234)
    ownership = []
    monkeypatch.setattr(runtime.os, "chown", lambda path, uid, gid: ownership.append((Path(path), uid, gid)))

    warp_helper._restore_file(config, b"{}\n", 0o600)

    assert stat.S_IMODE(config.stat().st_mode) == 0o640
    assert ownership and ownership[-1][1:] == (0, 1234)


def test_installer_repairs_xray_permissions_after_warp():
    source = Path("install.sh").read_text(encoding="utf-8")
    assert "set_xray_config_permissions()" in source
    warp_stage = source.split("stage9_ensure_warp() {", 1)[1].split("\nstage9_start_panel()", 1)[0]
    assert "set_xray_config_permissions" in warp_stage
    assert "systemctl restart xray.service" in warp_stage
    assert "systemctl is-active --quiet xray.service" in warp_stage
