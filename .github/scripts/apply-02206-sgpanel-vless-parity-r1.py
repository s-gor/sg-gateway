from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD_BUILD = "DEV-02206-FULL-BACKUP-VERIFY-UNLIMITED-R1"
NEW_BUILD = "DEV-02206-SGPANEL-VLESS-PARITY-R1"
SG_PANEL_REFERENCE_COMMIT = "31f1e137d83c02c64bf1039ebbdaf2b02bbfbeae"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, body: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    body = read(path)
    assert body.count(old) == 1, (path, body.count(old), old[:120])
    write(path, body.replace(old, new, 1))


# ---------------------------------------------------------------------------
# Development identity
# ---------------------------------------------------------------------------
assert read("BUILD-ID").strip() == OLD_BUILD
write("BUILD-ID", NEW_BUILD + "\n")

for path in (
    ".github/workflows/ci-02206-dev.yml",
    "tests/test_sg_gateway_02206_development_identity.py",
):
    body = read(path)
    assert OLD_BUILD in body, path
    write(path, body.replace(OLD_BUILD, NEW_BUILD))

manifest_path = ROOT / "release-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
assert manifest["version"] == "0.1.0-022.06"
assert manifest["build"] == OLD_BUILD
assert manifest["channel"] == "dev-02206"
manifest["build"] = NEW_BUILD
manifest["development_vless_parity"] = {
    "id": "sgpanel-vless-parity-r1",
    "reference_repository": "s-gor/sg-panel",
    "reference_commit": SG_PANEL_REFERENCE_COMMIT,
    "unchanged": ["vless-reality-tcp", "vless-xhttp-reality", "xmux-presets"],
    "aligned": [
        "vless-xhttp-tls-local-xray",
        "vless-xhttp-tls-nginx-termination",
        "vless-xhttp-tls-mode",
        "vless-xhttp-tls-client-uri",
    ],
    "other_protocols_changed": False,
}
manifest_path.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
    newline="\n",
)

changelog = read("CHANGELOG.md")
anchor = "- Full Backup Verify/Unlimited R1 integrates the Verify button into Maintenance and removes the artificial .sgbackup upload-size cap, including migration of the previous upload contract on safe panel update.\n"
assert changelog.count(anchor) == 1
write(
    "CHANGELOG.md",
    changelog.replace(
        anchor,
        anchor
        + "- SG-Panel VLESS parity R1 pins the current SG-Panel VLESS contract and aligns XHTTP-TLS to the same Nginx-terminated local-Xray dataplane, selected server/client XHTTP mode, and client URI fields; Reality TCP, XHTTP Reality, XMUX presets and non-Xray protocols are unchanged.\n"
        + "- Panel Update now leaves a replaceable working directory before source-tree replacement, preventing stale-cwd getcwd failures after rollback/update.\n",
        1,
    ),
)

# ---------------------------------------------------------------------------
# Updater must never stand inside /opt/sg-gateway while replacing that tree.
# ---------------------------------------------------------------------------
replace_once(
    "deploy/update-from-github.sh",
    "#!/usr/bin/env bash\nset -Eeuo pipefail\n\n",
    "#!/usr/bin/env bash\nset -Eeuo pipefail\n\n# The updater replaces /opt/sg-gateway. Never inherit a cwd inside that tree.\ncd /\n\n",
)

