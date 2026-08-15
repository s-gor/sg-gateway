from __future__ import annotations

import re
from pathlib import Path

path = Path(__file__).with_name("apply-02206-sgpanel-vless-parity-r1.py")
source = path.read_text(encoding="utf-8")
old = '    assert "location /sg-xhttp-tls/ {" in snippet\n'
new = '    assert "location /sg-xhttp-tls/ {{" in snippet\n'
assert source.count(old) == 1
source = source.replace(old, new, 1)
code = compile(source, str(path), "exec")
exec(code, {"__name__": "__main__", "__file__": str(path)})

# Correct only regression fixtures/expectations after the candidate generator.
test_path = Path(__file__).resolve().parents[2] / "tests" / "test_sg_gateway_02206_sgpanel_vless_parity.py"
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
