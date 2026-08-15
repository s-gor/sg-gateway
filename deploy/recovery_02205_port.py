from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"[PASS] {label}")


def patch_optional_warp() -> None:
    path = ROOT / "install.sh"

    old_stage10 = """stage10_start_and_verify() {
  stage9_start_hostd
  stage9_verify_hostd
  stage9_apply_runtime
  stage9_ensure_warp
  stage9_start_panel
  stage9_verify_nginx
  verify_client_identities_after_update
}
"""
    new_stage10 = """stage10_start_and_verify() {
  stage9_start_hostd
  stage9_verify_hostd
  stage9_apply_runtime
  stage9_start_panel
  stage9_verify_nginx
  verify_client_identities_after_update
}
"""
    replace_once(path, old_stage10, new_stage10, "remove automatic WARP from 10/10 final stage")

    old_hidden = """  run_hidden "Этап 9/9 · 1/5 · Запуск sg-hostd" stage9_start_hostd
  run_hidden "Этап 9/9 · 2/5 · Проверка команд hostd" stage9_verify_hostd
  run_hidden "Этап 9/9 · 3/6 · Сохранение/применение Xray runtime" stage9_apply_runtime
  run_hidden "Этап 9/9 · 4/6 · Создание и активация WARP" stage9_ensure_warp
  run_hidden "Этап 9/9 · 5/6 · Запуск панели" stage9_start_panel
  run_hidden "Этап 9/9 · 6/6 · Проверка Nginx и служб" stage9_verify_nginx
"""
    new_hidden = """  run_hidden "Этап 9/9 · 1/5 · Запуск sg-hostd" stage9_start_hostd
  run_hidden "Этап 9/9 · 2/5 · Проверка команд hostd" stage9_verify_hostd
  run_hidden "Этап 9/9 · 3/5 · Сохранение/применение Xray runtime" stage9_apply_runtime
  run_hidden "Этап 9/9 · 4/5 · Запуск панели" stage9_start_panel
  run_hidden "Этап 9/9 · 5/5 · Проверка Nginx и служб" stage9_verify_nginx
"""
    replace_once(path, old_hidden, new_hidden, "remove automatic WARP from 9/9 final stage")

    old_status = "  print_sg_admin_status\n  printf '[SG-Gateway] WARP:         создан и активен\\n'\n"
    new_status = """  print_sg_admin_status
  if [[ -s "$DATA_DIR/warp/wgcf.xray.json" || -s "$DATA_DIR/warp/wgcf-profile.conf" ]]; then
    printf '[SG-Gateway] WARP:         существующий профиль сохранён\\n'
  else
    printf '[SG-Gateway] WARP:         helper установлен; создаётся при необходимости в Outbounds\\n'
  fi
"""
    replace_once(path, old_status, new_status, "report optional WARP without auto registration")


def patch_updater_wsgi() -> None:
    path = ROOT / "deploy" / "update-from-github.sh"
    body = path.read_text(encoding="utf-8")
    marker = "# SG_GATEWAY_02205_WSGI_ISOLATED_VALIDATION_V1"
    if marker in body:
        raise SystemExit("updater WSGI isolation marker already present")

    preflight_anchor = "preflight() {\n"
    if body.count(preflight_anchor) != 1:
        raise SystemExit(f"updater preflight anchor count={body.count(preflight_anchor)}")

    block = r'''# SG_GATEWAY_02205_WSGI_ISOLATED_VALIDATION_V1
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
  "$PREFIX/.venv/bin/python" -B - "$source" "$module" "$target" <<'PYCANDIDATEWSGI'
import sys
from pathlib import Path

root = Path(sys.argv[1])
module = sys.argv[2]
target = sys.argv[3]
module_path = root.joinpath(*module.split("."))
present = module_path.with_suffix(".py").is_file() or (module_path / "__init__.py").is_file()
if not present:
    raise SystemExit(
        f"candidate source does not provide installed panel WSGI target {target}"
    )
print(f"Candidate WSGI target: {target} -> module present")
PYCANDIDATEWSGI
}

validate_deployed_panel() {
  runuser -u sg-gateway -- "$PREFIX/.venv/bin/python" -B -c \
    'from pathlib import Path; from jinja2 import Environment; env=Environment(); [env.parse(p.read_text(encoding="utf-8")) for p in Path("/opt/sg-gateway/app/web/templates").rglob("*.html")]; print("Templates: OK")'

  local target validation_root
  target="$(panel_wsgi_target)"
  validation_root="$TEMP_DIR/wsgi-validation"
  rm -rf "$validation_root"
  install -d -m 0750 -o sg-gateway -g sg-gateway \
    "$validation_root" "$validation_root/data" "$validation_root/log"

  runuser -u sg-gateway -- "$PREFIX/.venv/bin/python" -B - \
    "$PREFIX" "$CONFIG_DIR/sg-gateway.env" "$target" "$validation_root" <<'PYDEPLOYEDWSGI'
import importlib
import os
import shlex
import sys
from pathlib import Path

prefix = Path(sys.argv[1])
env_file = Path(sys.argv[2])
target = sys.argv[3]
validation_root = Path(sys.argv[4])

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

# The import can execute app.main -> init_db(). Keep it away from production.
os.environ["SG_GATEWAY_DATA_DIR"] = str(validation_root / "data")
os.environ["SG_GATEWAY_LOG_DIR"] = str(validation_root / "log")

os.chdir(prefix)
sys.path.insert(0, str(prefix))
module_name, object_name = target.split(":", 1)
module = importlib.import_module(module_name)
getattr(module, object_name)
print(f"Panel WSGI import: OK ({target}) with isolated data/log")
PYDEPLOYEDWSGI
}

'''
    body = body.replace(preflight_anchor, block + preflight_anchor, 1)

    prepare_anchor = 'print("Python syntax: OK")\nPYCHECK\n\n}\n'
    prepare_new = 'print("Python syntax: OK")\nPYCHECK\n\n  validate_candidate_wsgi_target "$SOURCE_DIR"\n}\n'
    if body.count(prepare_anchor) != 1:
        raise SystemExit(f"prepare_source validation anchor count={body.count(prepare_anchor)}")
    body = body.replace(prepare_anchor, prepare_new, 1)

    old_stage4 = """  run_stage 4 "Python/UI проверка без изменения runtime" \\
    runuser -u sg-gateway -- "$PREFIX/.venv/bin/python" -B -c \\
      'from pathlib import Path; from jinja2 import Environment; env=Environment(); [env.parse(p.read_text(encoding="utf-8")) for p in Path("/opt/sg-gateway/app/web/templates").rglob("*.html")]; print("Templates: OK")'
"""
    new_stage4 = '  run_stage 4 "Python/UI проверка без изменения runtime" validate_deployed_panel\n'
    if body.count(old_stage4) != 1:
        raise SystemExit(f"stage4 validation anchor count={body.count(old_stage4)}")
    body = body.replace(old_stage4, new_stage4, 1)

    path.write_text(body, encoding="utf-8", newline="\n")
    print("[PASS] updater WSGI validation is path-only before backup and isolated after deploy")


def main() -> None:
    patch_optional_warp()
    patch_updater_wsgi()


if __name__ == "__main__":
    main()