# ---------------------------------------------------------------------------
# Dedicated XHTTP-TLS front contract: same architecture as current SG-Panel.
# ---------------------------------------------------------------------------
write(
    "hostd/sg_hostd/xhttp_tls_front.py",
    r'''from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

NGINX_SITE = Path("/etc/nginx/sites-available/sg-gateway")
NGINX_SNIPPET = Path("/etc/nginx/snippets/sg-gateway-xhttp-tls.conf")
INCLUDE_DIRECTIVE = "include /etc/nginx/snippets/sg-gateway-xhttp-tls.conf;"
PLACEHOLDER_LISTEN_OLD = "listen 127.0.0.1:7444 ssl;"
PLACEHOLDER_LISTEN_HTTP2 = "listen 127.0.0.1:7444 ssl http2;"
MARKER = "SG_GATEWAY_XHTTP_TLS_SGPANEL_PARITY_R1"


class XhttpTlsFrontError(RuntimeError):
    pass


@dataclass(frozen=True)
class FrontBackup:
    site_existed: bool
    site_body: str
    snippet_existed: bool
    snippet_body: str


def _normalise_path(value: str) -> str:
    path = str(value or "/").strip()
    if not path.startswith("/"):
        path = "/" + path
    return path.rstrip("/") + "/"


def render_snippet(*, enabled: bool, path: str, port: int) -> str:
    lines = [f"# {MARKER}", "# Managed by SG-Gateway HostD; Xray stays local/plain like SG-Panel."]
    if not enabled:
        lines.append("# XHTTP-TLS disabled.")
        return "\n".join(lines) + "\n"
    route = _normalise_path(path)
    lines.extend(
        [
            f"location {route} {{",
            "    grpc_socket_keepalive on;",
            "    grpc_read_timeout 1h;",
            "    grpc_send_timeout 1h;",
            "    client_body_timeout 1h;",
            "    send_timeout 1h;",
            "    client_max_body_size 100m;",
            "    chunked_transfer_encoding on;",
            "    grpc_set_header Host $host;",
            "    grpc_set_header X-Real-IP $remote_addr;",
            "    grpc_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "    grpc_set_header X-Forwarded-Proto $scheme;",
            f"    grpc_pass grpc://127.0.0.1:{int(port)};",
            "}",
        ]
    )
    return "\n".join(lines) + "\n"


def _server_block_bounds(body: str) -> tuple[int, int]:
    listen_at = body.find(PLACEHOLDER_LISTEN_HTTP2)
    if listen_at < 0:
        listen_at = body.find(PLACEHOLDER_LISTEN_OLD)
    if listen_at < 0:
        raise XhttpTlsFrontError("Nginx placeholder TLS listener 127.0.0.1:7444 not found")
    start = body.rfind("server {", 0, listen_at)
    if start < 0:
        raise XhttpTlsFrontError("Nginx placeholder TLS server block not found")
    depth = 0
    seen = False
    for index in range(start, len(body)):
        char = body[index]
        if char == "{":
            depth += 1
            seen = True
        elif char == "}":
            depth -= 1
            if seen and depth == 0:
                return start, index
    raise XhttpTlsFrontError("Nginx placeholder TLS server block is not balanced")


def ensure_site_contract(body: str, *, enable_http2: bool) -> str:
    result = str(body)
    if enable_http2 and PLACEHOLDER_LISTEN_OLD in result:
        result = result.replace(PLACEHOLDER_LISTEN_OLD, PLACEHOLDER_LISTEN_HTTP2, 1)
    # Remove duplicates before inserting into the correct server block.
    lines = [line for line in result.splitlines() if line.strip() != INCLUDE_DIRECTIVE]
    result = "\n".join(lines) + ("\n" if result.endswith("\n") else "")
    start, end = _server_block_bounds(result)
    block = result[start : end + 1]
    if INCLUDE_DIRECTIVE in block:
        return result
    insertion = "    " + INCLUDE_DIRECTIVE + "\n"
    return result[:end] + insertion + result[end:]


def _atomic_write(path: Path, body: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    temporary.write_text(body, encoding="utf-8", newline="\n")
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def _run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=60)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise XhttpTlsFrontError(detail or "command failed: " + " ".join(command))


def prepare(*, enabled: bool, path: str, port: int) -> FrontBackup | None:
    if not NGINX_SITE.is_file():
        if enabled:
            raise XhttpTlsFrontError("Nginx HTTPS site is missing for XHTTP-TLS")
        return None
    site_body = NGINX_SITE.read_text(encoding="utf-8")
    snippet_existed = NGINX_SNIPPET.is_file()
    snippet_body = NGINX_SNIPPET.read_text(encoding="utf-8") if snippet_existed else ""
    backup = FrontBackup(True, site_body, snippet_existed, snippet_body)
    try:
        _atomic_write(
            NGINX_SITE,
            ensure_site_contract(site_body, enable_http2=bool(enabled)),
        )
        _atomic_write(NGINX_SNIPPET, render_snippet(enabled=enabled, path=path, port=port))
        _run(["nginx", "-t"])
    except Exception:
        _atomic_write(NGINX_SITE, site_body)
        if snippet_existed:
            _atomic_write(NGINX_SNIPPET, snippet_body)
        else:
            NGINX_SNIPPET.unlink(missing_ok=True)
        raise
    return backup


def reload_nginx() -> None:
    _run(["nginx", "-t"])
    _run(["systemctl", "reload", "nginx.service"])


def restore(backup: FrontBackup) -> None:
    if backup.site_existed:
        _atomic_write(NGINX_SITE, backup.site_body)
    else:
        NGINX_SITE.unlink(missing_ok=True)
    if backup.snippet_existed:
        _atomic_write(NGINX_SNIPPET, backup.snippet_body)
    else:
        NGINX_SNIPPET.unlink(missing_ok=True)
    reload_nginx()
''',
)

# ---------------------------------------------------------------------------
# Xray runtime: XHTTP-TLS is local/plain; Nginx terminates public TLS by Path.
# ---------------------------------------------------------------------------
runtime_path = "hostd/sg_hostd/client_runtime.py"
runtime = read(runtime_path)
import_anchor = "from app.xray.sg_panel_vless import reality_tcp_inbound, xhttp_reality_inbound\n"
assert runtime.count(import_anchor) == 1
runtime = runtime.replace(
    import_anchor,
    import_anchor
    + "from .xhttp_tls_front import prepare as prepare_xhttp_tls_front, reload_nginx as reload_xhttp_tls_front, restore as restore_xhttp_tls_front\n",
    1,
)

