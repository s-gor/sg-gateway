from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"[PASS] {label}")


def restore_preserved_sources() -> None:
    pairs = (
        (ROOT / "app/clients/exports_02205.py", ROOT / "app/clients/exports.py"),
        (ROOT / "app/web/templates/connections_02205.html", ROOT / "app/web/templates/connections.html"),
    )
    for source, target in pairs:
        if not source.is_file():
            raise SystemExit(f"missing preserved baseline: {source.relative_to(ROOT)}")
        shutil.copyfile(source, target)
        print(f"[PASS] restored full 022.05 source: {target.relative_to(ROOT)}")


def patch_exports() -> None:
    path = ROOT / "app/clients/exports.py"

    replace_once(
        path,
        "from urllib.parse import quote, urlencode\n",
        "from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit\n",
        "exports urllib helpers",
    )
    replace_once(
        path,
        "from app.xray.profiles import REALITY_TCP_FLOW, overview as xray_profiles_overview\n",
        "from app.xray.profiles import REALITY_TCP_FLOW, overview as xray_profiles_overview\n"
        "from app.xray.xmux import XmuxError, effective_client_extra\n",
        "exports XMUX imports",
    )

    anchor = '''def _xray_profile(profile_id: str):
    state = xray_profiles_overview()
    return state, next(
        (item for item in state["profiles"] if item.id == profile_id),
        None,
    )


'''
    helper = '''def _xray_profile(profile_id: str):
    state = xray_profiles_overview()
    return state, next(
        (item for item in state["profiles"] if item.id == profile_id),
        None,
    )


def _rewrite_xhttp_link(body: str, profile_id: str, config: dict) -> str:
    """Apply the SG-Panel client-side XMUX contract to one ready XHTTP link."""
    if not body or profile_id not in {"xhttp_reality", "xhttp_tls"}:
        return body

    try:
        extra = effective_client_extra(config)
    except XmuxError:
        # Invalid restored expert JSON must never leak a malformed Client Extra.
        extra = {}

    parts = urlsplit(body)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    rewritten: list[tuple[str, str]] = []
    mode_seen = False
    for key, value in pairs:
        if key == "extra":
            continue
        if profile_id == "xhttp_reality" and key == "mode":
            value = "stream-one"
            mode_seen = True
        rewritten.append((key, value))

    if profile_id == "xhttp_reality" and not mode_seen:
        rewritten.append(("mode", "stream-one"))
    if extra:
        rewritten.append(
            ("extra", json.dumps(extra, ensure_ascii=False, separators=(",", ":")))
        )

    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(rewritten), parts.fragment)
    )


'''
    replace_once(path, anchor, helper, "inline XHTTP link rewriter")

    old_return = '''    else:
        body = ""

    return ClientExport(filename, "text/plain; charset=utf-8", body)
'''
    new_return = '''    else:
        body = ""

    if profile_id in {"xhttp_reality", "xhttp_tls"} and body:
        body = _rewrite_xhttp_link(body, profile_id, current_config)

    return ClientExport(filename, "text/plain; charset=utf-8", body)
'''
    replace_once(path, old_return, new_return, "apply XMUX rewriter only to XHTTP exports")


def patch_connections() -> None:
    path = ROOT / "app/web/templates/connections.html"
    replace_once(
        path,
        "  <link rel=\"stylesheet\" href=\"{{ url_for('static', filename='sg-xray-profiles-v2.css') }}\">\n",
        "  <link rel=\"stylesheet\" href=\"{{ url_for('static', filename='sg-xray-profiles-v2.css') }}\">\n"
        "  <link rel=\"stylesheet\" href=\"{{ url_for('static', filename='sg-xmux-settings-v1.css') }}\">\n",
        "connections XMUX stylesheet",
    )
    replace_once(
        path,
        "\n  <section class=\"cnv1-engine-pair\">\n",
        "\n  {% include \"_xray_xmux_settings.html\" %}\n\n  <section class=\"cnv1-engine-pair\">\n",
        "connections XMUX settings panel",
    )
    replace_once(
        path,
        "{% block scripts %}\n<script>\n",
        "{% block scripts %}\n<script src=\"{{ url_for('static', filename='sg-xmux-settings-v1.js') }}\"></script>\n<script>\n",
        "connections XMUX script",
    )


def patch_xmux_ui_test() -> None:
    path = ROOT / "tests/test_sg_gateway_02205_xmux_sgpanel_contract.py"
    old = '''def test_connections_ui_exposes_exact_sg_panel_modes() -> None:
    wrapper = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    partial = (ROOT / "app/web/templates/_xray_xmux_settings.html").read_text(encoding="utf-8")
    css = (ROOT / "app/web/static/sg-xmux-settings-v1.css").read_text(encoding="utf-8")
    assert 'extends "connections_02205.html"' in wrapper
    assert "XMUX для XHTTP" in partial
    assert "Стандартный" in partial
    assert "Для РФ — уменьшенный" in partial
    assert "Ручной" in partial
    assert "maxConnections 2-4" in partial
    assert "maxConcurrency 0" in partial
    assert ".xps2-xmux" in css and "display: none" in css
'''
    new = '''def test_connections_ui_exposes_exact_sg_panel_modes_in_full_02205_template() -> None:
    template = (ROOT / "app/web/templates/connections.html").read_text(encoding="utf-8")
    partial = (ROOT / "app/web/templates/_xray_xmux_settings.html").read_text(encoding="utf-8")
    css = (ROOT / "app/web/static/sg-xmux-settings-v1.css").read_text(encoding="utf-8")
    js = (ROOT / "app/web/static/sg-xmux-settings-v1.js").read_text(encoding="utf-8")
    assert 'extends "base.html"' in template
    assert 'include "_xray_xmux_settings.html"' in template
    assert "sg-xmux-settings-v1.css" in template
    assert "sg-xmux-settings-v1.js" in template
    # Historical 022.05 source markers stay in the real template; only the old
    # fixed-RF presentation is hidden in favour of the SG-Panel mode selector.
    assert "xps2-xmux" in template
    assert "XMUX для XHTTP" in partial
    assert "Стандартный" in partial
    assert "Для РФ — уменьшенный" in partial
    assert "Ручной" in partial
    assert "maxConnections 2-4" in partial
    assert "maxConcurrency 0" in partial
    assert ".xps2-xmux" in css and "display: none" in css
    assert "stream-one" in js
'''
    replace_once(path, old, new, "XMUX UI test expects in-place 022.05 template")


def remove_wrapper_aliases() -> None:
    for rel in ("app/clients/exports_02205.py", "app/web/templates/connections_02205.html"):
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"expected temporary wrapper baseline: {rel}")
        path.unlink()
        print(f"[PASS] removed temporary wrapper baseline: {rel}")


def main() -> None:
    restore_preserved_sources()
    patch_exports()
    patch_connections()
    patch_xmux_ui_test()
    remove_wrapper_aliases()


if __name__ == "__main__":
    main()
