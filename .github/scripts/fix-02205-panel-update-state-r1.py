from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
updater_path = ROOT / "deploy" / "update-from-github.sh"
body = updater_path.read_text(encoding="utf-8")

old_globals = 'SOURCE_DIR=""\nBACKUP_READY=0'
new_globals = 'SOURCE_DIR=""\nSOURCE_COMMIT=""\nPANEL_UPDATE_STATE="${SG_GATEWAY_PANEL_UPDATE_STATE:-$DATA_DIR/updates/panel-state.json}"\nBACKUP_READY=0'
assert body.count(old_globals) == 1, body.count(old_globals)
body = body.replace(old_globals, new_globals)

marker = "\nprepare_source_archive() {\n"
assert body.count(marker) == 1, body.count(marker)
helper = r'''
resolve_source_commit() {
  local resolved=""

  if command -v git >/dev/null 2>&1; then
    resolved="$(git ls-remote --exit-code "$GIT_URL" "refs/heads/$BRANCH" 2>/dev/null | awk 'NR==1 {print $1}' || true)"
  fi

  if [[ ! "$resolved" =~ ^[0-9a-f]{40}$ ]]; then
    resolved="$(
      curl -4 -fsSL --max-time 20 -A 'SG-Gateway-Updater' \
        "https://api.github.com/repos/${REPOSITORY}/commits/${BRANCH}" 2>/dev/null \
      | python3 -c 'import json,re,sys; value=str(json.load(sys.stdin).get("sha") or "").strip().lower(); print(value if re.fullmatch(r"[0-9a-f]{40}", value) else "")' \
        2>/dev/null || true
    )"
  fi

  if [[ ! "$resolved" =~ ^[0-9a-f]{40}$ ]]; then
    resolved="$(
      curl -4 -fsSL --max-time 20 -A 'SG-Gateway-Updater' \
        "https://github.com/${REPOSITORY}/commits/${BRANCH}.atom" 2>/dev/null \
      | python3 -c 'import re,sys; match=re.search(r"Grit::Commit/([0-9a-fA-F]{40})", sys.stdin.read()); print(match.group(1).lower() if match else "")' \
        2>/dev/null || true
    )"
  fi

  [[ "$resolved" =~ ^[0-9a-f]{40}$ ]] || fail "cannot resolve exact GitHub commit for update channel $BRANCH"
  SOURCE_COMMIT="$resolved"
}
'''
body = body.replace(marker, "\n" + helper + marker.lstrip("\n"))

old_archive = r'''prepare_source_archive() {
  local archive="$TEMP_DIR/sg-gateway-main.tar.gz"
  rm -rf "$SOURCE_DIR"
  mkdir -p "$SOURCE_DIR"

  printf '[SG-Gateway Update] Source mode: COMPATIBILITY (full GitHub archive)\n'
  curl -fL --retry 6 --retry-all-errors --retry-delay 3 --connect-timeout 20 \
    "$ARCHIVE_URL" -o "$archive"
  gzip -t "$archive"
  tar -xzf "$archive" -C "$SOURCE_DIR" --strip-components=1
}
'''
new_archive = r'''prepare_source_archive() {
  local archive archive_url
  resolve_source_commit
  archive="$TEMP_DIR/sg-gateway-${SOURCE_COMMIT}.tar.gz"
  archive_url="https://github.com/${REPOSITORY}/archive/${SOURCE_COMMIT}.tar.gz"
  rm -rf "$SOURCE_DIR"
  mkdir -p "$SOURCE_DIR"

  printf '[SG-Gateway Update] Source mode: COMPATIBILITY (commit-pinned GitHub archive)\n'
  printf '[SG-Gateway Update] Source commit: %s\n' "$SOURCE_COMMIT"
  curl -fL --retry 6 --retry-all-errors --retry-delay 3 --connect-timeout 20 \
    "$archive_url" -o "$archive"
  gzip -t "$archive"
  tar -xzf "$archive" -C "$SOURCE_DIR" --strip-components=1
}
'''
assert body.count(old_archive) == 1, body.count(old_archive)
body = body.replace(old_archive, new_archive)

old_clone = r'''    "$GIT_URL" "$SOURCE_DIR" || return 1

  # SG_GATEWAY_02112_LIGHT_UPDATE_FIX9_R2
'''
new_clone = r'''    "$GIT_URL" "$SOURCE_DIR" || return 1

  SOURCE_COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD 2>/dev/null || true)"
  [[ "$SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || return 1
  printf '[SG-Gateway Update] Source commit: %s\n' "$SOURCE_COMMIT"

  # SG_GATEWAY_02112_LIGHT_UPDATE_FIX9_R2
'''
assert body.count(old_clone) == 1, body.count(old_clone)
body = body.replace(old_clone, new_clone)