start = runtime.index('    tls_needed = bool({"xhttp_tls", "hysteria2"} & enabled_profiles)\n')
end = runtime.index("\n    if not inbounds:\n", start)
new_tls_section = '''    if "xhttp_tls" in enabled_profiles:\n        if not profiles.get("tls_ready") or not profiles.get("tls_domain"):\n            raise ClientRuntimeError(\n                "XHTTP-TLS выбран, но HTTPS в Security не готов"\n            )\n        profile = by_id["xhttp_tls"]\n        xhttp_settings: dict[str, Any] = {"path": profile.path}\n        mode = str(getattr(profile, "mode", "") or "auto")\n        if mode != "auto":\n            xhttp_settings["mode"] = mode\n        inbounds.append({\n            "tag": "sg-vless-xhttp-tls",\n            "listen": "127.0.0.1",\n            "port": profile.port,\n            "protocol": "vless",\n            "settings": {\n                "clients": grouped["xhttp_tls"],\n                "decryption": vless_decryption,\n            },\n            "streamSettings": {\n                "network": "xhttp",\n                "security": "none",\n                "xhttpSettings": xhttp_settings,\n                "sockopt": {"trustedXForwardedFor": ["127.0.0.1"]},\n            },\n            "sniffing": sniffing,\n        })\n\n    if "hysteria2" in enabled_profiles:\n        if not profiles.get("tls_ready") or not profiles.get("tls_domain"):\n            raise ClientRuntimeError(\n                "Hysteria 2 выбран, но HTTPS в Security не готов"\n            )\n        domain = str(profiles["tls_domain"])\n        cert, key = _sync_xray_tls_material(domain)\n        tls_settings = {\n            "serverName": domain,\n            "minVersion": "1.2",\n            "alpn": ["h2", "http/1.1"],\n            "certificates": [\n                {"certificateFile": cert, "keyFile": key}\n            ],\n        }\n        profile = by_id["hysteria2"]\n        hysteria_tls = dict(tls_settings)\n        hysteria_tls["alpn"] = ["h3"]\n        hysteria_stream = {\n            "network": "hysteria",\n            "security": "tls",\n            "tlsSettings": hysteria_tls,\n            "hysteriaSettings": {\n                "version": 2,\n                "udpIdleTimeout": 60,\n            },\n        }\n        try:\n            finalmask = merge_finalmask(\n                settings_config.get("hysteria2_finalmask") or {},\n                settings_config.get("hysteria2_obfs_mode") or "none",\n                settings_config.get("hysteria2_obfs_password") or "",\n            )\n        except SalamanderError as exc:\n            raise ClientRuntimeError(str(exc)) from exc\n        if finalmask:\n            hysteria_stream["finalmask"] = finalmask\n        inbounds.append({\n            "tag": "sg-hysteria2",\n            "listen": "0.0.0.0",\n            "port": profile.port,\n            "protocol": "hysteria",\n            "settings": {\n                "version": 2,\n                "users": grouped["hysteria2"],\n            },\n            "streamSettings": hysteria_stream,\n            "sniffing": sniffing,\n        })\n'''
runtime = runtime[:start] + new_tls_section + runtime[end:]

# Add a parser that derives the front route from the exact candidate JSON.
apply_anchor = "\ndef test_xray_candidate() -> dict[str, Any]:\n"
front_helper = '''\ndef _xhttp_tls_front_spec(body: str) -> tuple[bool, str, int]:\n    try:\n        payload = json.loads(body)\n    except (TypeError, ValueError, json.JSONDecodeError) as exc:\n        raise ClientRuntimeError("Xray candidate JSON повреждён") from exc\n    for inbound in payload.get("inbounds", []):\n        if not isinstance(inbound, dict) or inbound.get("tag") != "sg-vless-xhttp-tls":\n            continue\n        stream = inbound.get("streamSettings")\n        xhttp = stream.get("xhttpSettings") if isinstance(stream, dict) else None\n        if not isinstance(xhttp, dict):\n            raise ClientRuntimeError("XHTTP-TLS candidate не содержит xhttpSettings")\n        return True, str(xhttp.get("path") or "/"), int(inbound.get("port") or 0)\n    return False, "/", 1\n\n'''
assert runtime.count(apply_anchor) == 1
runtime = runtime.replace(apply_anchor, front_helper + apply_anchor, 1)

