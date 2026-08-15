from __future__ import annotations

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
r5 = Path(__file__).with_name("fix-02206-full-backup-verify-unlimited-r5.py")
runpy.run_path(str(r5), run_name="__main__")

path = ROOT / "tests/test_sg_gateway_02111_backup_domain_release.py"
body = path.read_text(encoding="utf-8")
old = '''    assert "SG_GATEWAY_FULL_BACKUP_UPLOAD_FIX1" in access\n    assert "client_max_body_size 1024m;" in access\n    assert "proxy_read_timeout 300s;" in access\n    assert "def _ensure_full_restore_upload_nginx()" in runtime\n'''
new = '''    assert "SG_GATEWAY_FULL_BACKUP_UPLOAD_FIX1" in access\n    assert "client_max_body_size 1024m;" not in access\n    assert access.count("client_max_body_size 0;") >= 2\n    assert "proxy_read_timeout 300s;" in access\n    assert "def _ensure_full_restore_upload_nginx()" in runtime\n    assert "SG_GATEWAY_FULL_BACKUP_UPLOAD_UNLIMITED_V1" in runtime\n    assert "client_max_body_size 1024m;" not in runtime\n    assert "client_max_body_size 0;" in runtime\n'''
assert body.count(old) == 1
path.write_text(body.replace(old, new, 1), encoding="utf-8", newline="\n")
