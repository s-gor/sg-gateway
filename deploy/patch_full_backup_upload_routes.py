from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESTORE = "/maintenance/full-backups/restore"
VERIFY = "/maintenance/full-backups/verify"


def _patch_template(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    restore_marker = f"location = {RESTORE} {{"
    verify_marker = f"location = {VERIFY} {{"
    if restore_marker not in text:
        raise RuntimeError(f"{path}: restore upload location missing")

    block_pattern = re.compile(
        r"(?ms)^(?P<block>[ \t]*location = /maintenance/full-backups/restore \{\n"
        r"[ \t]*client_max_body_size 1024m;\n"
        r".*?^[ \t]*\}\n)"
    )
    matches = list(block_pattern.finditer(text))
    if not matches:
        raise RuntimeError(f"{path}: no exact restore 1024m nginx block found")

    for match in reversed(matches):
        restore_block = match.group("block")
        tail = text[match.end() :]
        nearby = tail[: len(restore_block) + 256]
        if verify_marker in nearby:
            continue
        verify_block = restore_block.replace(RESTORE, VERIFY, 1)
        text = text[: match.end()] + verify_block + text[match.end() :]

    if verify_marker not in text:
        raise RuntimeError(f"{path}: verify upload location was not created")
    path.write_text(text, encoding="utf-8", newline="\n")


def _patch_runtime(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    start = text.find("def _ensure_full_restore_upload_nginx() -> None:\n")
    end = text.find("\ndef _probe(\n", start)
    if start < 0 or end < 0:
        raise RuntimeError("full_backup_runtime.py: nginx helper not found")

    helper = '''def _ensure_full_restore_upload_nginx() -> None:\n    # SG_GATEWAY_FULL_BACKUP_UPLOAD_FIX2\n    path = Path("/etc/nginx/sites-available/sg-gateway")\n    if not path.is_file():\n        return\n    body = path.read_text(encoding="utf-8")\n    restore_path = "/maintenance/full-backups/restore"\n    verify_path = "/maintenance/full-backups/verify"\n    restore_marker = f"location = {restore_path} {{"\n    verify_marker = f"location = {verify_path} {{"\n\n    if restore_marker in body and verify_marker in body:\n        return\n\n    def existing_block(endpoint: str) -> str | None:\n        pattern = re.compile(\n            rf"(?ms)^    location = {re.escape(endpoint)} \\{{\\n"\n            r"        client_max_body_size 1024m;\\n"\n            r".*?^    \\}\\n"\n        )\n        match = pattern.search(body)\n        return match.group(0) if match else None\n\n    restore_block = existing_block(restore_path)\n    verify_block = existing_block(verify_path)\n\n    if restore_block and not verify_block:\n        insert_at = body.find(restore_block) + len(restore_block)\n        body = body[:insert_at] + restore_block.replace(restore_path, verify_path, 1) + body[insert_at:]\n    elif verify_block and not restore_block:\n        insert_at = body.find(verify_block)\n        body = body[:insert_at] + verify_block.replace(verify_path, restore_path, 1) + body[insert_at:]\n    elif not restore_block and not verify_block:\n        matches = list(re.finditer(\n            r"(?m)^    location / \\{\\n        proxy_pass http://127\\.0\\.0\\.1:(\\d+);\\n",\n            body,\n        ))\n        if len(matches) != 1:\n            raise RuntimeError(\n                f"Nginx Full Backup proxy location is ambiguous: {len(matches)}"\n            )\n        match = matches[0]\n        port = match.group(1)\n\n        def make_block(endpoint: str) -> str:\n            return (\n                f"    location = {endpoint} {{\\n"\n                "        client_max_body_size 1024m;\\n"\n                f"        proxy_pass http://127.0.0.1:{port};\\n"\n                "        proxy_http_version 1.1;\\n"\n                "        proxy_set_header Host $host;\\n"\n                "        proxy_set_header X-Real-IP $remote_addr;\\n"\n                "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\\n"\n                "        proxy_set_header X-Forwarded-Proto https;\\n"\n                "        proxy_read_timeout 300s;\\n"\n                "        proxy_send_timeout 300s;\\n"\n                "    }\\n"\n            )\n\n        block = (\n            "    # SG_GATEWAY_FULL_BACKUP_UPLOAD_FIX2\\n"\n            + make_block(restore_path)\n            + make_block(verify_path)\n        )\n        body = body[:match.start()] + block + body[match.start():]\n    else:\n        raise RuntimeError("Nginx Full Backup upload locations are malformed")\n\n    path.write_text(body, encoding="utf-8", newline="\\n")\n\n'''

    text = text[:start] + helper + text[end + 1 :]
    compile(text, str(path), "exec")
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    for relative in (
        "deploy/configure-panel-access.sh",
        "install.sh",
    ):
        _patch_template(ROOT / relative)
    _patch_runtime(ROOT / "hostd/sg_hostd/full_backup_runtime.py")

    for relative in (
        "deploy/configure-panel-access.sh",
        "install.sh",
        "hostd/sg_hostd/full_backup_runtime.py",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        if RESTORE not in text or VERIFY not in text:
            raise RuntimeError(f"{relative}: upload contract incomplete")


if __name__ == "__main__":
    main()
