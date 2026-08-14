from __future__ import annotations

from pathlib import Path
import hashlib
import re
import subprocess

ROOT = Path('.')
TEMPLATE = ROOT / 'app/web/templates/connections.html'
XRAY_CSS = ROOT / 'app/web/static/sg-xray-profiles-v2.css'
LAYOUT_CSS = ROOT / 'app/web/static/sg-preview28-final.css'
PUBLICATION_TEST = ROOT / 'tests/test_sg_gateway_021_full_publication_ru.py'
XMUX_TEST = ROOT / 'tests/test_sg_gateway_02114_xmux_simple_expert_ui.py'
POLISH_TEST = ROOT / 'tests/test_sg_gateway_02115_connections_polish.py'
SOURCE = ROOT / 'SOURCE-SHA256SUMS'

body = TEMPLATE.read_text(encoding='utf-8')

old = '''              <article class="xps2-parameter-row {{ 'is-visible' if profile.enabled and not locked else '' }}"\n                       data-profile-panel="{{ profile.id }}">'''
new = '''              <article class="xps2-parameter-row {{ 'has-xhttp' if profile.mode else '' }} {{ 'is-visible' if profile.enabled and not locked else '' }}"\n                       data-profile-panel="{{ profile.id }}">'''
if old not in body:
    raise SystemExit('parameter-row marker not found')
body = body.replace(old, new, 1)

old = '''                <label>\n                  <span>{{ 'UDP-порт' if profile.id == 'hysteria2' else 'TCP-порт' }}</span>'''
new = '''                <label class="xps2-port-field">\n                  <span>{{ 'UDP-порт' if profile.id == 'hysteria2' else 'TCP-порт' }}</span>'''
if old not in body:
    raise SystemExit('port field marker not found')
body = body.replace(old, new, 1)

mode_block = '''                {% if profile.mode %}\n                <label>\n                  <span>XHTTP mode клиента</span>\n                  <select name="{{ profile.id }}_mode" {% if locked %}disabled{% endif %}>\n                    {% for item in xray_profiles.xhttp_mode_options %}\n                    <option value="{{ item.value }}" {% if item.value == profile.mode %}selected{% endif %}>{{ item.title }} · {{ item.value }}</option>\n                    {% endfor %}\n                  </select>\n                  <small>Сервер остаётся в auto и принимает все четыре режима. Выбор меняет клиентские ссылки, QR и SG Client subscription.</small>\n                </label>\n\n                {% endif %}\n'''
if mode_block not in body:
    raise SystemExit('inline XHTTP mode block not found')
body = body.replace(mode_block, '', 1)

old = '''                <div class="xps2-flow-field">\n                  <span>VLESS Encryption</span>'''
new = '''                <div class="xps2-flow-field xps2-encryption-field">\n                  <span>VLESS Encryption</span>'''
if old not in body:
    raise SystemExit('encryption field marker not found')
body = body.replace(old, new, 1)

old = '''                <label>\n                  <span>Public Path</span>'''
new = '''                <label class="xps2-path-field">\n                  <span>Public Path</span>'''
if old not in body:
    raise SystemExit('path field marker not found')
body = body.replace(old, new, 1)

