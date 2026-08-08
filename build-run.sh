#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$ROOT/SG-Gateway-02110-FULL-CLEAN-SAFETY-FIX2.run}"
SOURCE_FOLDER="SG-Gateway-02110-SOURCE"
EXPECTED_VERSION="0.1.0-021.10"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
STAGE="$TMP/$SOURCE_FOLDER"
PAYLOAD="$TMP/payload.tar.gz"
SHA_FILE="${OUT%.run}-SHA256.txt"
TRANSFER_ZIP="${OUT%.run}-TRANSFER.zip"

mkdir -p "$STAGE"
tar -C "$ROOT" \
  --exclude='./.git' \
  --exclude='./.venv' \
  --exclude='./venv' \
  --exclude='./.pytest_cache' \
  --exclude='./.ruff_cache' \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='./SG-Gateway-02110-FULL-CLEAN-*.run' \
  --exclude='./SG-Gateway-02110-FULL-CLEAN-*-TRANSFER.zip' \
  --exclude='./SG-Gateway-02110-FULL-CLEAN-*-SHA256.txt' \
  -cf - . | tar -C "$STAGE" -xf -

tar --sort=name --mtime='UTC 2026-08-06' --owner=0 --group=0 --numeric-owner \
  -C "$TMP" -czf "$PAYLOAD" "$SOURCE_FOLDER"
PAYLOAD_SHA="$(sha256sum "$PAYLOAD" | awk '{print $1}')"

cat > "$OUT" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail

PACKAGE="SG-Gateway 0.1.0-021.10 Full Clean Safety Fix 2"
EXPECTED_VERSION="$EXPECTED_VERSION"
SOURCE_FOLDER="$SOURCE_FOLDER"
PAYLOAD_SHA256="$PAYLOAD_SHA"
PAYLOAD_MARKER="__SG_GATEWAY_02110_BINARY_PAYLOAD_BELOW__"
SELF="\$(readlink -f "\${BASH_SOURCE[0]}")"
TEMP_DIR=""

cleanup() { [[ -z "\${TEMP_DIR:-}" || ! -d "\$TEMP_DIR" ]] || rm -rf "\$TEMP_DIR"; }
trap cleanup EXIT INT TERM
fail() { printf '[SG-Gateway] [ERROR] %s\\n' "\$*" >&2; exit 1; }

extract_payload() {
  local command payload actual payload_line
  for command in awk tail sha256sum tar python3 bash readlink mktemp; do
    command -v "\$command" >/dev/null 2>&1 || fail "Не найдена команда: \$command"
  done
  TEMP_DIR="\$(mktemp -d /tmp/sg-gateway-02110.XXXXXX)"
  payload="\$TEMP_DIR/payload.tar.gz"
  payload_line="\$(awk -v marker="\$PAYLOAD_MARKER" '\$0 == marker { print NR + 1; exit }' "\$SELF")"
  [[ "\$payload_line" =~ ^[0-9]+\$ ]] || fail "Не найден встроенный binary payload"
  tail -n "+\$payload_line" "\$SELF" > "\$payload" || fail "Не удалось извлечь встроенный payload"
  actual="\$(sha256sum "\$payload" | awk '{print \$1}')"
  [[ "\$actual" == "\$PAYLOAD_SHA256" ]] || fail "Контрольная сумма payload не совпала"
  tar -xzf "\$payload" -C "\$TEMP_DIR" || fail "Не удалось распаковать payload"
  [[ -d "\$TEMP_DIR/\$SOURCE_FOLDER" ]] || fail "Каталог исходника не извлечён"
}

