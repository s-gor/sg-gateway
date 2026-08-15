from __future__ import annotations

# 022.05 compatibility wrapper.
# The complete pre-VLESS exporter is preserved byte-for-byte in exports_02205.py;
# this module only post-processes XHTTP links to apply the SG-Panel client-side
# XMUX contract without touching any server/runtime logic.

from app.clients import exports_02205 as _base

for _name in dir(_base):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_base, _name)

import json as _json
from urllib.parse import parse_qsl as _parse_qsl, quote as _urlquote, urlencode as _urlencode, urlsplit as _urlsplit, urlunsplit as _urlunsplit

from app.connections.settings import get_connection_settings as _get_connection_settings
from app.xray.xmux import XmuxError as _XmuxError, effective_client_extra as _effective_client_extra


_original_build_xray_profile_link = _base.build_xray_profile_link


def _rewrite_xhttp_link(body: str, profile_id: str, config: dict) -> str:
    if not body or profile_id not in {"xhttp_reality", "xhttp_tls"}:
        return body

    try:
        extra = _effective_client_extra(config)
    except _XmuxError:
        # Never emit a malformed expert payload. The UI blocks invalid values,
        # but restored/legacy databases must fail closed rather than corrupt a link.
        extra = {}

    parts = _urlsplit(body)
    pairs = _parse_qsl(parts.query, keep_blank_values=True)
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
            (
                "extra",
                _json.dumps(extra, ensure_ascii=False, separators=(",", ":")),
            )
        )

    query = _urlencode(
        rewritten,
        doseq=True,
        quote_via=_urlquote,
        safe="-._~",
    )
    return _urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def build_xray_profile_link(client, profile_id: str, device=None):
    result = _original_build_xray_profile_link(client, profile_id, device)
    if profile_id not in {"xhttp_reality", "xhttp_tls"} or not result.body:
        return result
    try:
        config = dict(_get_connection_settings("xray").config)
    except Exception:
        config = {}
    body = _rewrite_xhttp_link(result.body, profile_id, config)
    return _base.ClientExport(
        filename=result.filename,
        media_type=result.media_type,
        body=body,
    )


# Functions defined in the preserved module resolve globals from that module.
# Patch its one XHTTP entry point so build_xray_link/build_protocol_export and
# SG Subscription automatically use the same post-processor.
_base.build_xray_profile_link = build_xray_profile_link

def __getattr__(name: str):
    return getattr(_base, name)
