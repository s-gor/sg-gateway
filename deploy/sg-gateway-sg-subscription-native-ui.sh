#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${SG_GATEWAY_ROOT:-/opt/sg-gateway}"
TEMPLATE="$ROOT/app/web/templates/client_detail.html"
PARTIAL="$ROOT/app/web/templates/_sg_subscription_dual.html"

[[ -f "$TEMPLATE" ]] || { echo "missing $TEMPLATE" >&2; exit 1; }
[[ -f "$PARTIAL" ]] || { echo "missing $PARTIAL" >&2; exit 1; }

python3 - "$TEMPLATE" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
anchor = '  <section class="dv16-devices" aria-label="Устройства клиента">\n'
marker = '<!-- SG_SUBSCRIPTION_DUAL_UI_V1 -->'
include_line = '  {% include "_sg_subscription_dual.html" %}'
include_block = f'  {marker}\n{include_line}\n\n'

if anchor not in text:
    raise SystemExit("SG Subscription UI anchor not found")


def strip_direct_single_sg_blocks(value: str) -> str:
    """Remove old one-button SG Subscription blocks without touching the dual partial."""
    token = 'data-sg-subscription-v1'
    dual_token = 'data-sg-subscription-dual-v1'
    cursor = 0
    while True:
        hit = value.find(token, cursor)
        if hit < 0:
            break
        section_start = value.rfind('<section', 0, hit)
        section_end = value.find('</section>', hit)
        if section_start < 0 or section_end < 0:
            cursor = hit + len(token)
            continue
        section_end += len('</section>')
        block = value[section_start:section_end]
        if dual_token in block:
            cursor = section_end
            continue

        start = section_start
        end = section_end
        set_start = value.rfind('{% set client_sg_subscription', 0, section_start)
        if_start = value.rfind('{% if client_sg_subscription', 0, section_start)
        if set_start >= 0 and if_start >= set_start and section_start - if_start < 500:
            endif = value.find('{% endif %}', section_end)
            if endif >= 0 and endif - section_end < 500:
                start = set_start
                end = endif + len('{% endif %}')

        value = value[:start] + value[end:]
        cursor = max(0, start - 1)
    return value


# R7/R8/R9 live installations may already contain the old large one-button block.
# Remove it first, even when the dual marker is already present.
text = strip_direct_single_sg_blocks(text)

# Normalize the dual include to exactly one instance immediately before devices.
# Keep whitespace of the following element intact; only consume the marker/include lines.
pattern = re.compile(
    r'^[ \t]*<!-- SG_SUBSCRIPTION_DUAL_UI_V1 -->[ \t]*\n'
    r'^[ \t]*\{% include "_sg_subscription_dual\.html" %\}[ \t]*\n',
    re.MULTILINE,
)
text = pattern.sub('', text)
text = text.replace(anchor, include_block + anchor, 1)

text = text.replace('<strong>Подписка устройства</strong>', '<strong>Legacy SUB устройства</strong>')
text = text.replace(
    '<span>Ссылка для NekoBox и совместимых клиентов.</span>',
    '<span>Совместимая legacy-подписка устройства.</span>',
)
path.write_text(text, encoding="utf-8")
PY

grep -q 'SG_SUBSCRIPTION_DUAL_UI_V1' "$TEMPLATE"
[[ "$(grep -c 'SG_SUBSCRIPTION_DUAL_UI_V1' "$TEMPLATE")" -eq 1 ]]
! grep -q 'data-sg-subscription-v1' "$TEMPLATE"
grep -q 'data-sg-subscription-dual-v1' "$PARTIAL"
grep -q 'Универсальная подписка' "$PARTIAL"
grep -q 'SG Client / SG Mobile' "$PARTIAL"
grep -q 'sg-subscription-copy-universal' "$PARTIAL"
grep -q 'sg-subscription-copy-native' "$PARTIAL"
grep -q '/sg-subscription-v1/qr/universal' "$PARTIAL"
grep -q '/sg-subscription-v1/qr' "$PARTIAL"
grep -q 'Legacy SUB устройства' "$TEMPLATE"
echo "[PASS] Dual universal + SG Subscription UI applied; old single SG block removed"
