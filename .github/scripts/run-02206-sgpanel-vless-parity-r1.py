from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = Path(__file__).with_name("apply-02206-sgpanel-vless-parity-r1.py")
source = path.read_text(encoding="utf-8")
old = '    assert "location /sg-xhttp-tls/ {" in snippet\n'
new = '    assert "location /sg-xhttp-tls/ {{" in snippet\n'
assert source.count(old) == 1
source = source.replace(old, new, 1)
code = compile(source, str(path), "exec")
exec(code, {"__name__": "__main__", "__file__": str(path)})

# Correct only regression fixtures/expectations after the candidate generator.
test_path = ROOT / "tests" / "test_sg_gateway_02206_sgpanel_vless_parity.py"
test = test_path.read_text(encoding="utf-8")
valid_encryption = "mlkem768x25519plus.native.0rtt.test.CLIENT"
valid_decryption = "mlkem768x25519plus.native.600s.test.SERVER"
test, count = re.subn(r'^ENCRYPTION = ".*"$', f'ENCRYPTION = "{valid_encryption}"', test, count=1, flags=re.M)
assert count == 1
test, count = re.subn(r'^DECRYPTION = ".*"$', f'DECRYPTION = "{valid_decryption}"', test, count=1, flags=re.M)
assert count == 1
old_order = '    assert updated.index(INCLUDE_DIRECTIVE) < updated.index("location / { return 404; }")\n'
new_order = '    first_server = updated.split("server { listen 63443 ssl; }", 1)[0]\n    assert INCLUDE_DIRECTIVE in first_server\n'
assert test.count(old_order) == 1
test = test.replace(old_order, new_order, 1)
test, count = re.subn(
    r'    assert updater\.startswith\([^\n]+\)\n',
    '    assert updater.splitlines()[:5] == ["#!/usr/bin/env bash", "set -Eeuo pipefail", "", "# The updater replaces /opt/sg-gateway. Never inherit a cwd inside that tree.", "cd /"]\n',
    test,
    count=1,
)
assert count == 1
for signature in (
    'def test_xhttp_tls_runtime_matches_panel_local_plain_xray(monkeypatch) -> None:\n',
    'def test_xhttp_tls_auto_mode_is_server_default_not_forced_field(monkeypatch) -> None:\n',
):
    injection = signature + '    monkeypatch.setattr(client_runtime, "normalize_pair", lambda encryption, decryption: (str(encryption), str(decryption), False))\n'
    assert test.count(signature) == 1
    test = test.replace(signature, injection, 1)
test_path.write_text(test, encoding="utf-8", newline="\n")
compile(test, str(test_path), "exec")

# ---------------------------------------------------------------------------
# Full-suite regressions that encoded the pre-parity implementation details.
# ---------------------------------------------------------------------------
path_02110 = ROOT / "tests" / "test_sg_gateway_02110_cumulative.py"
body = path_02110.read_text(encoding="utf-8")
old = "    assert 'listen 127.0.0.1:$PLACEHOLDER_TLS_INTERNAL_PORT ssl;' in script\n"
new = "    assert 'listen 127.0.0.1:$PLACEHOLDER_TLS_INTERNAL_PORT ssl http2;' in script\n    assert 'include /etc/nginx/snippets/sg-gateway-xhttp-tls.conf;' in script\n"
assert body.count(old) == 1
path_02110.write_text(body.replace(old, new, 1), encoding="utf-8", newline="\n")

path_xmux = ROOT / "tests" / "test_sg_gateway_021_xmux_rf.py"
body = path_xmux.read_text(encoding="utf-8")
old = "    assert 'query_values[\"extra\"]' in exports\n"
new = "    assert 'xhttp_tls_link' in exports\n    assert 'xmux=(' in exports\n"
assert body.count(old) == 1
path_xmux.write_text(body.replace(old, new, 1), encoding="utf-8", newline="\n")

path_tls = ROOT / "tests" / "test_sg_gateway_021_xray_tls_material.py"
body = path_tls.read_text(encoding="utf-8")
old = '''def test_xray_config_uses_private_runtime_tls_copy():\n    source = Path("hostd/sg_hostd/client_runtime.py").read_text(encoding="utf-8")\n    assert 'cert, key = _sync_xray_tls_material(domain)' in source\n    tls_block = source.split("tls_needed =", 1)[1].split("if \\"xhttp_tls\\"", 1)[0]\n    assert "/etc/letsencrypt/live/" not in tls_block\n    assert 'XRAY_TLS_DIR = Path("/usr/local/etc/xray/tls")' in source\n'''
new = '''def test_xray_config_uses_private_runtime_tls_copy():\n    source = Path("hostd/sg_hostd/client_runtime.py").read_text(encoding="utf-8")\n    assert 'cert, key = _sync_xray_tls_material(domain)' in source\n    hysteria_block = source.split('if "hysteria2" in enabled_profiles:', 1)[1].split("if not inbounds:", 1)[0]\n    assert 'cert, key = _sync_xray_tls_material(domain)' in hysteria_block\n    assert "/etc/letsencrypt/live/" not in hysteria_block\n    xhttp_block = source.split('if "xhttp_tls" in enabled_profiles:', 1)[1].split('if "hysteria2" in enabled_profiles:', 1)[0]\n    assert '_sync_xray_tls_material' not in xhttp_block\n    assert '"security": "none"' in xhttp_block\n    assert 'XRAY_TLS_DIR = Path("/usr/local/etc/xray/tls")' in source\n'''
assert body.count(old) == 1
path_tls.write_text(body.replace(old, new, 1), encoding="utf-8", newline="\n")

path_backup = ROOT / "tests" / "test_sg_gateway_02206_full_backup_verify_unlimited.py"
body = path_backup.read_text(encoding="utf-8")
old = '    assert manifest["build"] == "DEV-02206-FULL-BACKUP-VERIFY-UNLIMITED-R1"\n'
assert body.count(old) == 1
path_backup.write_text(body.replace(old, "", 1), encoding="utf-8", newline="\n")

for changed in (path_02110, path_xmux, path_tls, path_backup):
    compile(changed.read_text(encoding="utf-8"), str(changed), "exec")