old_apply_begin = '''    candidate = CANDIDATE_DIR / "xray-config.json"\n    backup = XRAY_CONFIG.with_suffix(".json.previous")\n    had_live_config = XRAY_CONFIG.is_file()\n    try:\n'''
new_apply_begin = '''    candidate = CANDIDATE_DIR / "xray-config.json"\n    backup = XRAY_CONFIG.with_suffix(".json.previous")\n    had_live_config = XRAY_CONFIG.is_file()\n    front_backup = None\n    try:\n'''
assert runtime.count(old_apply_begin) == 1
runtime = runtime.replace(old_apply_begin, new_apply_begin, 1)

old_candidate_test = '''        _run(\n            [\n                "/usr/local/bin/xray",\n                "run",\n                "-test",\n                "-config",\n                str(candidate),\n            ],\n            timeout=60,\n        )\n        _set_engine_status(engine, ids, "applying")\n'''
new_candidate_test = '''        _run(\n            [\n                "/usr/local/bin/xray",\n                "run",\n                "-test",\n                "-config",\n                str(candidate),\n            ],\n            timeout=60,\n        )\n        front_enabled, front_path, front_port = _xhttp_tls_front_spec(body)\n        front_backup = prepare_xhttp_tls_front(\n            enabled=front_enabled, path=front_path, port=front_port\n        )\n        _set_engine_status(engine, ids, "applying")\n'''
assert runtime.count(old_candidate_test) == 1
runtime = runtime.replace(old_candidate_test, new_candidate_test, 1)

old_restart = '''        _run(["systemctl", "restart", "xray.service"], timeout=90)\n        _run(["systemctl", "is-active", "--quiet", "xray.service"])\n\n        current_profiles = xray_profiles_overview()\n'''
new_restart = '''        _run(["systemctl", "restart", "xray.service"], timeout=90)\n        _run(["systemctl", "is-active", "--quiet", "xray.service"])\n        if front_backup is not None:\n            reload_xhttp_tls_front()\n\n        current_profiles = xray_profiles_overview()\n'''
assert runtime.count(old_restart) == 1
runtime = runtime.replace(old_restart, new_restart, 1)

old_except_tail = '''        if settings_transaction is not None:\n            rollback_settings_transaction(settings_transaction.id, status="rolled_back_runtime_error")\n        restored = _xray_runtime_valid()\n        _set_failure_status(\n            engine,\n            ids,\n            previous,\n            runtime_restored=restored,\n        )\n        return EngineResult(engine, False, f"Xray Reality: {exc}", len(rows))\n'''
new_except_tail = '''        front_restore_error = ""\n        if front_backup is not None:\n            try:\n                restore_xhttp_tls_front(front_backup)\n            except Exception as front_exc:\n                front_restore_error = f"; Nginx rollback: {front_exc}"\n        if settings_transaction is not None:\n            rollback_settings_transaction(settings_transaction.id, status="rolled_back_runtime_error")\n        restored = _xray_runtime_valid()\n        _set_failure_status(\n            engine,\n            ids,\n            previous,\n            runtime_restored=restored,\n        )\n        return EngineResult(engine, False, f"Xray Reality: {exc}{front_restore_error}", len(rows))\n'''
assert runtime.count(old_except_tail) == 1
runtime = runtime.replace(old_except_tail, new_except_tail, 1)
compile(runtime, runtime_path, "exec")
write(runtime_path, runtime)

# ---------------------------------------------------------------------------
# SG-Panel-compatible XHTTP-TLS client URI.
# ---------------------------------------------------------------------------
vless_path = "app/xray/sg_panel_vless.py"
vless = read(vless_path)
append_anchor = '''    return (\n        f"vless://{uuid}@{host}:{int(port)}?{query}"\n        f"#{quote(str(title), safe='')}"\n    )\n'''
# The final occurrence is xhttp_reality_link. Add TLS helper after it.
pos = vless.rfind(append_anchor)
assert pos >= 0
pos += len(append_anchor)
tls_helper = r'''


def xhttp_tls_link(
    *,
    uuid: str,
    host: str,
    port: int,
    title: str,
    fingerprint: str,
    server_name: str,
    path: str,
    encryption: str,
    client_mode: str = "auto",
    xmux: dict[str, Any] | None = None,
) -> str:
    """Build the current SG-Panel XHTTP-TLS client contract."""
    fp = quote(fingerprint_for_xray(fingerprint), safe="")
    encrypted = quote(str(encryption), safe="-._~")
    extra = ""
    if xmux:
        extra_json = json.dumps(
            {"xmux": dict(xmux)},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        extra = f"&extra={quote(extra_json, safe='')}"
    query = (
        f"encryption={encrypted}&flow={REALITY_TCP_FLOW}"
        "&type=xhttp&security=tls"
        f"&fp={fp}&sni={quote(str(server_name), safe='')}"
        f"&host={quote(str(server_name), safe='')}"
        f"&path={quote(str(path), safe='')}"
        f"&mode={quote(str(client_mode or 'auto'), safe='-_')}"
        f"{extra}"
    )
    return (
        f"vless://{uuid}@{host}:{int(port)}?{query}"
        f"#{quote(str(title), safe='')}"
    )
'''
vless = vless[:pos] + tls_helper + vless[pos:]
compile(vless, vless_path, "exec")
write(vless_path, vless)

