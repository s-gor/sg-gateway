from __future__ import annotations

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