verify_source() {
  local root shell_file
  root="\$TEMP_DIR/\$SOURCE_FOLDER"
  [[ "\$(tr -d '[:space:]' < "\$root/VERSION")" == "\$EXPECTED_VERSION" ]] || fail "Версия payload не совпала"
  (cd "\$root" && sha256sum -c SOURCE-SHA256SUMS >/dev/null) || fail "Файлы исходника повреждены"
  (cd "\$root/vendor/cores" && sha256sum -c SHA256SUMS >/dev/null) || fail "Vendored engines повреждены"
  while IFS= read -r -d '' shell_file; do
    bash -n "\$shell_file" || fail "Ошибка shell-синтаксиса: \${shell_file#\$root/}"
  done < <(find "\$root" -type f -name '*.sh' -print0)
  [[ "\$(sha256sum "\$root/assets/placeholder/index.html" | awk '{print \$1}')" == "06b280bab43d9ed4ceeb75d34008b60158366a968e6eb950b3e0b4b0cbcdd226" ]] || fail "Заглушка не совпала с принятой"
  grep -Fq 'SG_GATEWAY_02110_HTTPS_VERIFY_RETRY_FIX1' "\$root/deploy/configure-panel-access.sh" || fail "Нет HTTPS retry"
  grep -Fq '/root/sg-gateway-02110-installer-resume.env' "\$root/deploy/full-uninstall-ubuntu.sh" || fail "Uninstall не очищает resume 02110"
  grep -Fq 'include\\s+/etc/nginx/stream-conf\\.d/sg-gateway-443\\.conf' "\$root/deploy/full-uninstall-ubuntu.sh" || fail "Uninstall не очищает direct stream include"
  grep -Fq 'SG_DEVICE_COLLAPSE_V4_LAST_CSS' "\$root/app/web/templates/base.html" || fail "Нет финального Device Collapse V4"
  grep -Fq 'System alignment final fix 3 — Disk is the reference' "\$root/app/web/static/sg-system-simple-dials-v1.css" || fail "Нет финального System FIX3"
  grep -Fq 'Скопировать ссылку' "\$root/app/web/templates/client_detail.html" || fail "Нет принятой кнопки подписки"
  grep -Fq 'SG_GATEWAY_02110_INSTALLER_SAFETY_FIX2' "\$root/install.sh" || fail "Нет installer safety fix 2"
  grep -Fq 'SG_GATEWAY_02110_UNINSTALL_SAFETY_FIX2' "\$root/deploy/full-uninstall-ubuntu.sh" || fail "Нет uninstall safety fix 2"
  ! grep -Eq 'nginx -T[^\n]*\|[^\n]*grep[^\n]*-[A-Za-z]*q' "\$root/install.sh" || fail "Остался опасный nginx -T | grep -q"
  ! grep -Eq 'ss -lntp[^\n]*\|[^\n]*grep[^\n]*-[A-Za-z]*q' "\$root/install.sh" || fail "Остался опасный ss | grep -q"
  python3 - "\$root" <<'PYVERIFY'
import ast, json, sys
from pathlib import Path
root=Path(sys.argv[1])
for base in (root/'app',root/'hostd',root/'engines'):
    if base.exists():
        for path in base.rglob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
for path in root.rglob('*.json'):
    json.loads(path.read_text(encoding='utf-8'))
exports=(root/'app/clients/exports.py').read_text(encoding='utf-8')
expected='decoded = "' + chr(92) + 'n".join(links)'
rejected='decoded = "' + (chr(92) * 2) + 'n".join(links)'
assert expected in exports, expected
assert rejected not in exports, rejected
PYVERIFY
}

extract_payload
verify_source
case "\${1:-}" in
  --verify-only)
    printf '[SG-Gateway] [OK] %s: binary payload и исходники полностью проверены.\\n' "\$PACKAGE"
    exit 0
    ;;
  --extract-only)
    destination="\${2:-\$PWD/SG-Gateway-02110-SOURCE}"
    rm -rf "\$destination"; mkdir -p "\$destination"
    cp -a "\$TEMP_DIR/\$SOURCE_FOLDER/." "\$destination/"
    printf '[SG-Gateway] [OK] Исходник извлечён: %s\\n' "\$destination"
    exit 0
    ;;
esac
exec bash "\$TEMP_DIR/\$SOURCE_FOLDER/install.sh" "\$@"
exit 1

__SG_GATEWAY_02110_BINARY_PAYLOAD_BELOW__
EOF
cat "$PAYLOAD" >> "$OUT"
chmod +x "$OUT"

# Check the text header separately; the rest of the file is intentionally binary.
awk '/^__SG_GATEWAY_02110_BINARY_PAYLOAD_BELOW__$/ { exit } { print }' "$OUT" | bash -n
"$OUT" --verify-only
RUN_SHA="$(sha256sum "$OUT" | awk '{print $1}')"
printf '%s  %s\n' "$RUN_SHA" "$(basename "$OUT")" > "$SHA_FILE"
rm -f "$TRANSFER_ZIP"
(
  cd "$(dirname "$OUT")"
  zip -q -9 "$(basename "$TRANSFER_ZIP")" "$(basename "$OUT")" "$(basename "$SHA_FILE")"
)

# Verify the exact transfer artifact after extraction.
VERIFY_DIR="$TMP/transfer-check"
mkdir -p "$VERIFY_DIR"
unzip -q "$TRANSFER_ZIP" -d "$VERIFY_DIR"
(
  cd "$VERIFY_DIR"
  sha256sum -c "$(basename "$SHA_FILE")"
  bash "$(basename "$OUT")" --verify-only
)
printf '%s\n' "$OUT"
printf '%s\n' "$TRANSFER_ZIP"