expert = r'''            <details class="cnv1-advanced sg-ljd-nested xps2-xhttp-expert" {% if xray_profiles.xhttp_xmux_mode != 'auto' %}open{% endif %}>
              <summary>
                <span>Экспертные настройки XHTTP</span>
                <span>Обычно не требуются</span>
              </summary>
              <div class="cnv1-advanced-body xps2-xhttp-expert-body">
                <div class="xps2-xhttp-mode-grid">
                  {% for profile in xray_profiles.profiles %}
                  {% if profile.mode %}
                  <label>
                    <span>{{ profile.title }} · режим клиента</span>
                    <select name="{{ profile.id }}_mode">
                      {% for item in xray_profiles.xhttp_mode_options %}
                      <option value="{{ item.value }}" {% if item.value == profile.mode %}selected{% endif %}>{{ item.title }} · {{ item.value }}</option>
                      {% endfor %}
                    </select>
                    <small>Сервер остаётся в auto. Этот выбор меняет только клиентские ссылки, QR и subscription.</small>
                  </label>
                  {% endif %}
                  {% endfor %}
                </div>

                <div class="xps2-xmux-expert-block">
                  <label class="xps2-xmux-mode-field">
                    <span>XMUX</span>
                    <select name="xhttp_xmux_mode" data-xmux-mode>
                      {% for item in xray_profiles.xhttp_xmux_mode_options %}
                      <option value="{{ item.value }}" {% if item.value == xray_profiles.xhttp_xmux_mode %}selected{% endif %}>{{ item.title }}</option>
                      {% endfor %}
                    </select>
                    <small>Xray Auto — рекомендуемый вариант. Остальные режимы нужны только для осознанной ручной настройки.</small>
                  </label>

                  <div class="xps2-xmux-manual-grid" data-xmux-manual {% if xray_profiles.xhttp_xmux_mode != 'expert' %}hidden{% endif %}>
                    <label><span>Макс. параллельность</span><small>maxConcurrency</small><input type="text" name="xhttp_xmux_maxConcurrency" value="{{ xray_profiles.xhttp_xmux_expert.get('maxConcurrency', '') }}" placeholder="0 или 8-16"></label>
                    <label><span>Макс. соединений</span><small>maxConnections</small><input type="text" name="xhttp_xmux_maxConnections" value="{{ xray_profiles.xhttp_xmux_expert.get('maxConnections', '') }}" placeholder="6 или 2-4"></label>
                    <label><span>Повторное использование</span><small>cMaxReuseTimes</small><input type="text" name="xhttp_xmux_cMaxReuseTimes" value="{{ xray_profiles.xhttp_xmux_expert.get('cMaxReuseTimes', '') }}" placeholder="0 или 300-600"></label>
                    <label><span>HTTP-запросов</span><small>hMaxRequestTimes</small><input type="text" name="xhttp_xmux_hMaxRequestTimes" value="{{ xray_profiles.xhttp_xmux_expert.get('hMaxRequestTimes', '') }}" placeholder="600-900"></label>
                    <label><span>Reuse, сек.</span><small>hMaxReusableSecs</small><input type="text" name="xhttp_xmux_hMaxReusableSecs" value="{{ xray_profiles.xhttp_xmux_expert.get('hMaxReusableSecs', '') }}" placeholder="1800-3000"></label>
                    <label><span>Keep-Alive</span><small>hKeepAlivePeriod</small><input type="number" min="0" name="xhttp_xmux_hKeepAlivePeriod" value="{{ xray_profiles.xhttp_xmux_expert.get('hKeepAlivePeriod', '') }}" placeholder="0"></label>
                  </div>
                  <p class="xps2-xmux-expert-note">В ручном режиме диапазоны задаются как <code>N-M</code>. Положительные maxConnections и maxConcurrency одновременно не используются.</p>
                </div>
              </div>
            </details>'''

pattern = re.compile(
    r'\n\n            <section class="xps2-xmux" data-xmux-shared>.*?\n            </section>\n          </section>\n\n          <footer class="xps2-actions">',
    re.S,
)
replacement = '\n\n' + expert + '\n          </section>\n\n          <footer class="xps2-actions">'
body, count = pattern.subn(replacement, body, count=1)
if count != 1:
    raise SystemExit(f'XMUX section replacement count={count}, expected 1')
TEMPLATE.write_text(body, encoding='utf-8')

css = XRAY_CSS.read_text(encoding='utf-8')
marker = '/* SG-Gateway 021 · client-only XMUX controls with native Xray Auto */'
if marker not in css:
    raise SystemExit('XMUX CSS marker not found')
