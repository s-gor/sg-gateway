from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD_BUILD = "DEV-02206-BASE-R1"
NEW_BUILD = "DEV-02206-CONNECTIONS-POLISH-R1"
SOURCE_BRANCH = "agent/restore-connections-polish-20260814"
SOURCE_CI_RUN = 31818719737


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


# Build identity stays in the 022.06 development line, but now names the first UI feature.
assert read("BUILD-ID").strip() == OLD_BUILD
write("BUILD-ID", NEW_BUILD + "\n")

manifest_path = ROOT / "release-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
assert manifest["version"] == "0.1.0-022.06"
assert manifest["build"] == OLD_BUILD
assert manifest["status"] == "DEVELOPMENT"
assert manifest["channel"] == "dev-02206"
manifest["build"] = NEW_BUILD
manifest["development_feature"] = {
    "id": "connections-polish-r1",
    "scope": "ui-only",
    "runtime_changes": False,
    "source_branch": SOURCE_BRANCH,
    "source_ci_run": SOURCE_CI_RUN,
    "preserves": ["gecko", "sg-panel-xmux", "vpn-runtime"],
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

# Restore only the proven Connections presentation layer from the old verified branch.
# Do NOT transplant its older Xray/Salamander/XMUX runtime implementation.
template = read("app/web/templates/connections.html")

old_article = """              <article class=\"xps2-parameter-row {{ 'is-visible' if profile.enabled and not locked else '' }}\"\n                       data-profile-panel=\"{{ profile.id }}\">"""
new_article = """              <article class=\"xps2-parameter-row {{ 'has-xhttp' if profile.mode else '' }} {{ 'is-visible' if profile.enabled and not locked else '' }}\"\n                       data-profile-panel=\"{{ profile.id }}\">"""
assert template.count(old_article) == 1
template = template.replace(old_article, new_article)

old_port = """                <label>\n                  <span>{{ 'UDP-порт' if profile.id == 'hysteria2' else 'TCP-порт' }}</span>"""
new_port = """                <label class=\"xps2-port-field\">\n                  <span>{{ 'UDP-порт' if profile.id == 'hysteria2' else 'TCP-порт' }}</span>"""
assert template.count(old_port) == 1
template = template.replace(old_port, new_port)

old_mode_ui = """                {% if profile.mode %}\n                <label>\n                  <span>XHTTP mode клиента</span>\n                  <select name=\"{{ profile.id }}_mode\" {% if locked %}disabled{% endif %}>\n                    {% for item in xray_profiles.xhttp_mode_options %}\n                    <option value=\"{{ item.value }}\" {% if item.value == profile.mode %}selected{% endif %}>{{ item.title }} · {{ item.value }}</option>\n                    {% endfor %}\n                  </select>\n                  <small>Сервер остаётся в auto и принимает все четыре режима. Выбор меняет клиентские ссылки, QR и SG Client subscription.</small>\n                </label>\n\n"""
assert template.count(old_mode_ui) == 1
template = template.replace(old_mode_ui, "                {% if profile.mode %}\n")

old_encryption = """                {% if profile.encryption_required %}\n                <div class=\"xps2-flow-field\">\n                  <span>VLESS Encryption</span>"""
new_encryption = """                {% if profile.encryption_required %}\n                <div class=\"xps2-flow-field xps2-encryption-field\">\n                  <span>VLESS Encryption</span>"""
assert template.count(old_encryption) == 1
template = template.replace(old_encryption, new_encryption)

old_path = """                {% if profile.path %}\n                <label>\n                  <span>Public Path</span>"""
new_path = """                {% if profile.path %}\n                <label class=\"xps2-path-field\">\n                  <span>Public Path</span>"""
assert template.count(old_path) == 1
template = template.replace(old_path, new_path)

anchor = """            <p class=\"xps2-empty-note\" data-xps2-empty>Выберите хотя бы одну карточку Xray.</p>\n          </section>\n\n          <footer class=\"xps2-actions\">"""
expert = """            <p class=\"xps2-empty-note\" data-xps2-empty>Выберите хотя бы одну карточку Xray.</p>\n\n            <details class=\"cnv1-advanced sg-ljd-nested xps2-xhttp-expert\">\n              <summary>\n                <span>Экспертные настройки XHTTP</span>\n                <span>Обычно не требуются</span>\n              </summary>\n              <div class=\"cnv1-advanced-body xps2-xhttp-expert-body\">\n                <div class=\"xps2-xhttp-mode-grid\">\n                  {% for profile in xray_profiles.profiles %}\n                  {% if profile.mode %}\n                  {% set tls_locked = profile.tls_required and not xray_profiles.tls_ready %}\n                  {% set encryption_locked = profile.encryption_required and not profile.encryption_ready %}\n                  {% set locked = tls_locked or encryption_locked %}\n                  <label data-xhttp-mode-profile=\"{{ profile.id }}\">\n                    <span>{{ profile.title }} · режим клиента</span>\n                    <select name=\"{{ profile.id }}_mode\" {% if locked %}disabled{% endif %}>\n                      {% for item in xray_profiles.xhttp_mode_options %}\n                      <option value=\"{{ item.value }}\" {% if item.value == profile.mode %}selected{% endif %}>{{ item.title }} · {{ item.value }}</option>\n                      {% endfor %}\n                    </select>\n                    <small>Сервер остаётся в auto. Reality фиксируется как в SG-Panel; TLS можно менять осознанно.</small>\n                  </label>\n                  {% endif %}\n                  {% endfor %}\n                </div>\n              </div>\n            </details>\n          </section>\n\n          <footer class=\"xps2-actions\">"""
assert template.count(anchor) == 1
template = template.replace(anchor, expert)

# Guard the accepted 022.05 additions while editing only presentation.
assert "Hysteria2 Obfuscation" in template
assert 'value="gecko"' in template
assert "Gecko · рекомендуется" in template
assert '{% include "_xray_xmux_settings.html" %}' in template
assert "sg-xmux-settings-v1.css" in template
assert "sg-xmux-settings-v1.js" in template
assert "xps2-xmux" in template
write("app/web/templates/connections.html", template)

# Restore compact XHTTP geometry, adapted to the current SG-Panel XMUX UI.
xray_css = read("app/web/static/sg-xray-profiles-v2.css")
marker = "/* SG-Gateway 022.06 · restored Connections polish over accepted XMUX/Gecko UI. */"
assert marker not in xray_css
xray_css += r'''

/* SG-Gateway 022.06 · restored Connections polish over accepted XMUX/Gecko UI. */
@media (min-width: 1281px) {
  .xps2-parameter-row.has-xhttp {
    grid-template-columns: minmax(215px, 1.05fr) minmax(120px, .38fr) minmax(210px, .72fr) minmax(175px, .58fr) minmax(205px, .72fr);
    align-items: stretch;
  }

  .xps2-parameter-row.has-xhttp > .xps2-parameter-title {
    align-self: center;
  }

  .xps2-parameter-row.has-xhttp > :is(.xps2-port-field, .xps2-flow-field, .xps2-encryption-field, .xps2-path-field) {
    min-width: 0;
    align-self: stretch;
  }
}

.xps2-xhttp-expert {
  grid-column: 1 / -1;
  margin-top: 14px;
  overflow: hidden;
}

.xps2-xhttp-expert > summary {
  min-height: 44px;
  padding: 0 14px;
}

.xps2-xhttp-expert-body {
  display: grid;
  gap: 14px;
  padding: 14px;
}

.xps2-xhttp-mode-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.xps2-xhttp-mode-grid label {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.xps2-xhttp-mode-grid label > span {
  color: var(--sg-text);
  font-size: 11px;
  font-weight: 750;
}

.xps2-xhttp-mode-grid label > small {
  margin: 0;
  color: var(--sg-muted);
  font-size: 9px;
  line-height: 1.45;
}

.xps2-xhttp-mode-grid select {
  width: 100%;
  min-height: 40px;
}

@media (max-width: 900px) {
  .xps2-xhttp-mode-grid {
    grid-template-columns: 1fr;
  }
}
'''
write("app/web/static/sg-xray-profiles-v2.css", xray_css)

# The current tree ends with a recovery override that forces Mihomo to full width.
# Remove only that tail so the already-existing balanced Preview-28 rules become active again.
preview = read("app/web/static/sg-preview28-final.css")
full_width_marker = "/* SG-Gateway 021 · Mihomo as a separate full-width Connections block */"
assert preview.count(full_width_marker) == 1
preview = preview.split(full_width_marker, 1)[0].rstrip() + "\n"
assert "grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);" in preview
assert ".cnv1-engine-awg .cnv1-form-actions { margin-top: auto; }" in preview
write("app/web/static/sg-preview28-final.css", preview)

# Keep the dedicated 022.06 CI identity aligned with the new development build.
workflow = read(".github/workflows/ci-02206-dev.yml")
assert workflow.count(OLD_BUILD) == 1
workflow = workflow.replace(OLD_BUILD, NEW_BUILD)
write(".github/workflows/ci-02206-dev.yml", workflow)

identity_test = read("tests/test_sg_gateway_02206_development_identity.py")
assert identity_test.count(OLD_BUILD) == 2
identity_test = identity_test.replace(OLD_BUILD, NEW_BUILD)
write("tests/test_sg_gateway_02206_development_identity.py", identity_test)

# Add user-facing documentation without changing the protocol contract.
docs = read("docs/CONNECTIONS.md")
docs_anchor = "## Xray\n\n"
assert docs.count(docs_anchor) == 1
docs_insert = (
    "## Xray\n\n"
    "На широком экране параметры XHTTP снова собраны в компактные строки, а выбор клиентского XHTTP mode вынесен в сворачиваемый блок «Экспертные настройки XHTTP». "
    "Новый отдельный SG-Panel XMUX-блок и Gecko остаются без изменений. Ниже AmneziaWG и Mihomo занимают две сбалансированные колонки; на узком экране они складываются вертикально.\n\n"
)
docs = docs.replace(docs_anchor, docs_insert)
write("docs/CONNECTIONS.md", docs)

changelog = read("CHANGELOG.md")
changelog_anchor = "- Frozen 022.05 updater channel remains `dev-02205`.\n"
assert changelog.count(changelog_anchor) == 1
changelog = changelog.replace(
    changelog_anchor,
    changelog_anchor
    + "- Connections polish R1 restores the previously CI-verified balanced AmneziaWG/Mihomo layout and compact XHTTP rows as a UI-only change; Gecko, SG-Panel XMUX and VPN runtime are preserved.\n",
)
write("CHANGELOG.md", changelog)

write(
    "tests/test_sg_gateway_02206_connections_polish.py",
    f'''from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\n\n\ndef _text(path: str) -> str:\n    return (ROOT / path).read_text(encoding="utf-8")\n\n\ndef test_connections_restores_balanced_awg_mihomo_pair() -> None:\n    css = _text("app/web/static/sg-preview28-final.css")\n    assert "Mihomo as a separate full-width Connections block" not in css\n    assert "grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);" in css\n    assert ".cnv1-engine-pair {{ align-items: stretch; }}" in css\n    assert ".cnv1-engine-awg .cnv1-form-actions {{ margin-top: auto; }}" in css\n\n\ndef test_xhttp_rows_are_compact_without_losing_current_xmux_ui() -> None:\n    template = _text("app/web/templates/connections.html")\n    css = _text("app/web/static/sg-xray-profiles-v2.css")\n    xmux_css = _text("app/web/static/sg-xmux-settings-v1.css")\n    row_start = template.index('<div class="xps2-parameter-list">')\n    row_end = template.index('<p class="xps2-empty-note"', row_start)\n    row_block = template[row_start:row_end]\n    assert "{{{{ 'has-xhttp' if profile.mode else '' }}}}" in row_block\n    assert 'class="xps2-port-field"' in row_block\n    assert 'class="xps2-flow-field xps2-encryption-field"' in row_block\n    assert 'class="xps2-path-field"' in row_block\n    assert "XHTTP mode клиента" not in row_block\n    assert "xps2-xmux" in row_block  # historical marker retained for 022.05 contract\n    assert "restored Connections polish over accepted XMUX/Gecko UI" in css\n    assert ".xps2-parameter-row.has-xhttp" in css\n    assert '{% include "_xray_xmux_settings.html" %}' in template\n    assert ".xps2-xmux" in xmux_css and "display: none" in xmux_css\n\n\ndef test_xhttp_mode_moves_to_single_collapsed_expert_section() -> None:\n    template = _text("app/web/templates/connections.html")\n    assert template.count('class="cnv1-advanced sg-ljd-nested xps2-xhttp-expert"') == 1\n    assert "Экспертные настройки XHTTP" in template\n    assert "Обычно не требуются" in template\n    assert 'data-xhttp-mode-profile="{{{{ profile.id }}}}"' in template\n    assert 'select name="{{{{ profile.id }}}}_mode"' in template\n    assert 'xps2-xhttp-mode-grid' in _text("app/web/static/sg-xray-profiles-v2.css")\n\n\ndef test_current_gecko_and_sg_panel_xmux_contract_survive_polish() -> None:\n    template = _text("app/web/templates/connections.html")\n    js = _text("app/web/static/sg-xmux-settings-v1.js")\n    partial = _text("app/web/templates/_xray_xmux_settings.html")\n    assert "Hysteria2 Obfuscation" in template\n    assert 'value="gecko"' in template\n    assert "Gecko · рекомендуется" in template\n    assert "XMUX для XHTTP" in partial\n    assert "Стандартный" in partial\n    assert "Для РФ — уменьшенный" in partial\n    assert "Ручной" in partial\n    assert "stream-one" in js\n    assert "hidden.name = 'xhttp_reality_mode'" in js\n\n\ndef test_connections_polish_is_declared_ui_only() -> None:\n    assert _text("BUILD-ID").strip() == "{NEW_BUILD}"\n    manifest = json.loads(_text("release-manifest.json"))\n    assert manifest["build"] == "{NEW_BUILD}"\n    feature = manifest["development_feature"]\n    assert feature["id"] == "connections-polish-r1"\n    assert feature["scope"] == "ui-only"\n    assert feature["runtime_changes"] is False\n    assert feature["source_branch"] == "{SOURCE_BRANCH}"\n    assert feature["source_ci_run"] == {SOURCE_CI_RUN}\n    assert set(feature["preserves"]) == {{"gecko", "sg-panel-xmux", "vpn-runtime"}}\n''',
)