exports_path = "app/clients/exports.py"
exports = read(exports_path)
old_import = "from app.xray.sg_panel_vless import reality_tcp_link, xhttp_reality_link\n"
new_import = "from app.xray.sg_panel_vless import reality_tcp_link, xhttp_reality_link, xhttp_tls_link\n"
assert exports.count(old_import) == 1
exports = exports.replace(old_import, new_import, 1)
start = exports.index('    elif profile_id == "xhttp_tls":\n')
end = exports.index('    elif profile_id == "hysteria2":\n', start)
new_export = '''    elif profile_id == "xhttp_tls":\n        domain = _working_tls_domain() or str(state.get("tls_domain") or "")\n        if (\n            not domain\n            or not vless_encryption\n            or "PLACEHOLDER" in vless_encryption.upper()\n        ):\n            body = ""\n        else:\n            body = xhttp_tls_link(\n                uuid=user_id,\n                host=domain,\n                port=443,\n                title=f"{_label(client, device)} · {profile.title}",\n                fingerprint=fingerprint,\n                server_name=domain,\n                path=profile.path,\n                encryption=vless_encryption,\n                client_mode=getattr(profile, "mode", "") or "auto",\n                xmux=(\n                    getattr(profile, "xmux", None)\n                    if getattr(profile, "xmux_enabled", False)\n                    else None\n                ),\n            )\n'''
exports = exports[:start] + new_export + exports[end:]
compile(exports, exports_path, "exec")
write(exports_path, exports)

# ---------------------------------------------------------------------------
# Nginx HTTPS generator always loads the HostD-managed XHTTP-TLS route.
# ---------------------------------------------------------------------------
access_path = "deploy/configure-panel-access.sh"
access = read(access_path)
old_constants = 'XRAY_INTERNAL_PORT="7443"; PLACEHOLDER_TLS_INTERNAL_PORT="7444"\n'
new_constants = old_constants + 'XHTTP_TLS_SNIPPET="/etc/nginx/snippets/sg-gateway-xhttp-tls.conf"\n'
assert access.count(old_constants) == 1
access = access.replace(old_constants, new_constants, 1)

old_dirs = "install -d -m 0755 \"$ACME_ROOT/.well-known/acme-challenge\" \"$PLACEHOLDER_ROOT\" /etc/nginx/sites-available /etc/nginx/sites-enabled /etc/nginx/stream-conf.d /etc/letsencrypt/renewal-hooks/deploy\n"
new_dirs = "install -d -m 0755 \"$ACME_ROOT/.well-known/acme-challenge\" \"$PLACEHOLDER_ROOT\" /etc/nginx/sites-available /etc/nginx/sites-enabled /etc/nginx/stream-conf.d /etc/nginx/snippets /etc/letsencrypt/renewal-hooks/deploy\n"
assert access.count(old_dirs) == 1
access = access.replace(old_dirs, new_dirs, 1)

asset_anchor = 'install -m 0644 "$RESTART_SOURCE" "$PLACEHOLDER_ROOT/restarting.html"\n'
asset_extra = asset_anchor + '''if [[ ! -f "$XHTTP_TLS_SNIPPET" ]]; then\n  printf '%s\\n' '# SG_GATEWAY_XHTTP_TLS_SGPANEL_PARITY_R1' '# XHTTP-TLS disabled until Xray Apply.' > "$XHTTP_TLS_SNIPPET"\n  chmod 0644 "$XHTTP_TLS_SNIPPET"\nfi\n'''
assert access.count(asset_anchor) == 1
access = access.replace(asset_anchor, asset_extra, 1)

old_backup_tail = 'backup_path "$RENEW_HOOK" renewal-hook "$dir"; printf \'%s\' "$dir"; }\n'
new_backup_tail = 'backup_path "$RENEW_HOOK" renewal-hook "$dir"; backup_path "$XHTTP_TLS_SNIPPET" xhttp-tls-snippet "$dir"; printf \'%s\' "$dir"; }\n'
assert access.count(old_backup_tail) == 1
access = access.replace(old_backup_tail, new_backup_tail, 1)
old_restore_tail = 'restore_path "$dir/renewal-hook" "$RENEW_HOOK"; }\n'
new_restore_tail = 'restore_path "$dir/renewal-hook" "$RENEW_HOOK"; restore_path "$dir/xhttp-tls-snippet" "$XHTTP_TLS_SNIPPET"; }\n'
assert access.count(old_restore_tail) == 1
access = access.replace(old_restore_tail, new_restore_tail, 1)

