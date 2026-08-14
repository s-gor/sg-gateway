from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "app/web/templates/connections.html"
CSS = ROOT / "app/web/static/sg-xray-profiles-v2.css"
TEST = ROOT / "tests/test_sg_gateway_02114_xmux_simple_expert_ui.py"

body = TEMPLATE.read_text(encoding="utf-8")
new_block = r'''            <section class="xps2-xmux" data-xmux-shared>
              <div class="xps2-xmux-main">
                <div class="xps2-xmux-copy">
                  <span>XMUX · XHTTP Reality + XHTTP TLS</span>
                  {% if xray_profiles.xhttp_xmux_mode == 'auto' %}
                  <strong>Автоматически · рекомендуется</strong>
                  <small>Xray использует штатные настройки XMUX. Для обычной работы ничего менять не нужно.</small>
                  {% else %}
                  <strong>Экспертная настройка активна</strong>
                  <small>Сейчас используется выбранный вручную режим XMUX. Откройте экспертные настройки, чтобы посмотреть или изменить его.</small>
                  {% endif %}
                </div>
                <span class="xps2-xmux-badge {{ 'recommended' if xray_profiles.xhttp_xmux_mode == 'auto' else 'expert' }}">
                  {{ 'Рекомендуется' if xray_profiles.xhttp_xmux_mode == 'auto' else 'Эксперт' }}
                </span>
              </div>

              <details class="xps2-xmux-details" {% if xray_profiles.xhttp_xmux_mode != 'auto' %}open{% endif %}>
                <summary>
                  <span class="xps2-xmux-show">Экспертные настройки XMUX</span>
                  <span class="xps2-xmux-hide">Скрыть экспертные настройки</span>
                </summary>

                <div class="xps2-xmux-expert">
                  <label class="xps2-xmux-mode-field">
                    <span>Режим XMUX</span>
                    <select name="xhttp_xmux_mode" data-xmux-mode>
                      {% for item in xray_profiles.xhttp_xmux_mode_options %}
                      <option value="{{ item.value }}" {% if item.value == xray_profiles.xhttp_xmux_mode %}selected{% endif %}>{{ item.title }}</option>
                      {% endfor %}
                    </select>
                    <small>Для большинства установок оставьте Xray Auto. Остальные варианты нужны только для точной настройки или совместимости.</small>
                  </label>

                  <details class="xps2-xmux-technical">
                    <summary>Технические значения пресетов</summary>
                    <div class="xps2-xmux-grid">
                      <div><span>Standard · SG-Panel</span><small>preset</small><strong>{{ xray_profiles.xhttp_xmux_standard | tojson }}</strong></div>
                      <div><span>Для РФ — уменьшенный · SG-Panel</span><small>preset</small><strong>{{ xray_profiles.xhttp_xmux_reduced | tojson }}</strong></div>
                      <div><span>Текущий effective XMUX</span><small>extra.xmux</small><strong>{{ xray_profiles.xhttp_xmux_effective | tojson if xray_profiles.xhttp_xmux_effective else 'не передаётся · native Xray' }}</strong></div>
                    </div>
                  </details>

                  <div class="xps2-xmux-grid" data-xmux-manual {% if xray_profiles.xhttp_xmux_mode != 'expert' %}hidden{% endif %}>
                    <div><span>Максимальная параллельность</span><small>maxConcurrency</small><input type="text" name="xhttp_xmux_maxConcurrency" value="{{ xray_profiles.xhttp_xmux_expert.get('maxConcurrency', '') }}" placeholder="0 или 8-16"></div>
                    <div><span>Максимум соединений</span><small>maxConnections</small><input type="text" name="xhttp_xmux_maxConnections" value="{{ xray_profiles.xhttp_xmux_expert.get('maxConnections', '') }}" placeholder="6 или 2-4"></div>
                    <div><span>Повторное использование</span><small>cMaxReuseTimes</small><input type="text" name="xhttp_xmux_cMaxReuseTimes" value="{{ xray_profiles.xhttp_xmux_expert.get('cMaxReuseTimes', '') }}" placeholder="0 или 300-600"></div>
                    <div><span>HTTP-запросов</span><small>hMaxRequestTimes</small><input type="text" name="xhttp_xmux_hMaxRequestTimes" value="{{ xray_profiles.xhttp_xmux_expert.get('hMaxRequestTimes', '') }}" placeholder="600-900"></div>
                    <div><span>Время reuse, сек.</span><small>hMaxReusableSecs</small><input type="text" name="xhttp_xmux_hMaxReusableSecs" value="{{ xray_profiles.xhttp_xmux_expert.get('hMaxReusableSecs', '') }}" placeholder="1800-3000"></div>
                    <div><span>Keep-Alive</span><small>hKeepAlivePeriod</small><input type="number" min="0" name="xhttp_xmux_hKeepAlivePeriod" value="{{ xray_profiles.xhttp_xmux_expert.get('hKeepAlivePeriod', '') }}" placeholder="0"></div>
                  </div>
                  <p class="xps2-xmux-expert-note">Ручной режим принимает число или диапазон <code>N-M</code>. Положительные <code>maxConnections</code> и <code>maxConcurrency</code> одновременно не используются.</p>
                </div>
              </details>
            </section>'''