main_marker = "\nmain() {\n"
assert body.count(main_marker) == 1, body.count(main_marker)
bind_state = r'''
bind_panel_update_state() {
  [[ "$SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]] || fail "source commit is unavailable after deployment"

  local new_version
  new_version="$(tr -d '\r\n' < "$PREFIX/VERSION")"
  install -d -m 0750 -o root -g sg-gateway "$(dirname "$PANEL_UPDATE_STATE")"

  PYTHONPATH="$PREFIX:$PREFIX/hostd" \
  SG_GATEWAY_APP_ROOT="$PREFIX" \
  SG_GATEWAY_PANEL_UPDATE_STATE="$PANEL_UPDATE_STATE" \
  "$PREFIX/.venv/bin/python" -B - \
    "$SOURCE_COMMIT" "$new_version" "$BACKUP_DIR" "$BRANCH" <<'PYPANELSTATE'
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.maintenance.panel_updates import source_fingerprint

commit = sys.argv[1].strip().lower()
version = sys.argv[2].strip()
backup = Path(sys.argv[3]).name
channel = sys.argv[4].strip()
root = Path(os.environ["SG_GATEWAY_APP_ROOT"])
state_path = Path(os.environ["SG_GATEWAY_PANEL_UPDATE_STATE"])

if not re.fullmatch(r"[0-9a-f]{40}", commit):
    raise SystemExit("invalid source commit")

fingerprint = source_fingerprint(root)
if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
    raise SystemExit("invalid deployed source fingerprint")

payload = {
    "commit": commit,
    "version": version,
    "channel": channel,
    "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "backup": backup,
    "source_fingerprint": fingerprint,
}
state_path.parent.mkdir(parents=True, exist_ok=True)
temporary = state_path.with_name(state_path.name + ".new")
temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.chmod(temporary, 0o640)
shutil.chown(temporary, user="root", group="sg-gateway")
os.replace(temporary, state_path)
print(f"Panel Update baseline: {commit[:12]} ({channel})")
PYPANELSTATE

  runuser -u sg-gateway -- test -r "$PANEL_UPDATE_STATE"
}
'''
body = body.replace(main_marker, "\n" + bind_state + main_marker.lstrip("\n"))

old_main = '  run_stage 6 "Проверка HTTPS, Clients, Nginx и runtime" verify_final\n\n  UPDATE_FINISHED=1'
new_main = '  run_stage 6 "Проверка HTTPS, Clients, Nginx и runtime" verify_final\n  bind_panel_update_state\n\n  UPDATE_FINISHED=1'
assert body.count(old_main) == 1, body.count(old_main)
body = body.replace(old_main, new_main)

updater_path.write_text(body, encoding="utf-8", newline="\n")

test_path = ROOT / "tests" / "test_sg_gateway_02205_panel_update_state_binding.py"
test_path.write_text(
    '''from pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nUPDATER = ROOT / "deploy" / "update-from-github.sh"\n\n\ndef _block(body: str, name: str, next_name: str) -> str:\n    start = body.index(f"{name}() {{")\n    end = body.index(f"\\n{next_name}() {{", start)\n    return body[start:end]\n\n\ndef test_update_source_is_bound_to_exact_commit_in_both_source_modes() -> None:\n    body = UPDATER.read_text(encoding="utf-8")\n    light = _block(body, "prepare_source_light", "prepare_source")\n    archive = _block(body, "prepare_source_archive", "prepare_source_light")\n    resolver = _block(body, "resolve_source_commit", "prepare_source_archive")\n\n    assert 'SOURCE_COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD' in light\n    assert '[[ "$SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]]' in light\n    assert 'archive_url="https://github.com/${REPOSITORY}/archive/${SOURCE_COMMIT}.tar.gz"' in archive\n    assert '"$archive_url" -o "$archive"' in archive\n    assert 'refs/heads/$BRANCH' in resolver\n    assert 'commits/${BRANCH}.atom' in resolver\n    assert 'SOURCE_COMMIT="$resolved"' in resolver\n\n\ndef test_successful_update_atomically_binds_panel_state_to_live_tree() -> None:\n    body = UPDATER.read_text(encoding="utf-8")\n    bind = _block(body, "bind_panel_update_state", "main")\n\n    assert 'SG_GATEWAY_PANEL_UPDATE_STATE="$PANEL_UPDATE_STATE"' in bind\n    assert 'from app.maintenance.panel_updates import source_fingerprint' in bind\n    assert 'fingerprint = source_fingerprint(root)' in bind\n    assert '"commit": commit' in bind\n    assert '"channel": channel' in bind\n    assert '"source_fingerprint": fingerprint' in bind\n    assert 'temporary.write_text' in bind\n    assert 'os.chmod(temporary, 0o640)' in bind\n    assert 'shutil.chown(temporary, user="root", group="sg-gateway")' in bind\n    assert 'os.replace(temporary, state_path)' in bind\n    assert 'runuser -u sg-gateway -- test -r "$PANEL_UPDATE_STATE"' in bind\n\n\ndef test_state_binding_happens_only_after_final_live_verification_and_before_success() -> None:\n    body = UPDATER.read_text(encoding="utf-8")\n    main = body[body.index("main() {"):]\n    verify = main.index('run_stage 6 "Проверка HTTPS, Clients, Nginx и runtime" verify_final')\n    bind = main.index("bind_panel_update_state", verify)\n    finished = main.index("UPDATE_FINISHED=1", bind)\n    assert verify < bind < finished\n\n\ndef test_built_in_panel_update_still_delegates_to_verified_shell_updater() -> None:\n    runtime = (ROOT / "hostd" / "sg_hostd" / "panel_update_runtime.py").read_text(encoding="utf-8")\n    update = runtime[runtime.index("def update_panel() -> dict[str, Any]:"):]\n    assert 'deploy" / "update-from-github.sh"' in update\n    assert 'env["SG_GATEWAY_GITHUB_BRANCH"] = GITHUB_BRANCH' in update\n''',
    encoding="utf-8",
    newline="\n",
)