css = css.split(marker, 1)[0].rstrip() + r'''


/* SG-Gateway 02115 · restore polished Connections geometry. */
@media (min-width: 1281px) {
  .xps2-parameter-row.has-xhttp {
    grid-template-columns: minmax(215px,1.05fr) minmax(120px,.38fr) minmax(210px,.72fr) minmax(175px,.58fr) minmax(205px,.72fr);
    align-items: stretch;
  }
  .xps2-parameter-row.has-xhttp > .xps2-parameter-title { align-self:center; }
  .xps2-parameter-row.has-xhttp > :is(.xps2-port-field,.xps2-flow-field,.xps2-encryption-field,.xps2-path-field) {
    min-width:0;
    align-self:stretch;
  }
  .xps2-parameter-row.has-xhttp > .xps2-flow-field { min-width:0; }
}

.xps2-xhttp-expert {
  grid-column:1/-1;
  margin-top:14px;
  overflow:hidden;
}
.xps2-xhttp-expert > summary {
  min-height:44px;
  padding:0 14px;
}
.xps2-xhttp-expert-body {
  display:grid;
  gap:14px;
  padding:14px;
}
.xps2-xhttp-mode-grid {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:12px;
}
.xps2-xhttp-expert-body label,
.xps2-xmux-mode-field,
.xps2-xmux-manual-grid label {
  display:grid;
  gap:6px;
  min-width:0;
}
.xps2-xhttp-expert-body label > span {
  color:var(--sg-text);
  font-size:11px;
  font-weight:750;
}
.xps2-xhttp-expert-body label > small,
.xps2-xmux-expert-note {
  margin:0;
  color:var(--sg-muted);
  font-size:9px;
  line-height:1.45;
}
.xps2-xhttp-expert-body select,
.xps2-xhttp-expert-body input {
  width:100%;
  min-height:40px;
}
.xps2-xmux-expert-block {
  display:grid;
  gap:12px;
  border-top:1px solid var(--sg-line-soft);
  padding-top:14px;
}
.xps2-xmux-manual-grid {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:10px;
}
.xps2-xmux-manual-grid[hidden] { display:none!important; }
.xps2-xmux-manual-grid label {
  border:1px solid var(--sg-line-soft);
  border-radius:10px;
  background:var(--sg-panel);
  padding:10px;
}
.xps2-xmux-manual-grid label > small {
  color:var(--sg-muted);
  font-size:8px;
  overflow-wrap:anywhere;
}
@media (max-width:1280px) {
  .xps2-parameter-row.has-xhttp { grid-template-columns:1fr 1fr; }
  .xps2-parameter-row.has-xhttp > .xps2-parameter-title { grid-column:1/-1; }
}
@media (max-width:900px) {
  .xps2-xhttp-mode-grid,
  .xps2-xmux-manual-grid { grid-template-columns:1fr; }
}
@media (max-width:650px) {
  .xps2-parameter-row.has-xhttp { grid-template-columns:1fr; }
}
'''
XRAY_CSS.write_text(css, encoding='utf-8')

layout = LAYOUT_CSS.read_text(encoding='utf-8')
full_marker = '/* SG-Gateway 021 · Mihomo as a separate full-width Connections block */'
if full_marker not in layout:
    raise SystemExit('full-width Mihomo override marker not found')
layout = layout.split(full_marker, 1)[0].rstrip() + '\n'
LAYOUT_CSS.write_text(layout, encoding='utf-8')

pub = PUBLICATION_TEST.read_text(encoding='utf-8')
old_pub = '''    assert "Автоматически · рекомендуется" in template\n    assert "Экспертные настройки XMUX" in template\n    assert "Технические значения пресетов" in template\n    assert "xps2-xmux-switch" not in template\n    assert "client-only XMUX controls with native Xray Auto" in xray_css\n    assert "Mihomo as a separate full-width Connections block" in layout_css\n    assert "grid-template-columns: minmax(0, 1fr) !important" in layout_css\n'''
new_pub = '''    assert "Экспертные настройки XHTTP" in template\n    assert "Xray Auto — рекомендуемый вариант" in template\n    assert "Технические значения пресетов" not in template\n    assert "xps2-xmux-switch" not in template\n    assert "restore polished Connections geometry" in xray_css\n    assert "Mihomo as a separate full-width Connections block" not in layout_css\n    assert "grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)" in layout_css\n'''
if old_pub not in pub:
    raise SystemExit('publication UI assertions not found')
