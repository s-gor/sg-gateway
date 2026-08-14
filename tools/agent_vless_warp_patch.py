from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def patch_connections() -> None:
    path = "app/web/templates/connections.html"
    body = read(path)
    old_pattern = re.compile(
        r'\n                <section class="xps2-xmux">\n.*?\n                </section>\n                \{% endif %\}',
        re.DOTALL,
    )
    body, count = old_pattern.subn("\n                {% endif %}", body, count=1)
    if count != 1:
        raise SystemExit(f"connections XMUX old block matches={count}, expected 1")

    anchor = '            <p class="xps2-empty-note" data-xps2-empty>Выберите хотя бы одну карточку Xray.</p>\n'
    if body.count(anchor) != 1:
        raise SystemExit("connections XMUX insertion anchor is not unique")
    shared = r'''

            <section class="xps2-xmux" data-xmux-shared>
              <div class="xps2-xmux-main">
                <div class="xps2-xmux-copy">
                  <span>Общий клиентский XMUX · XHTTP Reality + XHTTP TLS</span>
                  <strong>{{ 'Xray Auto · рекомендуется' if xray_profiles.xhttp_xmux_mode == 'auto' else xray_profiles.xhttp_xmux_mode }}</strong>
                  <small>В Xray Auto SG-Gateway не добавляет <code>extra.xmux</code>: используются штатные значения установленного Xray. Пресеты и ручной режим включаются только по выбору администратора.</small>
                </div>
              </div>

              <label>
                <span>Режим XMUX</span>
                <select name="xhttp_xmux_mode" data-xmux-mode>
                  {% for item in xray_profiles.xhttp_xmux_mode_options %}
                  <option value="{{ item.value }}" {% if item.value == xray_profiles.xhttp_xmux_mode %}selected{% endif %}>{{ item.title }} · {{ item.note }}</option>
                  {% endfor %}
                </select>
                <small>Xray Auto — рекомендуемый режим. Standard и «Для РФ — уменьшенный» сохранены как опциональные пресеты SG-Panel.</small>
              </label>

              <details class="xps2-xmux-details" open>
                <summary>
                  <span class="xps2-xmux-show">Показать пресеты и ручные параметры</span>
                  <span class="xps2-xmux-hide">Скрыть параметры</span>
                </summary>

                <div class="xps2-xmux-grid">
                  <div><span>Standard · SG-Panel</span><small>preset</small><strong>{{ xray_profiles.xhttp_xmux_standard | tojson }}</strong></div>
                  <div><span>Для РФ — уменьшенный · SG-Panel</span><small>preset</small><strong>{{ xray_profiles.xhttp_xmux_reduced | tojson }}</strong></div>
                  <div><span>Текущий effective XMUX</span><small>extra.xmux</small><strong>{{ xray_profiles.xhttp_xmux_effective | tojson if xray_profiles.xhttp_xmux_effective else 'не передаётся · native Xray' }}</strong></div>
                </div>

                <div class="xps2-xmux-grid" data-xmux-manual>
                  <div><span>Максимальная параллельность</span><small>maxConcurrency</small><input type="text" name="xhttp_xmux_maxConcurrency" value="{{ xray_profiles.xhttp_xmux_expert.get('maxConcurrency', '') }}" placeholder="0 или 8-16"></div>
                  <div><span>Максимум соединений</span><small>maxConnections</small><input type="text" name="xhttp_xmux_maxConnections" value="{{ xray_profiles.xhttp_xmux_expert.get('maxConnections', '') }}" placeholder="6 или 2-4"></div>
                  <div><span>Повторное использование</span><small>cMaxReuseTimes</small><input type="text" name="xhttp_xmux_cMaxReuseTimes" value="{{ xray_profiles.xhttp_xmux_expert.get('cMaxReuseTimes', '') }}" placeholder="0 или 300-600"></div>
                  <div><span>HTTP-запросов</span><small>hMaxRequestTimes</small><input type="text" name="xhttp_xmux_hMaxRequestTimes" value="{{ xray_profiles.xhttp_xmux_expert.get('hMaxRequestTimes', '') }}" placeholder="600-900"></div>
                  <div><span>Время reuse, сек.</span><small>hMaxReusableSecs</small><input type="text" name="xhttp_xmux_hMaxReusableSecs" value="{{ xray_profiles.xhttp_xmux_expert.get('hMaxReusableSecs', '') }}" placeholder="1800-3000"></div>
                  <div><span>Keep-Alive</span><small>hKeepAlivePeriod</small><input type="number" min="0" name="xhttp_xmux_hKeepAlivePeriod" value="{{ xray_profiles.xhttp_xmux_expert.get('hKeepAlivePeriod', '') }}" placeholder="0"></div>
                </div>
                <p>Ручной режим принимает число или диапазон <code>N-M</code> для range-полей. Положительные <code>maxConnections</code> и <code>maxConcurrency</code> одновременно запрещены Xray. XMUX остаётся клиентским параметром; серверный inbound не меняется.</p>
              </details>
            </section>
'''
    body = body.replace(anchor, anchor + shared, 1)

    js_anchor = "  const modes = [...form.querySelectorAll('input[name=\"hysteria2_obfs_mode\"]')];\n"
    if body.count(js_anchor) != 1:
        raise SystemExit("connections JS variable anchor is not unique")
    body = body.replace(
        js_anchor,
        js_anchor
        + "  const xmuxMode = form.querySelector('[data-xmux-mode]');\n"
        + "  const xmuxManual = form.querySelector('[data-xmux-manual]');\n",
        1,
    )
    fn_anchor = "  const syncConfirmation = () => {\n"
    if body.count(fn_anchor) != 1:
        raise SystemExit("connections JS function anchor is not unique")
    sync_xmux = """  const syncXmux = () => {\n    if (!xmuxManual) return;\n    const manual = xmuxMode?.value === 'expert';\n    xmuxManual.querySelectorAll('input').forEach(input => { input.disabled = !manual; });\n    xmuxManual.style.opacity = manual ? '1' : '.55';\n  };\n\n"""
    body = body.replace(fn_anchor, sync_xmux + fn_anchor, 1)
    listener_anchor = "  modes.forEach(item => item.addEventListener('change', syncSalamander));\n"
    if body.count(listener_anchor) != 1:
        raise SystemExit("connections JS listener anchor is not unique")
    body = body.replace(
        listener_anchor,
        listener_anchor + "  xmuxMode?.addEventListener('change', syncXmux);\n",
        1,
    )
    sync_anchor = "    syncSalamander();\n  };\n"
    if body.count(sync_anchor) != 1:
        raise SystemExit("connections JS sync anchor is not unique")
    body = body.replace(sync_anchor, "    syncSalamander();\n    syncXmux();\n  };\n", 1)
    if "XMUX для РФ</strong>" in body or "Рекомендуемый профиль для российских сетей" in body:
        raise SystemExit("old forced RF XMUX UI survived")
    write(path, body)


