#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${SG_GATEWAY_ROOT:-/opt/sg-gateway}"
TEMPLATE="$ROOT/app/web/templates/client_detail.html"
PARTIAL="$ROOT/app/web/templates/_sg_subscription_dual.html"

[[ -f "$TEMPLATE" ]] || { echo "missing $TEMPLATE" >&2; exit 1; }
[[ -f "$PARTIAL" ]] || { echo "missing $PARTIAL" >&2; exit 1; }

python3 - "$TEMPLATE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
anchor = '  <section class="dv16-devices" aria-label="Устройства клиента">\n'
marker = '<!-- SG_SUBSCRIPTION_DUAL_UI_V1 -->'
include = marker + '\n  {% include "_sg_subscription_dual.html" %}\n\n'
old_start = '  {% set client_sg_subscription = sg_subscription_url(client) %}\n'

if anchor not in text:
    raise SystemExit("SG Subscription UI anchor not found")

if marker not in text:
    if old_start in text:
        start = text.index(old_start)
        end = text.index(anchor, start)
        text = text[:start] + '  ' + include + text[end:]
    else:
        text = text.replace(anchor, '  ' + include + anchor, 1)

text = text.replace('<strong>Подписка устройства</strong>', '<strong>Legacy SUB устройства</strong>')
text = text.replace(
    '<span>Ссылка для NekoBox и совместимых клиентов.</span>',
    '<span>Совместимая legacy-подписка устройства.</span>',
)
path.write_text(text, encoding="utf-8")
PY

grep -q 'SG_SUBSCRIPTION_DUAL_UI_V1' "$TEMPLATE"
grep -q 'data-sg-subscription-dual-v1' "$PARTIAL"
grep -q 'Универсальная подписка' "$PARTIAL"
grep -q 'SG Client / SG Mobile' "$PARTIAL"
grep -q 'sg_subscription_v1_universal_qr' "$PARTIAL"
grep -q 'sg_subscription_v1_qr' "$PARTIAL"
grep -q 'Legacy SUB устройства' "$TEMPLATE"
echo "[PASS] Dual universal + SG Subscription UI applied"
