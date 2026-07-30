#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PARENT="$(dirname "$ROOT")"
SOURCE_NAME="SG-Gateway-021-SOURCE"
OUT="${1:-$PARENT/SG-Gateway-021-FULL-CLEAN-EC2-REBUILT.run}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

STAGE="$TMP/$SOURCE_NAME"
mkdir -p "$STAGE"
tar -C "$ROOT" \
  --exclude='./.git' \
  --exclude='./.venv' \
  --exclude='./venv' \
  --exclude='*/__pycache__' \
  --exclude='./.pytest_cache' \
  --exclude='./.ruff_cache' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='*.run' \
  --exclude='*.zip' \
  --exclude='*.patch' \
  -cf - . | tar -C "$STAGE" -xf -

tar --sort=name --mtime='UTC 2026-07-25' --owner=0 --group=0 --numeric-owner \
  -C "$TMP" -czf "$TMP/payload.tar.gz" "$SOURCE_NAME"
PAYLOAD_SHA="$(sha256sum "$TMP/payload.tar.gz" | awk '{print $1}')"
INSTALL_SHA="$(sha256sum "$STAGE/install.sh" | awk '{print $1}')"
WARP_SHA="$(sha256sum "$STAGE/app/routing/warp.py" | awk '{print $1}')"
WARP_HELPER_SHA="$(sha256sum "$STAGE/app/routing/warp_helper.py" | awk '{print $1}')"
WGCF_INSTALL_SHA="$(sha256sum "$STAGE/deploy/install-wgcf-cli.sh" | awk '{print $1}')"
OUTBOUNDS_SHA="$(sha256sum "$STAGE/app/web/templates/outbounds.html" | awk '{print $1}')"
CLIENTS_SHA="$(sha256sum "$STAGE/app/web/templates/clients.html" | awk '{print $1}')"
DETAIL_SHA="$(sha256sum "$STAGE/app/web/templates/client_detail.html" | awk '{print $1}')"
BASE_SHA="$(sha256sum "$STAGE/app/web/templates/base.html" | awk '{print $1}')"
LOGIN_SHA="$(sha256sum "$STAGE/app/web/templates/login.html" | awk '{print $1}')"
RECOVERY_SHA="$(sha256sum "$STAGE/app/web/templates/recovery.html" | awk '{print $1}')"
TYPOGRAPHY_SHA="$(sha256sum "$STAGE/app/web/static/sg-readable-typography-v3.css" | awk '{print $1}')"
CONSTANTS_SHA="$(sha256sum "$STAGE/app/constants.py" | awk '{print $1}')"
REQUIREMENTS_SHA="$(sha256sum "$STAGE/SG-GATEWAY-021-REQUIREMENTS.json" | awk '{print $1}')"

