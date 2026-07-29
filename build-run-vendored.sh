#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$ROOT/SG-Gateway-021-FULL-CLEAN-EC2-REBUILT-FINAL.run}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PAYLOAD="$TMP/payload.tar.gz"
CHECK_DIR="$TMP/check"

# Build from the PHYSICAL working tree, not from git-tracked files.
# This deliberately includes uncommitted vendor/cores.
tar \
  --exclude='./.git' \
  --exclude='./.venv' \
  --exclude='./venv' \
  --exclude='./__pycache__' \
  --exclude='./.pytest_cache' \
  --exclude='./*.pyc' \
  --exclude='./*.pyo' \
  --exclude='./SG-Gateway-*.run' \
  -C "$ROOT" \
  -czf "$PAYLOAD" \
  .

PAYLOAD_SHA="$(sha256sum "$PAYLOAD" | awk '{print $1}')"

{
  echo '#!/usr/bin/env bash'
  echo 'set -Eeuo pipefail'
  printf 'PAYLOAD_SHA256=%q\n' "$PAYLOAD_SHA"
  cat <<'WRAPPER'
SELF="$(readlink -f "${BASH_SOURCE[0]}")"
TMPDIR_RUN="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_RUN"' EXIT

PAYLOAD_FILE="$TMPDIR_RUN/payload.tar.gz"
SOURCE_DIR="$TMPDIR_RUN/source"

payload_line="$(awk '/^__SG_GATEWAY_021_PAYLOAD__$/{print NR+1; exit}' "$SELF")"
if [[ -z "$payload_line" ]]; then
    echo "[SG-Gateway] Ошибка: payload marker не найден." >&2
    exit 1
fi

tail -n +"$payload_line" "$SELF" > "$PAYLOAD_FILE"

actual_sha="$(sha256sum "$PAYLOAD_FILE" | awk '{print $1}')"
if [[ "$actual_sha" != "$PAYLOAD_SHA256" ]]; then
    echo "[SG-Gateway] Ошибка: payload повреждён." >&2
    exit 1
fi

mkdir -p "$SOURCE_DIR"
tar -xzf "$PAYLOAD_FILE" -C "$SOURCE_DIR"

if [[ ! -s "$SOURCE_DIR/vendor/cores/Xray-linux-64.zip" ]]; then
    echo "[SG-Gateway] Ошибка: Xray-linux-64.zip отсутствует внутри installer payload." >&2
    exit 1
fi

if [[ ! -s "$SOURCE_DIR/vendor/cores/SHA256SUMS" ]]; then
    echo "[SG-Gateway] Ошибка: vendor/cores/SHA256SUMS отсутствует внутри installer payload." >&2
    exit 1
fi

(
    cd "$SOURCE_DIR/vendor/cores"
    sha256sum -c SHA256SUMS >/dev/null
)

case "${1:-}" in
    --verify-only)
        echo "[SG-Gateway] OK: payload и 6 vendored cores встроены и целы."
        exit 0
        ;;
    --extract-only)
        target="${2:-}"
        if [[ -z "$target" ]]; then
            echo "Usage: $0 --extract-only TARGET_DIR" >&2
            exit 2
        fi
        mkdir -p "$target"
        cp -a "$SOURCE_DIR"/. "$target"/
        echo "$target"
        exit 0
        ;;
esac

chmod +x "$SOURCE_DIR/install.sh"
cd "$SOURCE_DIR"
exec bash ./install.sh "$@"

exit 0
__SG_GATEWAY_021_PAYLOAD__
WRAPPER
} > "$OUT"

cat "$PAYLOAD" >> "$OUT"
chmod +x "$OUT"

# One silent post-build check: prove that the FINAL .run contains the real core file.
mkdir -p "$CHECK_DIR"
"$OUT" --extract-only "$CHECK_DIR" >/dev/null
test -s "$CHECK_DIR/vendor/cores/Xray-linux-64.zip"
test -s "$CHECK_DIR/vendor/cores/mihomo-linux-amd64-v1.19.29.gz"
test -s "$CHECK_DIR/vendor/cores/sing-box-1.13.14-linux-amd64.tar.gz"
test -s "$CHECK_DIR/vendor/cores/wgcf-cli-linux-64.tar.zstd"
test -s "$CHECK_DIR/vendor/cores/amneziawg-tools-1.0.20260618-2.tar.gz"
test -s "$CHECK_DIR/vendor/cores/amneziawg-linux-kernel-module-1.0.20260329-2.tar.gz"

printf '%s\n' "$OUT"
