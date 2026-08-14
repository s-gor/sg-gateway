from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(body: str, old: str, new: str, label: str) -> str:
    count = body.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, got {count}")
    return body.replace(old, new, 1)


def patch_stale_warp_test() -> None:
    path = "tests/test_sg_gateway_017_warp_panel_port.py"
    body = read(path)
    old = '''def test_installer_creates_and_activates_warp_automatically_and_hides_links():
    source = Path("install.sh").read_text(encoding="utf-8")
    assert "stage9_ensure_warp" in source
    assert "/commands/warp.install" in source
    assert "Создание и активация WARP" in source
    assert "Первый клиент sg-admin: создан" in source
    assert "Первый VPN-клиент sg-admin будет создан автоматически" in source
    final = source.rsplit("INSTALL_SUCCESS=1", 1)[1]
    assert "subscription-base64" not in final
    assert "Ссылки первого клиента" not in source
    assert "WARP создаётся в Outbounds" not in source
'''
    new = '''def test_installer_installs_warp_helper_but_leaves_creation_to_outbounds():
    source = Path("install.sh").read_text(encoding="utf-8")
    assert "stage9_ensure_warp" in source
    assert "/commands/warp.install" in source
    assert "Создание и активация WARP" not in source
    assert "helper установлен; создаётся при необходимости в Outbounds" in source
    assert "Первый клиент sg-admin: создан" in source
    assert "Первый VPN-клиент sg-admin будет создан автоматически" in source
    final = source.rsplit("INSTALL_SUCCESS=1", 1)[1]
    assert "subscription-base64" not in final
    assert "Ссылки первого клиента" not in source
'''
    write(path, replace_once(body, old, new, path))


def patch_publication_test() -> None:
    path = "tests/test_sg_gateway_021_full_publication_ru.py"
    body = read(path)
    body = replace_once(
        body,
        '    assert "<strong>XMUX для РФ</strong>" in template\n    assert "Показать параметры" in template\n',
        '    assert "Xray Auto · рекомендуется" in template\n    assert "Показать пресеты и ручные параметры" in template\n',
        path + " UI",
    )
    body = replace_once(
        body,
        '    assert "compact client-only XMUX preset for Russian networks" in xray_css\n',
        '    assert "client-only XMUX controls with native Xray Auto" in xray_css\n',
        path + " CSS marker",
    )
    body = replace_once(
        body,
        '        "XMUX для российских сетей",\n',
        '        "XMUX для XHTTP",\n',
        path + " technical marker",
    )
    write(path, body)


def patch_xmux_css() -> None:
    path = "app/web/static/sg-xray-profiles-v2.css"
    body = read(path)
    body = replace_once(
        body,
        "/* SG-Gateway 021 · compact client-only XMUX preset for Russian networks */",
        "/* SG-Gateway 021 · client-only XMUX controls with native Xray Auto */",
        path + " comment",
    )
    body = replace_once(
        body,
        ".xps2-xmux-copy>small{color:var(--muted);font-size:11px;line-height:1.4}\n",
        ".xps2-xmux-copy>small{color:var(--muted);font-size:11px;line-height:1.4}\n"
        ".xps2-xmux>label{display:grid;gap:6px;padding:0 14px 13px}\n"
        ".xps2-xmux>label>span{color:var(--muted);font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.04em}\n"
        ".xps2-xmux>label>small{color:var(--muted);font-size:10px;line-height:1.4}\n"
        ".xps2-xmux>label select{width:100%;min-height:40px;border-radius:9px}\n",
        path + " selector styles",
    )
    body = replace_once(
        body,
        ".xps2-xmux-grid strong{grid-column:2;grid-row:1/3;color:var(--text);font-size:14px;white-space:nowrap}\n",
        ".xps2-xmux-grid strong{grid-column:2;grid-row:1/3;color:var(--text);font-size:12px;white-space:normal;overflow-wrap:anywhere;text-align:right}\n"
        ".xps2-xmux-grid input{grid-column:2;grid-row:1/3;width:min(180px,42vw);min-height:38px}\n",
        path + " grid value styles",
    )
    write(path, body)


def patch_technical_docs() -> None:
    path = "docs/TECHNICAL.md"
    body = read(path)
    pattern = re.compile(
        r"## 9\. XMUX для российских сетей\n.*?\n## 10\. Reality\n",
        re.DOTALL,
    )
    replacement = '''## 9. XMUX для XHTTP

XMUX — общий **клиентский** параметр для VLESS XHTTP Reality и VLESS XHTTP TLS. Серверные XHTTP inbound его не получают.

Режим по умолчанию — **Xray Auto**. В этом режиме SG-Gateway вообще не добавляет `extra.xmux`, поэтому используются штатные значения установленного Xray-core.

Администратор может явно выбрать:

- `Xray Auto` — рекомендуемый режим без навязанных значений;
- `Standard` — совместимый пресет SG-Panel;
- `Для РФ — уменьшенный` — совместимый пресет SG-Panel;
- `Ручной` — собственные значения или диапазоны.

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

В ручном режиме поддерживаются `maxConcurrency`, `maxConnections`, `cMaxReuseTimes`, `hMaxRequestTimes`, `hMaxReusableSecs` и `hKeepAlivePeriod`. Для range-полей допустимы число или диапазон `N-M`. Положительные `maxConnections` и `maxConcurrency` одновременно запрещены.

## 10. Reality
'''
    body, count = pattern.subn(replacement, body, count=1)
    if count != 1:
        raise SystemExit(f"{path}: stale XMUX section matches={count}")
    write(path, body)


def patch_readmes() -> None:
    path = "README.md"
    body = read(path)
    body = body.replace(
        "- **VLESS XHTTP Reality + XTLS Vision + VLESS Encryption + XMUX для РФ**;",
        "- **VLESS XHTTP Reality + XTLS Vision + VLESS Encryption + настраиваемый XMUX**;",
    )
    body = body.replace(
        "- **VLESS XHTTP TLS + XTLS Vision + VLESS Encryption + HTTPS + XMUX для РФ**;",
        "- **VLESS XHTTP TLS + XTLS Vision + VLESS Encryption + HTTPS + настраиваемый XMUX**;",
    )
    write(path, body)

    path = "docs/README.md"
    body = read(path)
    body = replace_once(body, "- XMUX для РФ;", "- XMUX для XHTTP: Xray Auto, presets и ручной режим;", path)
    write(path, body)


def cleanup_and_refresh_manifest() -> None:
    for relative in (
        ".github/workflows/agent-contract-cleanup.yml",
        "tools/agent_contract_cleanup.py",
    ):
        target = ROOT / relative
        if target.exists():
            target.unlink()

    manifest = ROOT / "SOURCE-SHA256SUMS"
    paths: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        _, name = line.split("  ", 1)
        paths.append(name)
    output = []
    for name in sorted(set(paths)):
        target = ROOT / name
        if not target.is_file():
            raise SystemExit(f"SOURCE inventory target missing: {name}")
        output.append(f"{hashlib.sha256(target.read_bytes()).hexdigest()}  {name}")
    manifest.write_text("\n".join(output) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    patch_stale_warp_test()
    patch_publication_test()
    patch_xmux_css()
    patch_technical_docs()
    patch_readmes()
    cleanup_and_refresh_manifest()


if __name__ == "__main__":
    main()