def patch_installer() -> None:
    path = "install.sh"
    body = read(path)
    removals = [
        '  run_quiet "Этап 10/10 · Создание и активация WARP" stage9_ensure_warp\n',
        '  run_hidden "Этап 9/9 · 4/6 · Создание и активация WARP" stage9_ensure_warp\n',
    ]
    for value in removals:
        if body.count(value) != 1:
            raise SystemExit(f"install removal anchor count={body.count(value)}: {value.strip()}")
        body = body.replace(value, "", 1)
    body = body.replace(
        "Этап 9/9 · 3/6 · Сохранение/применение Xray runtime",
        "Этап 9/9 · 3/5 · Сохранение/применение Xray runtime",
    )
    body = body.replace("Этап 9/9 · 5/6 · Запуск панели", "Этап 9/9 · 4/5 · Запуск панели")
    body = body.replace(
        "Этап 9/9 · 6/6 · Проверка Nginx и служб",
        "Этап 9/9 · 5/5 · Проверка Nginx и служб",
    )
    old_status = "  printf '[SG-Gateway] WARP:         создан и активен\\n'\n"
    if body.count(old_status) != 1:
        raise SystemExit("install final WARP status anchor is not unique")
    new_status = """  if [[ -s \"$DATA_DIR/warp/wgcf.xray.json\" || -s \"$DATA_DIR/warp/wgcf-profile.conf\" ]]; then\n    printf '[SG-Gateway] WARP:         существующий профиль сохранён\\n'\n  else\n    printf '[SG-Gateway] WARP:         helper установлен; создаётся при необходимости в Outbounds\\n'\n  fi\n"""
    body = body.replace(old_status, new_status, 1)
    write(path, body)


