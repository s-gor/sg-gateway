from __future__ import annotations

from pathlib import Path

path = Path(__file__).with_name("apply-02206-sgpanel-vless-parity-r1.py")
source = path.read_text(encoding="utf-8")
old = '    assert "location /sg-xhttp-tls/ {" in snippet\n'
new = '    assert "location /sg-xhttp-tls/ {{" in snippet\n'
assert source.count(old) == 1
source = source.replace(old, new, 1)
code = compile(source, str(path), "exec")
exec(code, {"__name__": "__main__", "__file__": str(path)})