pattern = re.compile(
    r'            <section class="xps2-xmux" data-xmux-shared>.*?\n            </section>\n          </section>\n\n          <footer class="xps2-actions">',
    re.S,
)
replacement = new_block + '\n          </section>\n\n          <footer class="xps2-actions">'
body, count = pattern.subn(replacement, body, count=1)
if count != 1:
    raise SystemExit(f"XMUX block replacement count={count}, expected 1")

old_sync = '''  const syncXmux = () => {\n    if (!xmuxManual) return;\n    const manual = xmuxMode?.value === 'expert';\n    xmuxManual.querySelectorAll('input').forEach(input => { input.disabled = !manual; });\n    xmuxManual.style.opacity = manual ? '1' : '.55';\n  };'''
new_sync = '''  const syncXmux = () => {\n    if (!xmuxManual) return;\n    const manual = xmuxMode?.value === 'expert';\n    xmuxManual.hidden = !manual;\n    xmuxManual.querySelectorAll('input').forEach(input => { input.disabled = !manual; });\n  };'''
if old_sync not in body:
    raise SystemExit("syncXmux block not found")
body = body.replace(old_sync, new_sync, 1)
TEMPLATE.write_text(body, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")
marker = "/* SG-Gateway 02114 · simplified XMUX summary and expert controls */"
if marker in css:
    css = css.split(marker, 1)[0].rstrip() + "\n"
css += r'''

/* SG-Gateway 02114 · simplified XMUX summary and expert controls */
.xps2-xmux-main{align-items:center}
.xps2-xmux-badge{display:inline-flex;align-items:center;min-height:28px;padding:0 10px;border:1px solid var(--line);border-radius:999px;background:var(--panel);font-size:10px;font-weight:850;white-space:nowrap}
.xps2-xmux-badge.recommended{color:var(--green)}
.xps2-xmux-badge.expert{color:var(--yellow)}
.xps2-xmux-details{padding:10px 14px 14px}
.xps2-xmux-expert{display:grid;gap:12px;margin-top:12px}
.xps2-xmux-mode-field{display:grid;gap:6px}
.xps2-xmux-mode-field>span{color:var(--muted);font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.04em}
.xps2-xmux-mode-field>small,.xps2-xmux-expert-note{margin:0;color:var(--muted);font-size:10px;line-height:1.45}
.xps2-xmux-mode-field select{width:100%;min-height:40px;border-radius:9px}
.xps2-xmux-technical{border:1px solid var(--line-soft);border-radius:10px;background:var(--panel);padding:9px 11px}
.xps2-xmux-technical>summary{color:var(--muted);font-size:11px;font-weight:750;cursor:pointer}
.xps2-xmux-technical[open]>summary{margin-bottom:10px;color:var(--text)}
.xps2-xmux-grid[hidden]{display:none!important}
@media (max-width:650px){.xps2-xmux-main{align-items:flex-start;flex-direction:column}.xps2-xmux-badge{align-self:flex-start}}
'''
CSS.write_text(css, encoding="utf-8")

TEST.write_text(r'''from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_xmux_normal_view_is_simple_and_recommended() -> None:
    body = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    assert "Автоматически · рекомендуется" in body
    assert "Для обычной работы ничего менять не нужно." in body
    assert "Экспертные настройки XMUX" in body
    assert body.index("Экспертные настройки XMUX") < body.index('name="xhttp_xmux_mode"')


def test_xmux_technical_values_are_nested_under_expert_controls() -> None:
    body = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    assert "Технические значения пресетов" in body
    assert body.index("Экспертные настройки XMUX") < body.index("Технические значения пресетов")
    assert body.index("Технические значения пресетов") < body.index("Standard · SG-Panel")
    assert 'data-xmux-manual {% if xray_profiles.xhttp_xmux_mode != \'expert\' %}hidden{% endif %}' in body


def test_xmux_custom_mode_reopens_expert_section_without_resetting_choice() -> None:
    body = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    assert '<details class="xps2-xmux-details" {% if xray_profiles.xhttp_xmux_mode != \'auto\' %}open{% endif %}>' in body
    assert 'value="{{ item.value }}" {% if item.value == xray_profiles.xhttp_xmux_mode %}selected{% endif %}' in body
    assert "xmuxManual.hidden = !manual;" in body
''', encoding="utf-8")
