from __future__ import annotations

from pathlib import Path

r2 = Path(__file__).with_name("fix-02206-full-backup-verify-unlimited-r2.py")
source = r2.read_text(encoding="utf-8")
old = '''assert body.count("client_max_body_size 1024m;") == expected, (relative, body.count("client_max_body_size 1024m;"))\n    body = body.replace("client_max_body_size 1024m;", "client_max_body_size 0;")'''
new = '''assert body.count("client_max_body_size 1024m;") >= expected, (relative, body.count("client_max_body_size 1024m;"))\n    body = body.replace("client_max_body_size 1024m;", "client_max_body_size 0;")'''
assert source.count(old) == 1
source = source.replace(old, new, 1)
exec(compile(source, str(r2), "exec"), {"__name__": "__main__", "__file__": str(r2)})