# Only the loopback placeholder TLS listener becomes HTTP/2-capable.
assert access.count("    listen 127.0.0.1:$PLACEHOLDER_TLS_INTERNAL_PORT ssl;\n") == 1
access = access.replace(
    "    listen 127.0.0.1:$PLACEHOLDER_TLS_INTERNAL_PORT ssl;\n",
    "    listen 127.0.0.1:$PLACEHOLDER_TLS_INTERNAL_PORT ssl http2;\n",
    1,
)
placeholder_anchor = '''    ssl_session_tickets off;\n    root $PLACEHOLDER_ROOT;\n    index index.html;\n'''
placeholder_new = '''    ssl_session_tickets off;\n    include /etc/nginx/snippets/sg-gateway-xhttp-tls.conf;\n    root $PLACEHOLDER_ROOT;\n    index index.html;\n'''
assert access.count(placeholder_anchor) >= 1
access = access.replace(placeholder_anchor, placeholder_new, 1)
write(access_path, access)

# Installer rollback owns the new persistent Nginx snippet too.
install = read("install.sh")
managed_anchor = "  etc/nginx/sites-enabled/sg-gateway-acme\n"
assert install.count(managed_anchor) == 1
install = install.replace(
    managed_anchor,
    managed_anchor + "  etc/nginx/snippets/sg-gateway-xhttp-tls.conf\n",
    1,
)
write("install.sh", install)

