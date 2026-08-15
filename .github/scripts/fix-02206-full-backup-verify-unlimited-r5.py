from __future__ import annotations

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
r4 = Path(__file__).with_name("fix-02206-full-backup-verify-unlimited-r4.py")
runpy.run_path(str(r4), run_name="__main__")

path = ROOT / "tests/test_sg_gateway_02206_ci_hygiene.py"
body = path.read_text(encoding="utf-8")
old = 'assert "SG_GATEWAY_FULL_BACKUP_UPLOAD_FIX2" in runtime'
new = 'assert "SG_GATEWAY_FULL_BACKUP_UPLOAD_UNLIMITED_V1" in runtime'
assert body.count(old) == 1
path.write_text(body.replace(old, new, 1), encoding="utf-8", newline="\n")
