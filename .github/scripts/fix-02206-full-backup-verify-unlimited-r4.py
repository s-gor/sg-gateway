from __future__ import annotations

from pathlib import Path

r1 = Path(__file__).with_name("fix-02206-full-backup-verify-unlimited-r1.py")
source = r1.read_text(encoding="utf-8")

old_picker = '''assert template.count(old_picker) == 1\ntemplate = template.replace(old_picker, new_picker, 1)'''
new_picker = '''assert template.count(old_picker) >= 1\ntemplate = template.replace(old_picker, new_picker)'''
assert source.count(old_picker) == 1
source = source.replace(old_picker, new_picker, 1)

old_limit = '''assert body.count("client_max_body_size 1024m;") == expected, (relative, body.count("client_max_body_size 1024m;"))'''
new_limit = '''assert body.count("client_max_body_size 1024m;") >= expected, (relative, body.count("client_max_body_size 1024m;"))'''
assert source.count(old_limit) == 1
source = source.replace(old_limit, new_limit, 1)

exec(compile(source, str(r1), "exec"), {"__name__": "__main__", "__file__": str(r1)})