# ---------------------------------------------------------------------------
# Parity regression tests: assert the product output, not comments.
# ---------------------------------------------------------------------------
write(
    "tests/test_sg_gateway_02206_sgpanel_vless_parity.py",
    rf'''from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
HOSTD = ROOT / "hostd"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HOSTD) not in sys.path:
    sys.path.insert(0, str(HOSTD))

from app.xray import xmux
from app.xray.sg_panel_vless import xhttp_reality_inbound, xhttp_reality_link, xhttp_tls_link
from sg_hostd import client_runtime
from sg_hostd.xhttp_tls_front import (
    INCLUDE_DIRECTIVE,
    MARKER,
    ensure_site_contract,
    render_snippet,
)

SG_PANEL_REFERENCE_COMMIT = "{SG_PANEL_REFERENCE_COMMIT}"
ENCRYPTION = "mlkem768x25519plus.native.0rtt.test.CLIENT"
DECRYPTION = "mlkem768x25519plus.native.600s.test.SERVER"


def test_reference_commit_is_pinned() -> None:
    assert SG_PANEL_REFERENCE_COMMIT == "31f1e137d83c02c64bf1039ebbdaf2b02bbfbeae"
    manifest = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))
    parity = manifest["development_vless_parity"]
    assert parity["reference_commit"] == SG_PANEL_REFERENCE_COMMIT
    assert parity["other_protocols_changed"] is False


def test_reality_xhttp_contract_remains_panel_server_auto_client_stream_one() -> None:
    inbound = xhttp_reality_inbound(
        clients=[{{"id": "11111111-1111-1111-1111-111111111111", "flow": "xtls-rprx-vision"}}],
        port=8444,
        path="/sg-xhttp-reality",
        decryption=DECRYPTION,
        dest="www.bing.com:443",
        server_name="www.bing.com",
        private_key="private",
        short_id="0123456789abcdef",
    )
    assert inbound["settings"]["decryption"] == DECRYPTION
    assert inbound["settings"]["clients"][0]["flow"] == "xtls-rprx-vision"
    assert inbound["streamSettings"]["network"] == "xhttp"
    assert inbound["streamSettings"]["security"] == "reality"
    assert inbound["streamSettings"]["xhttpSettings"]["mode"] == "auto"

    link = xhttp_reality_link(
        uuid="11111111-1111-1111-1111-111111111111",
        host="203.0.113.10",
        port=8444,
        title="Reality",
        fingerprint="firefox",
        server_name="www.bing.com",
        public_key="public",
        short_id="0123456789abcdef",
        path="/sg-xhttp-reality",
        encryption=ENCRYPTION,
    )
    query = parse_qs(urlsplit(link).query)
    assert query["flow"] == ["xtls-rprx-vision"]
    assert query["mode"] == ["stream-one"]
    assert query["encryption"] == [ENCRYPTION]


def test_xmux_presets_stay_exact_current_panel_contract() -> None:
    assert xmux.XMUX_STANDARD_PRESET == {{
        "maxConnections": "2-4",
        "cMaxReuseTimes": "300-600",
        "hMaxRequestTimes": "1000-2000",
        "hMaxReusableSecs": "1200-2400",
        "hKeepAlivePeriod": 600,
    }}
    assert xmux.XMUX_REDUCED_PRESET == {{
        "maxConcurrency": 0,
        "maxConnections": "6",
        "cMaxReuseTimes": 0,
        "hMaxRequestTimes": "600-900",
        "hMaxReusableSecs": "1800-3000",
        "hKeepAlivePeriod": 0,
    }}


def _profiles_for_tls(mode: str = "stream-up") -> dict:
    return {{
        "profiles": [
            SimpleNamespace(id="reality_tcp", enabled=False, ready=False, tls_required=False, port=443, path="", mode=""),
            SimpleNamespace(id="xhttp_reality", enabled=False, ready=False, tls_required=False, port=8444, path="/sg-xhttp-reality", mode="stream-one"),
            SimpleNamespace(id="xhttp_tls", enabled=True, ready=True, tls_required=True, port=8445, path="/sg-xhttp-tls", mode=mode),
            SimpleNamespace(id="hysteria2", enabled=False, ready=False, tls_required=True, port=8446, path="", mode=""),
        ],
        "tls_ready": True,
        "tls_domain": "vpn.example.com",
    }}


def test_xhttp_tls_runtime_matches_panel_local_plain_xray(monkeypatch) -> None:
    monkeypatch.setattr(client_runtime, "_read_env", lambda path: {{
        "SG_GATEWAY_XRAY_PRIVATE_KEY": "private",
        "SG_GATEWAY_XRAY_SHORT_ID": "0123456789abcdef",
        "SG_GATEWAY_VLESS_ENCRYPTION": ENCRYPTION,
        "SG_GATEWAY_VLESS_DECRYPTION": DECRYPTION,
        "SG_GATEWAY_REALITY_SNI": "www.bing.com",
        "SG_GATEWAY_REALITY_TARGET": "www.bing.com:443",
    }})
    monkeypatch.setattr(
        client_runtime,
        "get_connection_settings",
        lambda engine: SimpleNamespace(
            config={{"server_name": "www.bing.com", "target": "www.bing.com:443"}},
            host="203.0.113.10",
            port=443,
        ),
    )
    monkeypatch.setattr(client_runtime, "xray_profiles_overview", lambda: _profiles_for_tls("stream-up"))
    monkeypatch.setattr(
        client_runtime,
        "_sync_xray_tls_material",
        lambda domain: (_ for _ in ()).throw(AssertionError("XHTTP-TLS must not copy TLS into Xray")),
    )
    row = {{
        "client_id": 1,
        "client_name": "Parity",
        "engine_object_id": "11111111-1111-1111-1111-111111111111",
        "config_json": json.dumps({{"uuid": "11111111-1111-1111-1111-111111111111", "profiles": ["xhttp_tls"]}}),
    }}
    payload = json.loads(client_runtime._render_xray_config([row]))
    inbound = next(item for item in payload["inbounds"] if item["tag"] == "sg-vless-xhttp-tls")
    assert inbound["listen"] == "127.0.0.1"
    assert inbound["settings"]["decryption"] == DECRYPTION
    assert inbound["settings"]["clients"][0]["flow"] == "xtls-rprx-vision"
    stream = inbound["streamSettings"]
    assert stream["network"] == "xhttp"
    assert stream["security"] == "none"
    assert "tlsSettings" not in stream
    assert stream["xhttpSettings"] == {{"path": "/sg-xhttp-tls", "mode": "stream-up"}}
    assert stream["sockopt"] == {{"trustedXForwardedFor": ["127.0.0.1"]}}


def test_xhttp_tls_auto_mode_is_server_default_not_forced_field(monkeypatch) -> None:
    monkeypatch.setattr(client_runtime, "_read_env", lambda path: {{
        "SG_GATEWAY_XRAY_PRIVATE_KEY": "private",
        "SG_GATEWAY_XRAY_SHORT_ID": "0123456789abcdef",
        "SG_GATEWAY_VLESS_ENCRYPTION": ENCRYPTION,
        "SG_GATEWAY_VLESS_DECRYPTION": DECRYPTION,
    }})
    monkeypatch.setattr(
        client_runtime,
        "get_connection_settings",
        lambda engine: SimpleNamespace(config={{}}, host="203.0.113.10", port=443),
    )
    monkeypatch.setattr(client_runtime, "xray_profiles_overview", lambda: _profiles_for_tls("auto"))
    row = {{
        "client_id": 1,
        "client_name": "Parity",
        "engine_object_id": "11111111-1111-1111-1111-111111111111",
        "config_json": json.dumps({{"uuid": "11111111-1111-1111-1111-111111111111", "profiles": ["xhttp_tls"]}}),
    }}
    payload = json.loads(client_runtime._render_xray_config([row]))
    inbound = next(item for item in payload["inbounds"] if item["tag"] == "sg-vless-xhttp-tls")
    assert inbound["streamSettings"]["xhttpSettings"] == {{"path": "/sg-xhttp-tls"}}


def test_xhttp_tls_client_uri_matches_panel_fields() -> None:
    link = xhttp_tls_link(
        uuid="11111111-1111-1111-1111-111111111111",
        host="vpn.example.com",
        port=443,
        title="TLS",
        fingerprint="firefox",
        server_name="vpn.example.com",
        path="/sg-xhttp-tls",
        encryption=ENCRYPTION,
        client_mode="stream-up",
        xmux=xmux.XMUX_STANDARD_PRESET,
    )
    parsed = urlsplit(link)
    query = parse_qs(parsed.query)
    assert parsed.hostname == "vpn.example.com"
    assert parsed.port == 443
    assert query["type"] == ["xhttp"]
    assert query["security"] == ["tls"]
    assert query["flow"] == ["xtls-rprx-vision"]
    assert query["sni"] == ["vpn.example.com"]
    assert query["host"] == ["vpn.example.com"]
    assert query["path"] == ["/sg-xhttp-tls"]
    assert query["mode"] == ["stream-up"]
    assert query["encryption"] == [ENCRYPTION]
    assert "alpn" not in query
    extra = json.loads(query["extra"][0])
    assert extra["xmux"] == xmux.XMUX_STANDARD_PRESET


def test_nginx_front_is_panel_style_h2_path_to_local_xray() -> None:
    snippet = render_snippet(enabled=True, path="/sg-xhttp-tls", port=8445)
    assert MARKER in snippet
    assert "location /sg-xhttp-tls/ {" in snippet
    assert "grpc_socket_keepalive on;" in snippet
    assert "grpc_pass grpc://127.0.0.1:8445;" in snippet
    assert "proxy_pass" not in snippet

    site = """server {{
    listen 127.0.0.1:7444 ssl;
    server_name vpn.example.com;
    location / {{ return 404; }}
}}
server {{ listen 63443 ssl; }}
"""
    updated = ensure_site_contract(site, enable_http2=True)
    assert "listen 127.0.0.1:7444 ssl http2;" in updated
    assert updated.count(INCLUDE_DIRECTIVE) == 1
    assert updated.index(INCLUDE_DIRECTIVE) < updated.index("location / {{ return 404; }}")
    assert ensure_site_contract(updated, enable_http2=True) == updated


def test_https_generator_and_updater_carry_parity_contract() -> None:
    access = (ROOT / "deploy/configure-panel-access.sh").read_text(encoding="utf-8")
    assert 'XHTTP_TLS_SNIPPET="/etc/nginx/snippets/sg-gateway-xhttp-tls.conf"' in access
    assert "listen 127.0.0.1:$PLACEHOLDER_TLS_INTERNAL_PORT ssl http2;" in access
    assert "include /etc/nginx/snippets/sg-gateway-xhttp-tls.conf;" in access
    updater = (ROOT / "deploy/update-from-github.sh").read_text(encoding="utf-8")
    assert updater.startswith("#!/usr/bin/env bash\\nset -Eeuo pipefail\\n\\n# The updater replaces /opt/sg-gateway. Never inherit a cwd inside that tree.\\ncd /\\n")
''',
)