def patch_docs() -> None:
    write(
        "docs/CONNECTIONS.md",
        '''# Connections и клиентские профили

## AmneziaWG

SG-Gateway использует один серверный AmneziaWG-профиль. Настройки сервера включают адрес, DNS, ключи и параметры профиля. Для каждого устройства создаётся отдельная клиентская конфигурация.

## Xray

### VLESS Reality TCP

TCP/Reality-профиль с XTLS Vision.

### VLESS XHTTP Reality

Клиентская ссылка содержит XHTTP mode и VLESS Encryption. XMUX настраивается общим клиентским параметром для обоих XHTTP-профилей.

### VLESS XHTTP TLS

Требует готового HTTPS-домена. Клиентская ссылка содержит XHTTP mode и VLESS Encryption. XMUX использует тот же общий выбранный режим.

### Hysteria 2

Использует QUIC/UDP и TLS. Salamander FinalMask настраивается отдельно и проверяется перед применением.

## XMUX для XHTTP

По умолчанию выбран **Xray Auto**: SG-Gateway не добавляет `extra.xmux`, и клиент использует штатные значения установленного Xray.

Администратор может выбрать один из режимов:

- **Xray Auto** — рекомендуется, без навязанных значений;
- **Standard** — совместимый пресет SG-Panel;
- **Для РФ — уменьшенный** — совместимый пресет SG-Panel;
- **Ручной** — собственные значения или диапазоны для всех полей XMUX.

Standard:

```json
{
  "maxConnections": "2-4",
  "cMaxReuseTimes": "300-600",
  "hMaxRequestTimes": "1000-2000",
  "hMaxReusableSecs": "1200-2400",
  "hKeepAlivePeriod": 600
}
```

Для РФ — уменьшенный:

```json
{
  "maxConcurrency": 0,
  "maxConnections": 6,
  "cMaxReuseTimes": 0,
  "hMaxRequestTimes": "600-900",
  "hMaxReusableSecs": "1800-3000",
  "hKeepAlivePeriod": 0
}
```

Положительные `maxConnections` и `maxConcurrency` одновременно запрещены. Любой выбранный XMUX добавляется только в клиентский `extra.xmux` и не записывается в серверный inbound.

## Mihomo и sing-box

- Mieru обслуживается Mihomo;
- AnyTLS и TUIC v5 обслуживаются отдельным sing-box.

Каждый движок имеет собственное runtime-состояние, а панель объединяет их результаты в одном интерфейсе. Выключенный профиль не выдаётся клиентам как доступный, при этом сохранённые реквизиты остаются в базе для повторного включения.
''',
    )

    path = "docs/TECHNICAL.md"
    body = read(path)
    body = body.replace(
        "| VLESS XHTTP Reality | XHTTP | REALITY | `xtls-rprx-vision` | Да | Да | Не требуется |",
        "| VLESS XHTTP Reality | XHTTP | REALITY | `xtls-rprx-vision` | Да | Опционально | Не требуется |",
    )
    body = body.replace(
        "| VLESS XHTTP TLS | XHTTP | TLS | `xtls-rprx-vision` | Да | Да | Требуется |",
        "| VLESS XHTTP TLS | XHTTP | TLS | `xtls-rprx-vision` | Да | Опционально | Требуется |",
    )
    body = body.replace(
        'extra={"xmux":{...}}',
        '[extra={"xmux":{...}}]  # только preset/manual; в Xray Auto отсутствует',
    )
    marker = "Профиль доступен только при готовом HTTPS-состоянии.\n"
    if marker in body and "По умолчанию XMUX работает в режиме **Xray Auto**" not in body:
        body = body.replace(
            marker,
            marker
            + "\nПо умолчанию XMUX работает в режиме **Xray Auto**: `extra.xmux` не передаётся. Standard, уменьшенный и ручной режимы являются явным выбором администратора и применяются только к клиентским XHTTP-профилям.\n",
            1,
        )
    write(path, body)