cat > "$OUT" <<EOF2
#!/usr/bin/env bash
set -Eeuo pipefail
PACKAGE="SG-Gateway 021 Full Clean EC2 Rebuilt"
SOURCE_FOLDER="$SOURCE_NAME"
PAYLOAD_BEGIN="__SG_GATEWAY_021_REBUILT_PAYLOAD_BEGIN__"
PAYLOAD_END="__SG_GATEWAY_021_REBUILT_PAYLOAD_END__"
PAYLOAD_SHA256="$PAYLOAD_SHA"
EXPECTED_INSTALL_SHA256="$INSTALL_SHA"
EXPECTED_WARP_SHA256="$WARP_SHA"
EXPECTED_WARP_HELPER_SHA256="$WARP_HELPER_SHA"
EXPECTED_WGCF_INSTALL_SHA256="$WGCF_INSTALL_SHA"
EXPECTED_OUTBOUNDS_SHA256="$OUTBOUNDS_SHA"
EXPECTED_CLIENTS_SHA256="$CLIENTS_SHA"
EXPECTED_DETAIL_SHA256="$DETAIL_SHA"
EXPECTED_BASE_SHA256="$BASE_SHA"
EXPECTED_LOGIN_SHA256="$LOGIN_SHA"
EXPECTED_RECOVERY_SHA256="$RECOVERY_SHA"
EXPECTED_TYPOGRAPHY_SHA256="$TYPOGRAPHY_SHA"
EXPECTED_CONSTANTS_SHA256="$CONSTANTS_SHA"
EXPECTED_REQUIREMENTS_SHA256="$REQUIREMENTS_SHA"
TEMP_DIR=""
cleanup(){ [[ -z "\${TEMP_DIR:-}" || ! -d "\$TEMP_DIR" ]] || rm -rf "\$TEMP_DIR"; }
trap cleanup EXIT
fail(){ printf '[%s] ERROR: %s\n' "\$PACKAGE" "\$*" >&2; exit 1; }
extract_payload(){
  TEMP_DIR="\$(mktemp -d /tmp/sg-gateway-021-rebuilt.XXXXXX)"
  awk -v begin="\$PAYLOAD_BEGIN" -v end="\$PAYLOAD_END" '
    \$0 == begin {inside=1; next}
    \$0 == end {inside=0; exit}
    inside {print}
  ' "\$0" | base64 -d > "\$TEMP_DIR/payload.tar.gz" || fail "embedded payload decode failed"
  [[ "\$(sha256sum "\$TEMP_DIR/payload.tar.gz" | awk '{print \$1}')" == "\$PAYLOAD_SHA256" ]] || fail "embedded payload checksum mismatch"
  tar -xzf "\$TEMP_DIR/payload.tar.gz" -C "\$TEMP_DIR"
  [[ -d "\$TEMP_DIR/\$SOURCE_FOLDER" ]] || fail "source folder missing after extraction"
}
verify_source(){
  local root="\$TEMP_DIR/\$SOURCE_FOLDER"
  [[ "\$(cat "\$root/VERSION")" == "0.1.0-021.7" ]] || fail "version mismatch"
  [[ "\$(sha256sum "\$root/install.sh" | awk '{print \$1}')" == "\$EXPECTED_INSTALL_SHA256" ]] || fail "install.sh mismatch"
  [[ "\$(sha256sum "\$root/app/routing/warp.py" | awk '{print \$1}')" == "\$EXPECTED_WARP_SHA256" ]] || fail "WARP core mismatch"
  [[ "\$(sha256sum "\$root/app/routing/warp_helper.py" | awk '{print \$1}')" == "\$EXPECTED_WARP_HELPER_SHA256" ]] || fail "WARP helper mismatch"
  [[ "\$(sha256sum "\$root/deploy/install-wgcf-cli.sh" | awk '{print \$1}')" == "\$EXPECTED_WGCF_INSTALL_SHA256" ]] || fail "wgcf installer mismatch"
  [[ "\$(sha256sum "\$root/app/web/templates/outbounds.html" | awk '{print \$1}')" == "\$EXPECTED_OUTBOUNDS_SHA256" ]] || fail "Outbounds UI mismatch"
  [[ "\$(sha256sum "\$root/app/web/templates/clients.html" | awk '{print \$1}')" == "\$EXPECTED_CLIENTS_SHA256" ]] || fail "Clients UI mismatch"
  [[ "\$(sha256sum "\$root/app/web/templates/client_detail.html" | awk '{print \$1}')" == "\$EXPECTED_DETAIL_SHA256" ]] || fail "Client detail mismatch"
  [[ "\$(sha256sum "\$root/app/web/templates/base.html" | awk '{print \$1}')" == "\$EXPECTED_BASE_SHA256" ]] || fail "base template mismatch"
  [[ "\$(sha256sum "\$root/app/web/templates/login.html" | awk '{print \$1}')" == "\$EXPECTED_LOGIN_SHA256" ]] || fail "login template mismatch"
  [[ "\$(sha256sum "\$root/app/web/templates/recovery.html" | awk '{print \$1}')" == "\$EXPECTED_RECOVERY_SHA256" ]] || fail "recovery template mismatch"
  [[ "\$(sha256sum "\$root/app/web/static/sg-readable-typography-v3.css" | awk '{print \$1}')" == "\$EXPECTED_TYPOGRAPHY_SHA256" ]] || fail "readable typography mismatch"
  [[ "\$(sha256sum "\$root/app/constants.py" | awk '{print \$1}')" == "\$EXPECTED_CONSTANTS_SHA256" ]] || fail "product constants mismatch"
  [[ "\$(sha256sum "\$root/SG-GATEWAY-021-REQUIREMENTS.json" | awk '{print \$1}')" == "\$EXPECTED_REQUIREMENTS_SHA256" ]] || fail "requirements manifest mismatch"
  bash -n "\$root/install.sh" || fail "install.sh syntax check failed"
  bash -n "\$root/deploy/install-wgcf-cli.sh" || fail "wgcf helper syntax check failed"
  grep -Fq 'DEFAULT_AWG_PORT="585"' "\$root/install.sh" || fail "AmneziaWG UDP 585 installer contract missing"
  grep -Fq 'AMNEZIAWG_UDP_PORT = 585' "\$root/app/constants.py" || fail "AmneziaWG UDP 585 Python contract missing"
  grep -Fq '"port": AMNEZIAWG_UDP_PORT' "\$root/app/db.py" || fail "AmneziaWG database default is not 585"
  grep -Fq 'awg_port = AMNEZIAWG_UDP_PORT' "\$root/app/install_seed.py" || fail "AmneziaWG seed does not force 585"
  grep -Fq 'min="585" max="585"' "\$root/app/web/templates/connections.html" || fail "AmneziaWG UI does not show fixed 585"
  grep -Fq 'AmneziaWG invariant: UDP {AMNEZIAWG_UDP_PORT}' "\$root/install.sh" || fail "AmneziaWG clean database assertion missing"
  grep -Fq 'AmneziaWG runtime does not listen on UDP 585' "\$root/install.sh" || fail "AmneziaWG runtime assertion missing"
  ! grep -Fq 'read_tty "UDP-порт AmneziaWG"' "\$root/install.sh" || fail "AmneziaWG port prompt must not exist"
  grep -Fq 'stage9_ensure_warp' "\$root/install.sh" || fail "automatic WARP stage missing"
  grep -Fq '/commands/warp.install' "\$root/install.sh" || fail "automatic WARP command missing"
  ! grep -Fq 'Ссылки первого клиента' "\$root/install.sh" || fail "client links leaked by installer"
  grep -Fq 'ArchiveNetwork/wgcf-cli' "\$root/app/routing/warp_helper.py" || fail "verified wgcf source missing"
  grep -Fq '"generate", "--xray"' "\$root/app/routing/warp_helper.py" || fail "wgcf Xray generation missing"
  grep -Fq '162.159.192.1:2408' "\$root/app/routing/warp.py" || fail "verified WARP IPv4 endpoint missing"
  grep -Fq 'noKernelTun' "\$root/app/routing/warp.py" || fail "noKernelTun contract missing"
  grep -Fq 'WARP JSON' "\$root/app/web/templates/outbounds.html" || fail "WARP JSON action missing"
  grep -Fq 'sg-readable-typography-v3.css' "\$root/app/web/templates/base.html" || fail "readable typography is not loaded"
  grep -Fq -- '--sgrt-small: 13px' "\$root/app/web/static/sg-readable-typography-v3.css" || fail "readable small-text scale missing"
  grep -Fq '.ob49-page' "\$root/app/web/static/sg-readable-typography-v3.css" || fail "Outbounds typography coverage missing"
  grep -Fq '.r096-page' "\$root/app/web/static/sg-readable-typography-v3.css" || fail "Routing typography coverage missing"
  grep -Fq '.mtv2-page' "\$root/app/web/static/sg-readable-typography-v3.css" || fail "Maintenance typography coverage missing"
  grep -Fq '.secv2-page' "\$root/app/web/static/sg-readable-typography-v3.css" || fail "Security typography coverage missing"
  grep -Fq '.hlpv1-page' "\$root/app/web/static/sg-readable-typography-v3.css" || fail "Help typography coverage missing"
  ! grep -Fq 'Clients list row exact 2× typography' "\$root/app/web/static/sg-readable-typography-v3.css" || fail "rejected doubled Clients row remains"
  ! grep -Fq 'height: 136px' "\$root/app/web/static/sg-readable-typography-v3.css" || fail "rejected Clients row height remains"
  ! grep -RIFq --exclude='*.svg' --exclude='*.dat' --exclude='*.sqlite' '51820' "\$root/app" "\$root/hostd" "\$root/deploy" "\$root/install.sh" "\$root/release-manifest.json" || fail "stale UDP 51820 remains in managed source"
  grep -Fq 'local suffix="[Enter = Да / n = Нет]"' "\$root/install.sh" || fail "sg-admin Enter=yes prompt missing"
  grep -Fq 'sanitize_installer_stream()' "\$root/install.sh" || fail "installer log sanitizer missing"
  grep -Fq 'sanitize_installer_stream < "\$raw_output" >> "\$INSTALL_LOG"' "\$root/install.sh" || fail "stage output is not sanitized"
  grep -Fq '[REDACTED PEM BLOCK]' "\$root/install.sh" || fail "PEM redaction missing"
  grep -Fq '[REDACTED LONG CREDENTIAL]' "\$root/install.sh" || fail "long credential redaction missing"
  ! grep -Fq '.dv16-' "\$root/app/web/static/sg-readable-typography-v3.css" || fail "approved client-detail typography was changed"
  ! grep -Fq 'dv16-add-bottom' "\$root/app/web/templates/client_detail.html" || fail "duplicate add-device button remains"
  python3 - "\$root" <<'PY'
from pathlib import Path
import ast, json, sys
root=Path(sys.argv[1])
install=(root/'install.sh').read_text(encoding='utf-8')
final=install.rsplit('INSTALL_SUCCESS=1',1)[1]
for forbidden in ('subscription-base64','vless://','hysteria2://','hy2://','mieru://','BEGIN CERTIFICATE','BEGIN PRIVATE KEY'):
    if forbidden in final:
        raise SystemExit(f'sensitive final output marker remains: {forbidden}')
for base in (root/'app', root/'hostd', root/'engines'):
    for path in base.rglob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
for path in root.rglob('*.json'):
    json.loads(path.read_text(encoding='utf-8'))
import sqlite3
with sqlite3.connect(root / 'data/sg-gateway.sqlite') as connection:
    row = connection.execute("SELECT port FROM connection_settings WHERE engine='amneziawg'").fetchone()
assert row and int(row[0]) == 585, row
requirements=json.loads((root/'SG-GATEWAY-021-REQUIREMENTS.json').read_text(encoding='utf-8'))
assert requirements['invariants']['amneziawg_udp_port'] == 585
assert requirements['invariants']['clients_row_typography'] == 'approved-v018-scale'
PY
}
extract_payload
verify_source
case "\${1:-}" in
  --verify-only)
    printf '[%s] Payload and source verified.\n' "\$PACKAGE"
    exit 0
    ;;
  --extract-only)
    destination="\${2:-\$PWD/SG-Gateway-021-SOURCE}"
    rm -rf "\$destination"
    mkdir -p "\$destination"
    cp -a "\$TEMP_DIR/\$SOURCE_FOLDER/." "\$destination/"
    printf '[%s] Source extracted to %s\n' "\$PACKAGE" "\$destination"
    exit 0
    ;;
esac
exec bash "\$TEMP_DIR/\$SOURCE_FOLDER/install.sh"
exit 1
__SG_GATEWAY_021_REBUILT_PAYLOAD_BEGIN__
EOF2
base64 -w 76 "$TMP/payload.tar.gz" >> "$OUT"
printf '\n__SG_GATEWAY_021_REBUILT_PAYLOAD_END__\n' >> "$OUT"
chmod +x "$OUT"
printf '%s\n' "$OUT"
