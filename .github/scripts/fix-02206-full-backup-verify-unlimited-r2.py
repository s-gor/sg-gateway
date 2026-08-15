from __future__ import annotations

from pathlib import Path

path = Path(__file__).with_name("fix-02206-full-backup-verify-unlimited-r1.py")
source = path.read_text(encoding="utf-8")
old = '''assert template.count(old_picker) == 1\ntemplate = template.replace(old_picker, new_picker, 1)'''
new = '''assert template.count(old_picker) >= 1\ntemplate = template.replace(old_picker, new_picker)'''
assert source.count(old) == 1
source = source.replace(old, new, 1)
exec(compile(source, str(path), "exec"), {"__name__": "__main__", "__file__": str(path)})