def patch_tests() -> None:
    write(
        "tests/test_sg_gateway_021_xmux_rf.py",
        r'''from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from app.xray import profiles as profiles_module
from app.xray.profiles import _values
from app.xray.sg_panel_vless import reality_tcp_link, xhttp_reality_link
from app.xray.xmux import (
    XHTTP_XMUX_REDUCED,
    XHTTP_XMUX_STANDARD,
    XmuxError,
    normalise_expert,
    resolve,
)

ROOT = Path(__file__).resolve().parents[1]


def test_sg_panel_compatibility_presets_are_exact():
    assert XHTTP_XMUX_STANDARD == {
        "maxConnections": "2-4",
        "cMaxReuseTimes": "300-600",
        "hMaxRequestTimes": "1000-2000",
        "hMaxReusableSecs": "1200-2400",
        "hKeepAlivePeriod": 600,
    }
    assert XHTTP_XMUX_REDUCED == {
        "maxConcurrency": 0,
        "maxConnections": 6,
        "cMaxReuseTimes": 0,
        "hMaxRequestTimes": "600-900",
        "hMaxReusableSecs": "1800-3000",
        "hKeepAlivePeriod": 0,
    }


def test_native_xray_auto_is_default_and_does_not_force_extra_xmux():
    values = _values({}, 443)
    assert values["xhttp_xmux_mode"] == "auto"
    assert values["xhttp_xmux_effective"] is None


def test_overview_uses_no_client_xmux_in_native_auto(monkeypatch):
    settings = SimpleNamespace(host="203.0.113.10", port=443)
    config = {
        "public_key": "public-key",
        "short_id": "0123456789abcdef",
        "vless_encryption": "mlkem768x25519plus.native.0rtt.example",
    }
    monkeypatch.setattr(
        profiles_module,
        "_config",
        lambda: (settings, config, {"https_ready": True, "domain": "vpn.example"}),
    )
    monkeypatch.setattr(profiles_module, "_service_active", lambda: False)
    monkeypatch.setattr(profiles_module, "_installed_xray_version", lambda: "26.6.27")
    monkeypatch.setattr(profiles_module, "_vless_encryption_ready", lambda value: True)

    state = profiles_module.overview()
    by_id = {item.id: item for item in state["profiles"]}
    assert state["xhttp_xmux_mode"] == "auto"
    assert state["xhttp_xmux_effective"] is None
    assert by_id["xhttp_reality"].xmux_enabled is False
    assert by_id["xhttp_reality"].xmux is None
    assert by_id["xhttp_tls"].xmux_enabled is False
    assert by_id["xhttp_tls"].xmux is None


def test_optional_presets_resolve_only_when_selected():
    assert resolve({"xhttp_xmux_mode": "standard"})[2] == XHTTP_XMUX_STANDARD
    assert resolve({"xhttp_xmux_mode": "reduced"})[2] == XHTTP_XMUX_REDUCED


def test_manual_xmux_accepts_ranges_and_blocks_conflicting_positive_controllers():
    manual = normalise_expert(
        {
            "maxConcurrency": 0,
            "maxConnections": "2-4",
            "cMaxReuseTimes": "300-600",
            "hMaxRequestTimes": "600-900",
            "hMaxReusableSecs": "1800-3000",
            "hKeepAlivePeriod": 0,
        },
        require_non_empty=True,
    )
    assert manual["maxConnections"] == "2-4"
    assert manual["hKeepAlivePeriod"] == 0

    with pytest.raises(XmuxError, match="положительные maxConnections и maxConcurrency"):
        normalise_expert(
            {"maxConcurrency": "8-16", "maxConnections": 6},
            require_non_empty=True,
        )


def test_xhttp_reality_native_auto_link_has_no_extra(monkeypatch):
    monkeypatch.delenv("SG_GATEWAY_PUBLIC_ADDRESS", raising=False)
    link = xhttp_reality_link(
        uuid="11111111-1111-4111-8111-111111111111",
        host="203.0.113.10",
        port=8444,
        title="XMUX Native Auto",
        fingerprint="firefox",
        server_name="www.microsoft.com",
        public_key="public-key",
        short_id="0123456789abcdef",
        path="/sg-xhttp-reality",
        encryption="mlkem768x25519plus.native.0rtt.example",
        client_mode="stream-one",
        xmux=None,
    )
    query = parse_qs(urlsplit(link).query)
    assert "extra" not in query


def test_xhttp_reality_selected_standard_link_contains_extra(monkeypatch):
    monkeypatch.delenv("SG_GATEWAY_PUBLIC_ADDRESS", raising=False)
    link = xhttp_reality_link(
        uuid="11111111-1111-4111-8111-111111111111",
        host="203.0.113.10",
        port=8444,
        title="XMUX Standard",
        fingerprint="firefox",
        server_name="www.microsoft.com",
        public_key="public-key",
        short_id="0123456789abcdef",
        path="/sg-xhttp-reality",
        encryption="mlkem768x25519plus.native.0rtt.example",
        client_mode="stream-one",
        xmux=XHTTP_XMUX_STANDARD,
    )
    query = parse_qs(urlsplit(link).query)
    assert json.loads(query["extra"][0]) == {"xmux": XHTTP_XMUX_STANDARD}


def test_reality_links_prefer_direct_public_address_over_passed_domain(monkeypatch):
    direct_ip = "203.0.113.77"
    monkeypatch.setenv("SG_GATEWAY_PUBLIC_ADDRESS", direct_ip)

    tcp = reality_tcp_link(
        uuid="11111111-1111-4111-8111-111111111111",
        host="vpn.example",
        port=443,
        title="Reality TCP",
        fingerprint="firefox",
        server_name="www.bing.com",
        public_key="public-key",
        short_id="0123456789abcdef",
    )
    xhttp = xhttp_reality_link(
        uuid="11111111-1111-4111-8111-111111111111",
        host="vpn.example",
        port=8444,
        title="XHTTP Reality",
        fingerprint="firefox",
        server_name="www.bing.com",
        public_key="public-key",
        short_id="0123456789abcdef",
        path="/sg-xhttp-reality",
        encryption="mlkem768x25519plus.native.0rtt.example",
        client_mode="stream-one",
        xmux=None,
    )

    assert urlsplit(tcp).hostname == direct_ip
    assert urlsplit(xhttp).hostname == direct_ip
    assert "vpn.example" not in tcp
    assert "vpn.example" not in xhttp


def test_reality_links_keep_explicit_host_when_direct_address_is_unset(monkeypatch):
    monkeypatch.delenv("SG_GATEWAY_PUBLIC_ADDRESS", raising=False)
    link = reality_tcp_link(
        uuid="11111111-1111-4111-8111-111111111111",
        host="vpn.example",
        port=443,
        title="Reality TCP",
        fingerprint="firefox",
        server_name="www.bing.com",
        public_key="public-key",
        short_id="0123456789abcdef",
    )
    assert urlsplit(link).hostname == "vpn.example"


def test_xmux_ui_exposes_auto_presets_and_manual_without_forcing_rf():
    template = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    inbound = (ROOT / "app/xray/sg_panel_vless.py").read_text(encoding="utf-8")

    for label in ("Xray Auto", "Standard", "Для РФ — уменьшенный", "Ручной"):
        assert label in template
    for key in (
        "maxConcurrency",
        "maxConnections",
        "cMaxReuseTimes",
        "hMaxRequestTimes",
        "hMaxReusableSecs",
        "hKeepAlivePeriod",
    ):
        assert key in template
    assert "Рекомендуемый профиль для российских сетей" not in template
    assert "XMUX для РФ</strong>" not in template
    server_function = inbound.split("def xhttp_reality_inbound", 1)[1].split(
        "def reality_tcp_link", 1
    )[0]
    assert '"xmux"' not in server_function
''',
    )

    write(
        "tests/test_sg_gateway_02113_optional_warp_install.py",
        '''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_clean_install_keeps_warp_helper_but_never_auto_registers_warp() -> None:
    body = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "install_wgcf_from_vendor" in body
    assert "[Engine 5/5] WARP wgcf-cli" in body
    assert 'run_quiet "Этап 10/10 · Создание и активация WARP" stage9_ensure_warp' not in body
    assert 'run_hidden "Этап 9/9 · 4/6 · Создание и активация WARP" stage9_ensure_warp' not in body
    assert "WARP:         создан и активен" not in body
    assert "helper установлен; создаётся при необходимости в Outbounds" in body


def test_manual_warp_creation_remains_available_after_install() -> None:
    outbounds = (ROOT / "app/web/templates/outbounds.html").read_text(encoding="utf-8")
    commands = (ROOT / "hostd/sg_hostd/commands.py").read_text(encoding="utf-8")
    assert "Создать WARP" in outbounds
    assert "warp.install" in commands
''',
    )


def remove_one_shot_files() -> None:
    for relative in (
        ".github/workflows/agent-vless-warp-patch.yml",
        "tools/agent_vless_warp_patch.py",
    ):
        target = ROOT / relative
        if target.exists():
            target.unlink()


def refresh_source_manifest() -> None:
    manifest = ROOT / "SOURCE-SHA256SUMS"
    paths: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        _, name = line.split("  ", 1)
        paths.append(name)
    for name in (
        "app/xray/xmux.py",
        "tests/test_sg_gateway_02113_optional_warp_install.py",
    ):
        if name not in paths:
            paths.append(name)
    paths = sorted(set(paths))
    output: list[str] = []
    for name in paths:
        target = ROOT / name
        if not target.is_file():
            raise SystemExit(f"SOURCE inventory target missing: {name}")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        output.append(f"{digest}  {name}")
    manifest.write_text("\n".join(output) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    patch_connections()
    patch_installer()
    patch_docs()
    patch_tests()
    remove_one_shot_files()
    refresh_source_manifest()


if __name__ == "__main__":
    main()