# The old 022.05 XMUX test remains valid, but its TLS export must now assert
# the Panel URI fields instead of only mode/extra.
xmux_test_path = "tests/test_sg_gateway_02205_xmux_sgpanel_contract.py"
xmux_test = read(xmux_test_path)
old_tls_test = '''def test_export_rewriter_keeps_tls_client_mode() -> None:\n    from app.clients.exports import _rewrite_xhttp_link\n\n    source = "vless://u@example.com:8445?type=xhttp&security=tls&mode=packet-up#TLS"\n    rewritten = _rewrite_xhttp_link(source, "xhttp_tls", {"xhttp_xmux_mode": "reduced"})\n    query = parse_qs(urlsplit(rewritten).query)\n    assert query["mode"] == ["packet-up"]\n    assert json.loads(query["extra"][0])["xmux"] == xmux.XMUX_REDUCED_PRESET\n'''
new_tls_test = '''def test_export_rewriter_keeps_tls_client_mode() -> None:\n    from app.clients.exports import _rewrite_xhttp_link\n\n    source = "vless://u@example.com:443?type=xhttp&security=tls&host=example.com&mode=packet-up#TLS"\n    rewritten = _rewrite_xhttp_link(source, "xhttp_tls", {"xhttp_xmux_mode": "reduced"})\n    query = parse_qs(urlsplit(rewritten).query)\n    assert query["mode"] == ["packet-up"]\n    assert query["host"] == ["example.com"]\n    assert json.loads(query["extra"][0])["xmux"] == xmux.XMUX_REDUCED_PRESET\n'''
assert xmux_test.count(old_tls_test) == 1
write(xmux_test_path, xmux_test.replace(old_tls_test, new_tls_test, 1))