PUBLICATION_TEST.write_text(pub.replace(old_pub, new_pub, 1), encoding='utf-8')

XMUX_TEST.write_text(r'''from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_normal_xray_rows_do_not_show_xhttp_tuning_controls() -> None:
    body = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    parameter_start = body.index('<div class="xps2-parameter-list">')
    expert_start = body.index('Экспертные настройки XHTTP')
    normal = body[parameter_start:expert_start]
    assert "XHTTP mode клиента" not in normal
    assert 'data-xmux-mode' not in normal
    assert "Технические значения пресетов" not in body


def test_xhttp_modes_and_xmux_live_inside_one_expert_line() -> None:
    body = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    expert_start = body.index('Экспертные настройки XHTTP')
    footer = body.index('<footer class="xps2-actions">', expert_start)
    expert = body[expert_start:footer]
    assert 'name="{{ profile.id }}_mode"' in expert
    assert 'name="xhttp_xmux_mode"' in expert
    assert 'data-xmux-manual' in expert
    assert 'Xray Auto — рекомендуемый вариант' in expert


def test_manual_xmux_fields_stay_hidden_until_manual_mode() -> None:
    body = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    assert 'data-xmux-manual {% if xray_profiles.xhttp_xmux_mode != \'expert\' %}hidden{% endif %}' in body
    assert 'xmuxManual.hidden = !manual;' in body
''', encoding='utf-8')

POLISH_TEST.write_text(r'''from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_connections_restores_balanced_awg_mihomo_pair() -> None:
    css = (ROOT / "app/web/static/sg-preview28-final.css").read_text(encoding="utf-8")
    assert "Mihomo as a separate full-width Connections block" not in css
    assert "grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)" in css
    assert ".cnv1-engine-pair { align-items: stretch; }" in css
    assert ".cnv1-engine-awg .cnv1-form-actions { margin-top: auto; }" in css


def test_xhttp_rows_are_compact_on_wide_desktop() -> None:
    template = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    css = (ROOT / "app/web/static/sg-xray-profiles-v2.css").read_text(encoding="utf-8")
    assert "{{ 'has-xhttp' if profile.mode else '' }}" in template
    assert 'class="xps2-port-field"' in template
    assert 'class="xps2-flow-field xps2-encryption-field"' in template
    assert 'class="xps2-path-field"' in template
    assert ".xps2-parameter-row.has-xhttp" in css
    assert "restore polished Connections geometry" in css


def test_expert_tuning_is_a_single_collapsed_line() -> None:
    template = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    assert 'class="cnv1-advanced sg-ljd-nested xps2-xhttp-expert"' in template
    assert "Экспертные настройки XHTTP" in template
    assert "Обычно не требуются" in template
    assert "Технические значения пресетов" not in template
''', encoding='utf-8')

# Remove helper/workflow from the final tree before regenerating source integrity.
for helper in (
    ROOT / '.github/agent-restore-connections-polish.py',
    ROOT / '.github/workflows/agent-restore-connections-polish.yml',
):
    if helper.exists():
        helper.unlink()

tracked = subprocess.check_output(['git', 'ls-files'], text=True).splitlines()
# git ls-files still includes deleted helper paths until staged; exclude missing files.
rows = []
for relative in tracked:
    if relative == 'SOURCE-SHA256SUMS':
        continue
    path = ROOT / relative
    if not path.is_file():
        continue
    rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
SOURCE.write_text('\n'.join(rows) + '\n', encoding='utf-8')
