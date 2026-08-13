#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${SG_GATEWAY_ROOT:-/opt/sg-gateway}"
TEMPLATE="$ROOT/app/web/templates/client_detail.html"

[[ -f "$TEMPLATE" ]] || { echo "missing $TEMPLATE" >&2; exit 1; }

python3 - "$TEMPLATE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
marker = 'data-sg-subscription-v1'

if marker not in text:
    anchor = '  <section class="dv16-devices" aria-label="Устройства клиента">\n'
    if anchor not in text:
        raise SystemExit("SG Subscription UI anchor not found")
    block = '''  {% set client_sg_subscription = sg_subscription_url(client) %}\n  {% if client_sg_subscription %}\n  <section class="dv16-subscription state-applied" data-sg-subscription-v1>\n    <div class="dv16-subscription-summary">\n      <strong>SG Subscription</strong>\n      <span>Одна подписка клиента для всех его устройств.</span>\n      <small>SG v1: все выбранные и готовые профили, включая AmneziaWG 2.0 и 3.0.</small>\n    </div>\n    <div class="dv16-subscription-actions">\n      <button class="button primary dv16-copy" type="button" data-copy-value="{{ client_sg_subscription|e }}">Скопировать SG Subscription</button>\n      <details class="dv16-qr">\n        <summary class="button">QR</summary>\n        <div class="dv16-qr-popover">\n          <button type="button" aria-label="Закрыть QR" onclick="this.closest('details').removeAttribute('open')">×</button>\n          <img src="{{ url_for('sg_subscription_v1_qr', client_id=client.id) }}" alt="QR SG Subscription {{ client.name }}">\n        </div>\n      </details>\n    </div>\n  </section>\n  {% endif %}\n\n'''
    text = text.replace(anchor, block + anchor, 1)

text = text.replace('<strong>Подписка устройства</strong>', '<strong>Legacy SUB устройства</strong>')
text = text.replace(
    '<span>Ссылка для NekoBox и совместимых клиентов.</span>',
    '<span>Совместимая legacy-подписка устройства.</span>',
)
path.write_text(text, encoding="utf-8")
PY

grep -q 'data-sg-subscription-v1' "$TEMPLATE"
grep -q 'Legacy SUB устройства' "$TEMPLATE"
echo "[PASS] SG Subscription native UI applied"
