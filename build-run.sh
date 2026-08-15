#!/usr/bin/env bash
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
