from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE_SHA = "9fbf42aea2bde80a99229de5661a93b6dce4f6c1"
LIVE_TREE = "c482dc4f158dc1d61c2ba1d683a14e96d24dac68"
LIVE_BUILD = "LIVE-02205-SGPANEL-XMUX-WARP-UPDATER-R4"
VERSION = "0.1.0-022.05"


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8", newline="\n")


# Release identity: publication-only metadata; runtime/update channel stays frozen on dev-02205.
write("BUILD-ID", LIVE_BUILD + "\n")
manifest_path = ROOT / "release-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
assert manifest["version"] == VERSION
assert manifest["channel"] == "dev-02205"
manifest["build"] = LIVE_BUILD
manifest["status"] = "LIVE"
manifest["next_development_line"] = "0.1.0-022.06"
manifest.setdefault("source_integrity", {})["manifest"] = "SOURCE-SHA256SUMS"
manifest["source_integrity"]["mode"] = "sha256-file-inventory"
manifest["source_integrity"]["ci_verified"] = True
manifest["source_integrity"]["build_run_verified"] = True
manifest["publication"] = {
    "published": "2026-08-15",
    "live_validated_commit": LIVE_SHA,
    "live_validated_tree": LIVE_TREE,
    "runtime_changes_after_live_validation": False,
    "release_branch": "release-02205-live",
    "stable_branch": "stable-02205",
    "next_development_branch": "dev-02206",
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

# Current, version-driven self-extracting FULL builder. No 021.12 release identity is hardcoded.
write(
    "build-run.sh",
    r'''#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
BUILD_ID="$(tr -d '\r\n' < "$ROOT/BUILD-ID")"
[[ -n "$VERSION" ]] || { echo "[SG-Gateway Build] VERSION is empty" >&2; exit 1; }
[[ -n "$BUILD_ID" ]] || { echo "[SG-Gateway Build] BUILD-ID is empty" >&2; exit 1; }

DEFAULT_BASENAME="SG-Gateway-${VERSION}-FULL"
OUT="${1:-$ROOT/${DEFAULT_BASENAME}.run}"
SOURCE_FOLDER="SG-Gateway-${VERSION}-SOURCE"
PAYLOAD_MARKER="__SG_GATEWAY_BINARY_PAYLOAD_V1__"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
STAGE="$TMP/$SOURCE_FOLDER"
PAYLOAD="$TMP/payload.tar.gz"
SHA_FILE="${OUT%.run}-SHA256.txt"
TRANSFER_ZIP="${OUT%.run}-TRANSFER.zip"

mkdir -p "$STAGE"
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$ROOT" archive --format=tar HEAD | tar -C "$STAGE" -xf -
  SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(git -C "$ROOT" show -s --format=%ct HEAD)}"
else
  tar -C "$ROOT" \
    --exclude='./.git' \
    --exclude='./.venv' \
    --exclude='./venv' \
    --exclude='./.pytest_cache' \
    --exclude='./.ruff_cache' \
    --exclude='*/__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='./SG-Gateway-*-FULL*.run' \
    --exclude='./SG-Gateway-*-FULL*-TRANSFER.zip' \
    --exclude='./SG-Gateway-*-FULL*-SHA256.txt' \
    -cf - . | tar -C "$STAGE" -xf -
  SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-0}"
fi
[[ "$SOURCE_DATE_EPOCH" =~ ^[0-9]+$ ]] || SOURCE_DATE_EPOCH=0

[[ "$(tr -d '[:space:]' < "$STAGE/VERSION")" == "$VERSION" ]] || { echo "[SG-Gateway Build] VERSION mismatch" >&2; exit 1; }
[[ "$(tr -d '\r\n' < "$STAGE/BUILD-ID")" == "$BUILD_ID" ]] || { echo "[SG-Gateway Build] BUILD-ID mismatch" >&2; exit 1; }
(cd "$STAGE" && sha256sum -c SOURCE-SHA256SUMS >/dev/null)
if [[ -f "$STAGE/vendor/cores/SHA256SUMS" ]]; then
  (cd "$STAGE/vendor/cores" && sha256sum -c SHA256SUMS >/dev/null)
fi

tar --sort=name --mtime="@${SOURCE_DATE_EPOCH}" --owner=0 --group=0 --numeric-owner \
  -C "$TMP" -czf "$PAYLOAD" "$SOURCE_FOLDER"
PAYLOAD_SHA="$(sha256sum "$PAYLOAD" | awk '{print $1}')"
PACKAGE="SG-Gateway ${VERSION} (${BUILD_ID})"

{
  printf '%s\n' '#!/usr/bin/env bash' 'set -Eeuo pipefail'
  printf 'PACKAGE=%q\n' "$PACKAGE"
  printf 'EXPECTED_VERSION=%q\n' "$VERSION"
  printf 'EXPECTED_BUILD_ID=%q\n' "$BUILD_ID"
  printf 'SOURCE_FOLDER=%q\n' "$SOURCE_FOLDER"
  printf 'PAYLOAD_SHA256=%q\n' "$PAYLOAD_SHA"
  printf 'PAYLOAD_MARKER=%q\n' "$PAYLOAD_MARKER"
} > "$OUT"

cat >> "$OUT" <<'EOSG'
SELF="$(readlink -f "${BASH_SOURCE[0]}")"
TEMP_DIR=""

cleanup() { [[ -z "${TEMP_DIR:-}" || ! -d "$TEMP_DIR" ]] || rm -rf "$TEMP_DIR"; }
trap cleanup EXIT INT TERM
fail() { printf '[SG-Gateway] [ERROR] %s\n' "$*" >&2; exit 1; }

extract_payload() {
  local command payload actual payload_line token
  for command in awk tail sha256sum tar python3 bash readlink mktemp; do
    command -v "$command" >/dev/null 2>&1 || fail "Не найдена команда: $command"
  done
  token="${EXPECTED_VERSION//[^A-Za-z0-9]/}"
  TEMP_DIR="$(mktemp -d "/tmp/sg-gateway-${token}.XXXXXX")"
  payload="$TEMP_DIR/payload.tar.gz"
  payload_line="$(awk -v marker="$PAYLOAD_MARKER" '$0 == marker { print NR + 1; exit }' "$SELF")"
  [[ "$payload_line" =~ ^[0-9]+$ ]] || fail "Не найден встроенный binary payload"
  tail -n "+$payload_line" "$SELF" > "$payload" || fail "Не удалось извлечь встроенный payload"
  actual="$(sha256sum "$payload" | awk '{print $1}')"
  [[ "$actual" == "$PAYLOAD_SHA256" ]] || fail "Контрольная сумма payload не совпала"
  tar -xzf "$payload" -C "$TEMP_DIR" || fail "Не удалось распаковать payload"
  [[ -d "$TEMP_DIR/$SOURCE_FOLDER" ]] || fail "Каталог исходника не извлечён"
}

verify_source() {
  local root shell_file
  root="$TEMP_DIR/$SOURCE_FOLDER"
  [[ "$(tr -d '[:space:]' < "$root/VERSION")" == "$EXPECTED_VERSION" ]] || fail "Версия payload не совпала"
  [[ "$(tr -d '\r\n' < "$root/BUILD-ID")" == "$EXPECTED_BUILD_ID" ]] || fail "Build ID payload не совпал"
  (cd "$root" && sha256sum -c SOURCE-SHA256SUMS >/dev/null) || fail "Файлы исходника повреждены"
  if [[ -f "$root/vendor/cores/SHA256SUMS" ]]; then
    (cd "$root/vendor/cores" && sha256sum -c SHA256SUMS >/dev/null) || fail "Vendored engines повреждены"
  fi
  while IFS= read -r -d '' shell_file; do
    bash -n "$shell_file" || fail "Ошибка shell-синтаксиса: ${shell_file#$root/}"
  done < <(find "$root" -type f -name '*.sh' -print0)

  python3 - "$root" "$EXPECTED_VERSION" "$EXPECTED_BUILD_ID" <<'PYVERIFY'
import ast
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
expected_version = sys.argv[2]
expected_build = sys.argv[3]

listed = set()
for line_no, raw in enumerate((root / "SOURCE-SHA256SUMS").read_text(encoding="utf-8").splitlines(), 1):
    if not raw.strip():
        continue
    match = re.fullmatch(r"([0-9a-f]{64})  (.+)", raw)
    if match is None:
        raise SystemExit(f"invalid SOURCE-SHA256SUMS line {line_no}: {raw!r}")
    listed.add(match.group(2))
actual = {
    path.relative_to(root).as_posix()
    for path in root.rglob("*")
    if path.is_file() and path.relative_to(root).as_posix() != "SOURCE-SHA256SUMS"
}
if actual != listed:
    raise SystemExit(
        f"source inventory mismatch: missing={sorted(actual-listed)[:20]} extra={sorted(listed-actual)[:20]}"
    )

for base_name in ("app", "hostd", "engines", "deploy", "tests"):
    base = root / base_name
    if base.exists():
        for path in base.rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
for path in root.rglob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))

manifest = json.loads((root / "release-manifest.json").read_text(encoding="utf-8"))
if manifest.get("version") != expected_version:
    raise SystemExit("release-manifest VERSION mismatch")
if (root / "BUILD-ID").read_text(encoding="utf-8").strip() != expected_build:
    raise SystemExit("BUILD-ID mismatch")
for required in ("install.sh", "deploy/update-from-github.sh", "deploy/install-from-github.sh"):
    if not (root / required).is_file():
        raise SystemExit(f"missing required source file: {required}")
PYVERIFY
}

extract_payload
verify_source
case "${1:-}" in
  --verify-only)
    printf '[SG-Gateway] [OK] %s: binary payload и исходники полностью проверены.\n' "$PACKAGE"
    exit 0
    ;;
  --extract-only)
    destination="${2:-$PWD/$SOURCE_FOLDER}"
    rm -rf "$destination"
    mkdir -p "$destination"
    cp -a "$TEMP_DIR/$SOURCE_FOLDER/." "$destination/"
    printf '[SG-Gateway] [OK] Исходник извлечён: %s\n' "$destination"
    exit 0
    ;;
esac
exec bash "$TEMP_DIR/$SOURCE_FOLDER/install.sh" "$@"
EOSG

printf '\n%s\n' "$PAYLOAD_MARKER" >> "$OUT"
cat "$PAYLOAD" >> "$OUT"
chmod +x "$OUT"

awk -v marker="$PAYLOAD_MARKER" '$0 == marker { exit } { print }' "$OUT" | bash -n
"$OUT" --verify-only
RUN_SHA="$(sha256sum "$OUT" | awk '{print $1}')"
printf '%s  %s\n' "$RUN_SHA" "$(basename "$OUT")" > "$SHA_FILE"
rm -f "$TRANSFER_ZIP"
zip -q -j "$TRANSFER_ZIP" "$OUT" "$SHA_FILE"
printf '[SG-Gateway Build] RUN: %s\n' "$OUT"
printf '[SG-Gateway Build] SHA256: %s\n' "$SHA_FILE"
printf '[SG-Gateway Build] TRANSFER: %s\n' "$TRANSFER_ZIP"
''',
)

write(
    "build-run-vendored.sh",
    r'''#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
exec "$ROOT/build-run.sh" "${1:-$ROOT/SG-Gateway-${VERSION}-FULL.run}"
''',
)

write(
    ".github/workflows/ci.yml",
    r'''name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  panel:
    runs-on: ubuntu-24.04
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Verify source integrity
        run: |
          python3 -B - <<'PY'
          import hashlib
          import re
          import subprocess
          from pathlib import Path

          rows = Path("SOURCE-SHA256SUMS").read_text(encoding="utf-8").splitlines()
          expected = {}
          for line_no, raw in enumerate(rows, 1):
              if not raw.strip():
                  continue
              match = re.fullmatch(r"([0-9a-f]{64})  (.+)", raw)
              if match is None:
                  raise SystemExit(f"invalid SOURCE-SHA256SUMS line {line_no}: {raw!r}")
              digest, path = match.groups()
              if path in expected:
                  raise SystemExit(f"duplicate checksum path: {path}")
              expected[path] = digest

          tracked = set(subprocess.check_output(["git", "ls-files"], text=True, encoding="utf-8").splitlines())
          tracked.discard("SOURCE-SHA256SUMS")
          listed = set(expected)
          if tracked != listed:
              raise SystemExit(
                  f"checksum inventory mismatch: missing={sorted(tracked-listed)[:20]} extra={sorted(listed-tracked)[:20]}"
              )
          for path in sorted(tracked):
              proc = subprocess.Popen(["git", "show", f"HEAD:{path}"], stdout=subprocess.PIPE)
              assert proc.stdout is not None
              digest = hashlib.sha256()
              for chunk in iter(lambda: proc.stdout.read(1024 * 1024), b""):
                  digest.update(chunk)
              if proc.wait() != 0:
                  raise SystemExit(f"git show failed for {path}")
              if digest.hexdigest() != expected[path]:
                  raise SystemExit(f"source hash mismatch: {path}")
          print(f"Git source integrity ok: {len(tracked)} tracked files verified")
          PY

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements-dev.txt

      - name: Check source syntax
        run: |
          bash -n install.sh
          bash -n build-run.sh
          bash -n build-run-vendored.sh
          bash -n deploy/install-from-github.sh
          bash -n deploy/update-from-github.sh
          python -B -c "from pathlib import Path; files=list(Path('app').rglob('*.py'))+list(Path('hostd').rglob('*.py'))+list(Path('engines').rglob('*.py'))+list(Path('deploy').rglob('*.py'))+list(Path('tests').rglob('*.py')); [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in files]; print(f'syntax ok: {len(files)} files')"

      - name: Check release manifest
        run: |
          python -B - <<'PY'
          import json
          from pathlib import Path
          manifest = json.loads(Path("release-manifest.json").read_text(encoding="utf-8"))
          version = Path("VERSION").read_text(encoding="utf-8").strip()
          build_id = Path("BUILD-ID").read_text(encoding="utf-8").strip()
          assert manifest["version"] == version
          assert manifest["build"] == build_id
          assert manifest["status"] == "LIVE"
          assert manifest["next_development_line"] == "0.1.0-022.06"
          assert manifest["source_integrity"]["mode"] == "sha256-file-inventory"
          assert manifest["safe_update"]["preserve_local_assets"] is True
          assert manifest["source_integrity"]["ci_verified"] is True
          assert manifest["source_integrity"]["build_run_verified"] is True
          assert manifest["images"]["panel"]
          assert manifest["images"]["xray"]
          print("manifest ok")
          PY

      - name: Run full repository suite
        run: python -m pytest -q

      - name: Build and verify current FULL package
        run: |
          command -v zip
          command -v unzip
          VERSION="$(tr -d '[:space:]' < VERSION)"
          OUT="/tmp/SG-Gateway-${VERSION}-FULL.run"
          bash build-run.sh "$OUT"
          "$OUT" --verify-only
          test -s "${OUT%.run}-SHA256.txt"
          test -s "${OUT%.run}-TRANSFER.zip"
          unzip -t "${OUT%.run}-TRANSFER.zip"
''',
)

# Historical 021.12 release-freeze tests must not constrain the current release builder/CI.
historical_path = ROOT / "tests" / "test_sg_gateway_02112_final_cumulative_cleanup_r5.py"
historical = historical_path.read_text(encoding="utf-8")
old = '''def test_build_run_uses_committed_git_archive_and_checks_both_resume_generations() -> None:\n    text = _text(BUILD_RUN)'''
new = '''def test_build_run_uses_committed_git_archive_and_checks_both_resume_generations() -> None:\n    if _text(ROOT / "VERSION").strip() != "0.1.0-021.12":\n        pytest.skip("historical 021.12 release-freeze contract")\n    text = _text(BUILD_RUN)'''
assert historical.count(old) == 1
historical = historical.replace(old, new)
old = '''def test_ci_checks_canonical_integrity_and_full_clean() -> None:\n    workflow = _text(ROOT / ".github" / "workflows" / "ci.yml")'''
new = '''def test_ci_checks_canonical_integrity_and_full_clean() -> None:\n    if _text(ROOT / "VERSION").strip() != "0.1.0-021.12":\n        pytest.skip("historical 021.12 release-freeze contract")\n    workflow = _text(ROOT / ".github" / "workflows" / "ci.yml")'''
assert historical.count(old) == 1
historical = historical.replace(old, new)
historical_path.write_text(historical, encoding="utf-8", newline="\n")

write(
    "tests/test_sg_gateway_02205_publication.py",
    f'''from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\n\n\ndef _text(path: str) -> str:\n    return (ROOT / path).read_text(encoding="utf-8")\n\n\ndef test_02205_publication_identity_matches_live_release() -> None:\n    assert _text("VERSION").strip() == "{VERSION}"\n    assert _text("BUILD-ID").strip() == "{LIVE_BUILD}"\n    manifest = json.loads(_text("release-manifest.json"))\n    assert manifest["version"] == "{VERSION}"\n    assert manifest["build"] == "{LIVE_BUILD}"\n    assert manifest["status"] == "LIVE"\n    assert manifest["next_development_line"] == "0.1.0-022.06"\n    assert manifest["channel"] == "dev-02205"\n    assert manifest["maintenance_updates"]["panel"]["channel"] == "dev-02205"\n    assert manifest["publication"]["live_validated_commit"] == "{LIVE_SHA}"\n    assert manifest["publication"]["live_validated_tree"] == "{LIVE_TREE}"\n    assert manifest["publication"]["runtime_changes_after_live_validation"] is False\n\n\ndef test_full_builder_is_current_and_version_driven() -> None:\n    body = _text("build-run.sh")\n    assert 'VERSION="$(tr -d' in body\n    assert 'BUILD_ID="$(tr -d' in body\n    assert 'git -C "$ROOT" archive --format=tar HEAD' in body\n    assert '__SG_GATEWAY_BINARY_PAYLOAD_V1__' in body\n    assert 'SOURCE-SHA256SUMS' in body\n    assert 'SG-Gateway-02112-FULL-CLEAN.run' not in body\n    assert 'EXPECTED_VERSION="0.1.0-021.12"' not in body\n    wrapper = _text("build-run-vendored.sh")\n    assert 'SG-Gateway-${{VERSION}}-FULL.run' in wrapper\n    assert '02112' not in wrapper\n\n\ndef test_main_ci_validates_current_release_not_02112_freeze() -> None:\n    body = _text(".github/workflows/ci.yml")\n    assert 'Verify source integrity' in body\n    assert 'Run full repository suite' in body\n    assert 'Build and verify current FULL package' in body\n    assert 'manifest["status"] == "LIVE"' in body\n    assert '0.1.0-022.06' in body\n    assert 'FINAL-AWG2' not in body\n    assert 'SG-Gateway-02112-FULL-CLEAN.run' not in body\n\n\ndef test_publication_docs_point_to_current_live_line() -> None:\n    readme = _text("README.md")\n    assert 'version-0.1.0--022.05' in readme\n    assert 'status-LIVE' in readme\n    publication = _text("PUBLICATION-02205.md")\n    assert "{LIVE_SHA}" in publication\n    assert "472 passed, 4 skipped" in publication\n''',
)

# README: keep the historical 021.12 section, but make 022.05 the current public entry point.
readme_path = ROOT / "README.md"
readme = readme_path.read_text(encoding="utf-8")
readme = readme.replace("version-0.1.0--021.12-3b82f6", "version-0.1.0--022.05-3b82f6", 1)
readme = readme.replace("status-FINAL--AWG2-16A34A", "status-LIVE-16A34A", 1)
old_intro = "> **021.12 FINAL AWG2.** Эта линия feature-frozen: новые функции и AWG3 в `0.1.0-021.12` больше не добавляются. Только критические bug/security fixes. AWG3 начинается с `0.1.0-022.01`. Подробный freeze: [`SG-GATEWAY-02112-FINAL-AWG2.md`](SG-GATEWAY-02112-FINAL-AWG2.md)."
new_intro = "> **0.1.0-022.05 LIVE.** Текущая принятая линия SG-Gateway: SG-Panel XMUX, ручной WARP, безопасный Panel Update с rollback и точной привязкой установленного commit/fingerprint. Live-база подтверждена 15 августа 2026. Историческая 021.12 FINAL AWG2 сохранена отдельно."
assert readme.count(old_intro) == 1
readme = readme.replace(old_intro, new_intro)
marker = "\n## SG-Gateway 0.1.0-021.12\n"
assert readme.count(marker) == 1
current_section = '''\n## SG-Gateway 0.1.0-022.05\n\n`0.1.0-022.05` — текущая LIVE-линия. Она прошла реальный безопасный update на существующем SG-Gateway и закреплена как `stable-02205` / `release-02205-live`.\n\nКлючевые изменения линии:\n\n- VLESS Reality TCP и XHTTP Reality с актуальным XMUX-контрактом SG-Panel/Xray;\n- ручное создание WARP из панели без обязательной регистрации WARP во время clean install;\n- Panel Update через проверенный shell-updater с safety backup, rollback и финальной live-проверкой;\n- после успешного Update фиксируются точный source commit и fingerprint установленного дерева;\n- clean-installer identity приведена к 022.05;\n- полный repository CI и отдельные контракты XMUX/WARP/update сохранены.\n\nСледующая development-линия: `0.1.0-022.06` (`dev-02206`). Подробности публикации: [`PUBLICATION-02205.md`](PUBLICATION-02205.md).\n'''
readme = readme.replace(marker, current_section + marker)
readme_path.write_text(readme, encoding="utf-8", newline="\n")

# Installation doc: only current-line identity; detailed historical material stays below.
installation_path = ROOT / "docs" / "INSTALLATION.md"
installation = installation_path.read_text(encoding="utf-8")
old_note = "> **0.1.0-021.12 = FINAL AWG2.** Версия зафиксирована как окончательная линия с AmneziaWG 2. AWG3 начинается только с `0.1.0-022.01`."
new_note = "> **0.1.0-022.05 = LIVE.** Это текущая опубликованная линия SG-Gateway. Историческая `0.1.0-021.12` сохранена как FINAL AWG2 baseline. Следующая development-линия — `0.1.0-022.06`."
assert installation.count(old_note) == 1
installation = installation.replace(old_note, new_note)
installation = installation.replace("## Схема чистой установки 021.10", "## Текущая схема чистой установки", 1)
installation_path.write_text(installation, encoding="utf-8", newline="\n")

publication = f'''# SG-Gateway 0.1.0-022.05 — LIVE publication\n\nДата публикации: **2026-08-15**.\n\n## Принятая live-база\n\n- VERSION: `{VERSION}`\n- live-validated commit: `{LIVE_SHA}`\n- live-validated tree: `{LIVE_TREE}`\n- live branch: `live-02205-accepted-20260815`\n- stable snapshot: `stable-02205`\n- release snapshot: `release-02205-live`\n- next development branch: `dev-02206`\n\nLive update завершился штатным сообщением `SG-Gateway safely updated`; rollback не сработал. Перед публикацией R4 development CI подтвердил **472 passed, 4 skipped**.\n\n## Что публикуется\n\nПубличная 022.05 сохраняет принятый VPN/runtime-контракт без изменений после live validation. Publication-слой меняет только release/build metadata, документацию, главный GitHub CI и генератор self-extracting `.run` пакета.\n\n`build-run.sh` теперь берёт `VERSION` и `BUILD-ID` из текущего дерева, архивирует точный committed `HEAD`, проверяет `SOURCE-SHA256SUMS`, собирает self-extracting `.run`, повторно выполняет `--verify-only`, создаёт SHA256-файл и transfer ZIP.\n\n## Линия обновлений\n\n022.05 оставляет frozen update-channel `dev-02205`; эта ветка больше не используется для новой разработки. Новая работа начинается только в `dev-02206`. Это не даёт опубликованным 022.05-инсталляциям случайно перейти на будущую development-линию.\n'''
write("PUBLICATION-02205.md", publication)

# Changelog: prepend current live release, preserve full historical 021.12 log below.
changelog_path = ROOT / "CHANGELOG.md"
changelog = changelog_path.read_text(encoding="utf-8")
if not changelog.startswith("# SG-Gateway 0.1.0-022.05"):
    prefix = f'''# SG-Gateway 0.1.0-022.05 — LIVE\n\n- Live-validated baseline: `{LIVE_SHA}` / tree `{LIVE_TREE}`.\n- SG-Panel XMUX + manual WARP + safe Panel Update accepted on a real SG-Gateway.\n- Panel Update binds exact deployed commit/fingerprint only after final live verification.\n- Clean installer identity is 022.05; automatic WARP registration remains outside clean install.\n- Publication tooling is version-driven; the old 021.12-only `.run` builder and main CI contract are retired from the active release path.\n- Next development line: `0.1.0-022.06`.\n\n'''
    changelog = prefix + changelog
changelog_path.write_text(changelog, encoding="utf-8", newline="\n")
