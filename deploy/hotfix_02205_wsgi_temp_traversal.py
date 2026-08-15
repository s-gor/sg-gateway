from pathlib import Path

updater = Path("deploy/update-from-github.sh")
body = updater.read_text(encoding="utf-8")
old = '''  validation_root="$TEMP_DIR/wsgi-validation"\n  rm -rf "$validation_root"\n  install -d -m 0750 -o sg-gateway -g sg-gateway \\\n    "$validation_root" "$validation_root/data" "$validation_root/log"\n'''
new = '''  validation_root="$TEMP_DIR/wsgi-validation"\n  rm -rf "$validation_root"\n  # TEMP_DIR is created root:root 0700 by mktemp. The deployed WSGI import\n  # runs as sg-gateway, so allow traversal only for the duration of this\n  # isolated validation. Directory listing remains denied.\n  chmod 0711 "$TEMP_DIR"\n  install -d -m 0750 -o sg-gateway -g sg-gateway \\\n    "$validation_root" "$validation_root/data" "$validation_root/log"\n'''
if body.count(old) != 1:
    raise SystemExit(f"expected one validation-root anchor, found {body.count(old)}")
body = body.replace(old, new, 1)
old_tail = '''print(f"Panel WSGI import: OK ({target}) with isolated data/log")\nPYDEPLOYEDWSGI\n}\n'''
new_tail = '''print(f"Panel WSGI import: OK ({target}) with isolated data/log")\nPYDEPLOYEDWSGI\n  chmod 0700 "$TEMP_DIR"\n}\n'''
if body.count(old_tail) != 1:
    raise SystemExit(f"expected one WSGI validation tail, found {body.count(old_tail)}")
body = body.replace(old_tail, new_tail, 1)
updater.write_text(body, encoding="utf-8", newline="\n")

test = Path("tests/test_sg_gateway_02205_update_wsgi_isolation.py")
t = test.read_text(encoding="utf-8")
anchor = '''    assert "Panel WSGI import: OK" in block\n'''
insert = '''    assert "Panel WSGI import: OK" in block\n    assert 'chmod 0711 "$TEMP_DIR"' in block\n    assert 'chmod 0700 "$TEMP_DIR"' in block\n    assert block.index('chmod 0711 "$TEMP_DIR"') < block.index('runuser -u sg-gateway')\n    assert block.index('chmod 0700 "$TEMP_DIR"') > block.index('PYDEPLOYEDWSGI')\n'''
if t.count(anchor) != 1:
    raise SystemExit(f"expected one test anchor, found {t.count(anchor)}")
t = t.replace(anchor, insert, 1)
test.write_text(t, encoding="utf-8", newline="\n")
print("[PASS] exact WSGI TEMP_DIR traversal hotfix applied")
