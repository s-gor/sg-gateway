from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
updater_path = ROOT / "deploy/update-from-github.sh"
updater = updater_path.read_text(encoding="utf-8")

helper_marker = "# SG_GATEWAY_02113_WSGI_COMPAT_FIX"
if helper_marker not in updater:
    helper = r'''
# SG_GATEWAY_02113_WSGI_COMPAT_FIX
panel_wsgi_target() {
  local raw
  raw="$(systemctl show -p ExecStart --value "$PANEL_SERVICE" 2>/dev/null || true)"
  python3 - "$raw" <<'PYWSGITARGET'
import re
import sys

raw = sys.argv[1]
items = re.findall(
    r"(?<![A-Za-z0-9_.])([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*)(?![A-Za-z0-9_])",
    raw,
)
print(items[-1] if items else "app.main:app")
PYWSGITARGET
}

validate_candidate_wsgi_target() {
  local source="$1" target module
  target="$(panel_wsgi_target)"
  module="${target%%:*}"
  PYTHONPATH="$source" "$PREFIX/.venv/bin/python" -B - "$source" "$module" "$target" <<'PYCANDIDATEWSGI'
import importlib.util
import sys
from pathlib import Path

root = Path(sys.argv[1])
module = sys.argv[2]
target = sys.argv[3]
sys.path.insert(0, str(root))
if importlib.util.find_spec(module) is None:
    raise SystemExit(
        f"candidate source does not provide installed panel WSGI target {target}"
    )
print(f"Candidate WSGI target: {target} -> module present")
PYCANDIDATEWSGI
}

validate_deployed_panel() {
  runuser -u sg-gateway -- "$PREFIX/.venv/bin/python" -B -c \
    'from pathlib import Path; from jinja2 import Environment; env=Environment(); [env.parse(p.read_text(encoding="utf-8")) for p in Path("/opt/sg-gateway/app/web/templates").rglob("*.html")]; print("Templates: OK")'

  local target
  target="$(panel_wsgi_target)"
  runuser -u sg-gateway -- "$PREFIX/.venv/bin/python" -B - "$PREFIX" "$CONFIG_DIR/sg-gateway.env" "$target" <<'PYDEPLOYEDWSGI'
import importlib
import os
import shlex
import sys
from pathlib import Path

prefix = Path(sys.argv[1])
env_file = Path(sys.argv[2])
target = sys.argv[3]

for raw in env_file.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    name, value = line.split("=", 1)
    name = name.strip()
    value = value.strip()
    if value[:1] in {'"', "'"}:
        try:
            parsed = shlex.split(value, posix=True)
            value = parsed[0] if parsed else ""
        except ValueError:
            value = value[1:-1] if len(value) >= 2 else ""
    os.environ[name] = value

os.chdir(prefix)
sys.path.insert(0, str(prefix))
module_name, object_name = target.split(":", 1)
module = importlib.import_module(module_name)
getattr(module, object_name)
print(f"Panel WSGI import: OK ({target})")
PYDEPLOYEDWSGI
}

'''
    updater = updater.replace("preflight() {", helper + "preflight() {", 1)

syntax_tail = '''print("Python syntax: OK")
PYCHECK

}
'''
if 'validate_candidate_wsgi_target "$SOURCE_DIR"' not in updater:
    if syntax_tail not in updater:
        raise SystemExit("prepare_source syntax tail not found")
    updater = updater.replace(
        syntax_tail,
        '''print("Python syntax: OK")
PYCHECK

  validate_candidate_wsgi_target "$SOURCE_DIR"
}
''',
        1,
    )

if "validate_deployed_panel() {" not in updater:
    raise SystemExit("validate_deployed_panel helper insertion failed")

stage4_pattern = re.compile(
    r'''  run_stage 4 "Python/UI проверка без изменения runtime" \\\n    runuser -u sg-gateway -- "\$PREFIX/\.venv/bin/python" -B -c \\\n      'from pathlib import Path; from jinja2 import Environment; env=Environment\(\); \[env\.parse\(p\.read_text\(encoding="utf-8"\)\) for p in Path\("/opt/sg-gateway/app/web/templates"\)\.rglob\("\*\.html"\)\]; print\("Templates: OK"\)'\n'''
)
if 'run_stage 4 "Python/UI проверка без изменения runtime" validate_deployed_panel' not in updater:
    updater, count = stage4_pattern.subn(
        '  run_stage 4 "Python/UI проверка без изменения runtime" validate_deployed_panel\n',
        updater,
        count=1,
    )
    if count != 1:
        raise SystemExit(f"stage 4 replacement count={count}")

updater_path.write_text(updater, encoding="utf-8")

production = ROOT / "app/production.py"
production.write_text(
    '''"""Compatibility WSGI entrypoint for existing SG-Gateway installations.\n\nSome installed 021 systemd units still launch ``app.production:app``.\nPanel-only updates intentionally preserve those units, so this module must stay\navailable while the canonical entrypoint remains ``app.main:app``.\n"""\n\nfrom app.main import app, create_app\n\napplication = app\n\n__all__ = ["app", "application", "create_app"]\n''',
    encoding="utf-8",
)

test_path = ROOT / "tests/test_sg_gateway_02113_update_wsgi_compat.py"
test_path.write_text(
    '''from __future__ import annotations\n\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\n\n\ndef test_legacy_production_wsgi_entrypoint_is_kept_for_existing_units() -> None:\n    body = (ROOT / "app/production.py").read_text(encoding="utf-8")\n    assert "from app.main import app, create_app" in body\n    assert "application = app" in body\n\n\ndef test_panel_only_updater_checks_installed_wsgi_target_before_mutation() -> None:\n    body = (ROOT / "deploy/update-from-github.sh").read_text(encoding="utf-8")\n    assert "panel_wsgi_target()" in body\n    assert "validate_candidate_wsgi_target()" in body\n    assert 'validate_candidate_wsgi_target "$SOURCE_DIR"' in body\n    assert body.index('validate_candidate_wsgi_target "$SOURCE_DIR"') < body.index(\n        'run_stage 2 "Safety Backup: SG state + full /etc/letsencrypt"'\n    )\n\n\ndef test_panel_only_updater_imports_effective_wsgi_target_before_restart() -> None:\n    body = (ROOT / "deploy/update-from-github.sh").read_text(encoding="utf-8")\n    assert "validate_deployed_panel()" in body\n    assert "Panel WSGI import: OK" in body\n    assert 'run_stage 4 "Python/UI проверка без изменения runtime" validate_deployed_panel' in body\n    assert body.index('run_stage 4 "Python/UI проверка без изменения runtime" validate_deployed_panel') < body.index(\n        'run_stage 5 "Перезапуск только panel + hostd"'\n    )\n''',
    encoding="utf-8",
)
