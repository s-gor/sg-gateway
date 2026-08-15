from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD_BUILD = "DEV-02206-CI-HYGIENE-R1"
NEW_BUILD = "DEV-02206-FULL-BACKUP-VERIFY-UNLIMITED-R1"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Build identity
# ---------------------------------------------------------------------------
assert read("BUILD-ID").strip() == OLD_BUILD
write("BUILD-ID", NEW_BUILD + "\n")

workflow = read(".github/workflows/ci-02206-dev.yml")
assert workflow.count(OLD_BUILD) == 1
write(".github/workflows/ci-02206-dev.yml", workflow.replace(OLD_BUILD, NEW_BUILD))

identity = read("tests/test_sg_gateway_02206_development_identity.py")
assert identity.count(OLD_BUILD) == 2
write("tests/test_sg_gateway_02206_development_identity.py", identity.replace(OLD_BUILD, NEW_BUILD))

# Hygiene is a historical feature contract, not the forever-current BUILD-ID.
hygiene_path = "tests/test_sg_gateway_02206_ci_hygiene.py"
hygiene = read(hygiene_path)
old_hygiene = '''def test_ci_hygiene_is_declared_non_runtime() -> None:\n    assert _text("BUILD-ID").strip() == "DEV-02206-CI-HYGIENE-R1"\n    manifest = json.loads(_text("release-manifest.json"))\n    assert manifest["build"] == "DEV-02206-CI-HYGIENE-R1"\n    hygiene = manifest["development_hygiene"]\n'''
new_hygiene = '''def test_ci_hygiene_is_declared_non_runtime() -> None:\n    manifest = json.loads(_text("release-manifest.json"))\n    hygiene = manifest["development_hygiene"]\n'''
assert hygiene.count(old_hygiene) == 1
write(hygiene_path, hygiene.replace(old_hygiene, new_hygiene, 1))

# ---------------------------------------------------------------------------
# Restore the Verify button into the PRODUCT template, not just the patcher.
# ---------------------------------------------------------------------------
patcher_path = ROOT / "deploy" / "patch_full_backup_verify_ui.py"
spec = importlib.util.spec_from_file_location("patch_full_backup_verify_ui", patcher_path)
assert spec is not None and spec.loader is not None
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)

template_path = "app/web/templates/maintenance.html"
template = patcher.patch_text(read(template_path))
old_picker = "Нажмите, чтобы выбрать файл · максимум 512 MiB"
new_picker = "Нажмите, чтобы выбрать файл · без ограничения размера"
assert template.count(old_picker) == 1
template = template.replace(old_picker, new_picker, 1)
assert template.count("data-sg-full-verify-button") == 2
assert 'name="backup_action" value="verify"' in template
assert "Проверить backup" in template
assert "Проверка ничего не меняет." in template
assert "готов к проверке / восстановлению" in template
assert "verifyButton.addEventListener(\"click\", () => {" in template
assert "form.dataset.sgConfirmBypass = \"1\"" in template
assert "максимум 512 MiB" not in template
write(template_path, template)

# ---------------------------------------------------------------------------
# Remove the Python-side 512 MiB hard stop.
# ---------------------------------------------------------------------------
full_backups_path = "app/maintenance/full_backups.py"
full_backups = read(full_backups_path)
assert "MAX_UPLOAD_BYTES = 512 * 1024 * 1024\n" in full_backups
full_backups = full_backups.replace("MAX_UPLOAD_BYTES = 512 * 1024 * 1024\n", "", 1)
limit_block = '''            total += len(chunk)\n            if total > MAX_UPLOAD_BYTES:\n                handle.close()\n                temporary.unlink(missing_ok=True)\n                raise ValueError("Полный backup больше допустимых 512 MiB")\n            handle.write(chunk)\n'''
unlimited_block = '''            total += len(chunk)\n            handle.write(chunk)\n'''
assert full_backups.count(limit_block) == 1
full_backups = full_backups.replace(limit_block, unlimited_block, 1)
assert "MAX_UPLOAD_BYTES" not in full_backups
assert "допустимых 512 MiB" not in full_backups
write(full_backups_path, full_backups)

# ---------------------------------------------------------------------------
# New installations / panel access rewrites: no artificial request-size cap.
# Nginx uses client_max_body_size 0 for unlimited body size.
# ---------------------------------------------------------------------------
for relative, expected in (
    ("install.sh", 2),
    ("deploy/configure-panel-access.sh", 2),
):
    body = read(relative)
    assert body.count("client_max_body_size 1024m;") == expected, (relative, body.count("client_max_body_size 1024m;"))
    body = body.replace("client_max_body_size 1024m;", "client_max_body_size 0;")
    assert body.count("client_max_body_size 0;") >= expected
    write(relative, body)

# ---------------------------------------------------------------------------
# Hostd: normalize old 1024m live upload locations to unlimited, and create
# missing exact locations with the unlimited contract.
# ---------------------------------------------------------------------------
runtime_path = "hostd/sg_hostd/full_backup_runtime.py"
runtime = read(runtime_path)
start = runtime.index("def _ensure_full_restore_upload_nginx() -> None:\n")
end = runtime.index("\ndef _probe(\n", start)
new_runtime_helper = r'''def _normalize_full_backup_upload_nginx_text(body: str) -> str:
    # SG_GATEWAY_FULL_BACKUP_UPLOAD_UNLIMITED_V1
    restore_path = "/maintenance/full-backups/restore"
    verify_path = "/maintenance/full-backups/verify"

    def location_pattern(endpoint: str) -> re.Pattern[str]:
        return re.compile(
            rf"(?ms)^    location = {re.escape(endpoint)} \{{\n.*?^    \}}\n"
        )

    def existing_block(endpoint: str) -> str | None:
        match = location_pattern(endpoint).search(body)
        return match.group(0) if match else None

    restore_block = existing_block(restore_path)
    verify_block = existing_block(verify_path)

    if restore_block and not verify_block:
        insert_at = body.find(restore_block) + len(restore_block)
        body = body[:insert_at] + restore_block.replace(restore_path, verify_path, 1) + body[insert_at:]
    elif verify_block and not restore_block:
        insert_at = body.find(verify_block)
        body = body[:insert_at] + verify_block.replace(verify_path, restore_path, 1) + body[insert_at:]
    elif not restore_block and not verify_block:
        matches = list(re.finditer(
            r"(?m)^    location / \{\n        proxy_pass http://127\.0\.0\.1:(\d+);\n",
            body,
        ))
        if len(matches) != 1:
            raise RuntimeError(
                f"Nginx Full Backup proxy location is ambiguous: {len(matches)}"
            )
        match = matches[0]
        port = match.group(1)

        def make_block(endpoint: str) -> str:
            return (
                f"    location = {endpoint} {{\n"
                "        client_max_body_size 0;\n"
                f"        proxy_pass http://127.0.0.1:{port};\n"
                "        proxy_http_version 1.1;\n"
                "        proxy_set_header Host $host;\n"
                "        proxy_set_header X-Real-IP $remote_addr;\n"
                "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
                "        proxy_set_header X-Forwarded-Proto https;\n"
                "        proxy_read_timeout 300s;\n"
                "        proxy_send_timeout 300s;\n"
                "    }\n"
            )

        block = (
            "    # SG_GATEWAY_FULL_BACKUP_UPLOAD_UNLIMITED_V1\n"
            + make_block(restore_path)
            + make_block(verify_path)
        )
        body = body[:match.start()] + block + body[match.start():]

    for endpoint in (restore_path, verify_path):
        pattern = location_pattern(endpoint)
        match = pattern.search(body)
        if match is None:
            raise RuntimeError(f"Nginx Full Backup upload location is missing: {endpoint}")
        block = match.group(0)
        directive = re.compile(r"(?m)^(?P<indent>\s*)client_max_body_size\s+[^;]+;\s*$")
        if directive.search(block):
            normalized = directive.sub(
                lambda item: f"{item.group('indent')}client_max_body_size 0;",
                block,
                count=1,
            )
        else:
            first_line_end = block.find("\n") + 1
            normalized = block[:first_line_end] + "        client_max_body_size 0;\n" + block[first_line_end:]
        body = body[:match.start()] + normalized + body[match.end():]

    return body


def _ensure_full_restore_upload_nginx() -> None:
    path = Path("/etc/nginx/sites-available/sg-gateway")
    if not path.is_file():
        return
    body = path.read_text(encoding="utf-8")
    normalized = _normalize_full_backup_upload_nginx_text(body)
    if normalized != body:
        path.write_text(normalized, encoding="utf-8", newline="\n")
'''
runtime = runtime[:start] + new_runtime_helper + runtime[end:]
compile(runtime, runtime_path, "exec")
assert "client_max_body_size 1024m;" not in runtime
assert "client_max_body_size 0;" in runtime
assert "_normalize_full_backup_upload_nginx_text" in runtime
write(runtime_path, runtime)

# ---------------------------------------------------------------------------
# Safe panel update: migrate ONLY this upload-size contract on existing hosts.
# The updater already has a full safety backup; verify the final site equals
# the exact normalization of the pre-update site before declaring success.
# ---------------------------------------------------------------------------
updater_path = "deploy/update-from-github.sh"
updater = read(updater_path)
backup_anchor = '''  fingerprint_paths \\
    /etc/nginx/nginx.conf \\
    /etc/nginx/sites-available/sg-gateway \\
    /etc/nginx/sites-enabled/sg-gateway \\
    /etc/nginx/stream-conf.d/sg-gateway-443.conf \\
    > "$BACKUP_DIR/nginx-before.sha256"\n\n'''
backup_extra = backup_anchor + '''  fingerprint_paths \\
    /etc/nginx/nginx.conf \\
    /etc/nginx/sites-enabled/sg-gateway \\
    /etc/nginx/stream-conf.d/sg-gateway-443.conf \\
    > "$BACKUP_DIR/nginx-static-before.sha256"\n  if [[ -f /etc/nginx/sites-available/sg-gateway ]]; then\n    cp -a /etc/nginx/sites-available/sg-gateway "$BACKUP_DIR/nginx-site-before.conf"\n  fi\n\n'''
assert updater.count(backup_anchor) == 1
updater = updater.replace(backup_anchor, backup_extra, 1)

runtime_check_anchor = '''  runuser -u sg-gateway -- "$PREFIX/.venv/bin/python" -c \\
    'import flask, jinja2, waitress; print("Python runtime: OK")'\n}\n\nrestart_panel() {\n'''
runtime_check_replacement = '''  runuser -u sg-gateway -- "$PREFIX/.venv/bin/python" -c \\
    'import flask, jinja2, waitress; print("Python runtime: OK")'\n\n  # 022.06: remove the old Full Backup upload cap using the deployed,\n  # unit-tested normalizer. This is the only server config migration allowed\n  # by the panel-only updater in this release.\n  PYTHONPATH="$PREFIX/hostd" "$PREFIX/.venv/bin/python" -B - <<'PYFULLBACKUPUPLOAD'\nfrom sg_hostd.full_backup_runtime import _ensure_full_restore_upload_nginx\n_ensure_full_restore_upload_nginx()\nprint("Full Backup upload contract: unlimited")\nPYFULLBACKUPUPLOAD\n  nginx -t >/dev/null\n  systemctl reload nginx.service\n}\n\nrestart_panel() {\n'''
assert updater.count(runtime_check_anchor) == 1
updater = updater.replace(runtime_check_anchor, runtime_check_replacement, 1)

verify_old = '''  before="$(cat "$BACKUP_DIR/nginx-before.sha256")"\n  after="$(fingerprint_paths \\
    /etc/nginx/nginx.conf \\
    /etc/nginx/sites-available/sg-gateway \\
    /etc/nginx/sites-enabled/sg-gateway \\
    /etc/nginx/stream-conf.d/sg-gateway-443.conf)"\n  [[ "$before" == "$after" ]] || fail "Nginx configuration changed during Update"\n\n'''
verify_new = '''  before="$(cat "$BACKUP_DIR/nginx-static-before.sha256")"\n  after="$(fingerprint_paths \\
    /etc/nginx/nginx.conf \\
    /etc/nginx/sites-enabled/sg-gateway \\
    /etc/nginx/stream-conf.d/sg-gateway-443.conf)"\n  [[ "$before" == "$after" ]] || fail "Nginx static configuration changed during Update"\n\n  if [[ -f "$BACKUP_DIR/nginx-site-before.conf" ]]; then\n    PYTHONPATH="$PREFIX/hostd" "$PREFIX/.venv/bin/python" -B - \\
      "$BACKUP_DIR/nginx-site-before.conf" /etc/nginx/sites-available/sg-gateway <<'PYVERIFYUPLOADCONTRACT'\nimport sys\nfrom pathlib import Path\nfrom sg_hostd.full_backup_runtime import _normalize_full_backup_upload_nginx_text\n\nbefore_path = Path(sys.argv[1])\nafter_path = Path(sys.argv[2])\nexpected = _normalize_full_backup_upload_nginx_text(before_path.read_text(encoding="utf-8"))\nactual = after_path.read_text(encoding="utf-8")\nif actual != expected:\n    raise SystemExit("Full Backup upload contract changed outside the expected normalization")\nprint("Full Backup upload contract migration: OK")\nPYVERIFYUPLOADCONTRACT\n  fi\n\n'''
assert updater.count(verify_old) == 1
updater = updater.replace(verify_old, verify_new, 1)

old_final = "  printf '[SG-Gateway Update] Nginx/Certbot/Let'\\''s Encrypt/cores were not modified.\\n'\n"
new_final = "  printf '[SG-Gateway Update] Full Backup upload-size contract normalized; certificates/cores were not modified.\\n'\n"
assert updater.count(old_final) == 1
updater = updater.replace(old_final, new_final, 1)
write(updater_path, updater)

# ---------------------------------------------------------------------------
# Manifest / changelog
# ---------------------------------------------------------------------------
manifest_path = ROOT / "release-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
assert manifest["version"] == "0.1.0-022.06"
assert manifest["build"] == OLD_BUILD
assert manifest["channel"] == "dev-02206"
manifest["build"] = NEW_BUILD
manifest["portable_full_backup"].pop("max_upload_mib", None)
manifest["portable_full_backup"]["upload_size_limit"] = "unlimited"
manifest["portable_full_backup"]["verify_button_integrated"] = True
manifest["development_fix"] = {
    "id": "full-backup-verify-unlimited-r1",
    "verify_button": "integrated-in-maintenance-template",
    "upload_size_limit": "unlimited",
    "legacy_upload_limit_migration": True,
    "panel_update_migration_scope": "full-backup-upload-contract-only",
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

changelog = read("CHANGELOG.md")
anchor = "- CI hygiene R1 removes the inherited 022.05 development workflow and the completed Full Backup patch generator/workflow from dev-02206; runtime behavior is unchanged.\n"
assert changelog.count(anchor) == 1
write(
    "CHANGELOG.md",
    changelog.replace(
        anchor,
        anchor
        + "- Full Backup Verify/Unlimited R1 integrates the Verify button into Maintenance and removes the artificial .sgbackup upload-size cap, including migration of the previous upload contract on safe panel update.\n",
        1,
    ),
)

# ---------------------------------------------------------------------------
# Regression tests must check the real product tree, not only patch generators.
# ---------------------------------------------------------------------------
ui_test_path = "tests/test_sg_gateway_02205_full_backup_verify_ui.py"
ui_test = read(ui_test_path)
insert = '''\n\ndef test_full_backup_verify_button_is_integrated_in_product_template():\n    template = TEMPLATE_PATH.read_text(encoding="utf-8")\n\n    assert template.count("data-sg-full-verify-button") == 2\n    assert 'name="backup_action" value="verify"' in template\n    assert "Проверить backup" in template\n    assert "Проверка ничего не меняет." in template\n    assert "готов к проверке / восстановлению" in template\n    assert 'verifyButton.addEventListener("click", () => {' in template\n    assert 'form.dataset.sgConfirmBypass = "1"' in template\n    assert "максимум 512 MiB" not in template\n    assert "без ограничения размера" in template\n'''
marker = "\ndef test_full_backup_verify_ui_patch_is_complete_and_idempotent():\n"
assert marker in ui_test
ui_test = ui_test.replace(marker, insert + marker, 1)
write(ui_test_path, ui_test)

write(
    "tests/test_sg_gateway_02206_full_backup_verify_unlimited.py",
    r'''from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOSTD_ROOT = ROOT / "hostd"
if str(HOSTD_ROOT) not in sys.path:
    sys.path.insert(0, str(HOSTD_ROOT))

from sg_hostd.full_backup_runtime import _normalize_full_backup_upload_nginx_text


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_no_python_or_ui_512mib_upload_cap_remains() -> None:
    upload = _text("app/maintenance/full_backups.py")
    template = _text("app/web/templates/maintenance.html")
    assert "MAX_UPLOAD_BYTES" not in upload
    assert "допустимых 512 MiB" not in upload
    assert "максимум 512 MiB" not in template
    assert "без ограничения размера" in template


def test_install_and_panel_access_templates_use_unlimited_upload_contract() -> None:
    for path in ("install.sh", "deploy/configure-panel-access.sh"):
        body = _text(path)
        assert "client_max_body_size 1024m;" not in body
        assert body.count("client_max_body_size 0;") >= 2
        assert "/maintenance/full-backups/restore" in body
        assert "/maintenance/full-backups/verify" in body


def test_live_upload_contract_normalizer_migrates_old_1024m_blocks() -> None:
    old = """server {
    listen 63443;
    location = /maintenance/full-backups/restore {
        client_max_body_size 1024m;
        proxy_pass http://127.0.0.1:18080;
    }
    location = /maintenance/full-backups/verify {
        client_max_body_size 1024m;
        proxy_pass http://127.0.0.1:18080;
    }
    location / {
        proxy_pass http://127.0.0.1:18080;
    }
}
"""
    normalized = _normalize_full_backup_upload_nginx_text(old)
    assert "client_max_body_size 1024m;" not in normalized
    assert normalized.count("client_max_body_size 0;") == 2
    assert _normalize_full_backup_upload_nginx_text(normalized) == normalized


def test_live_upload_contract_normalizer_can_create_missing_exact_blocks() -> None:
    old = """server {
    listen 63443;
    location / {
        proxy_pass http://127.0.0.1:18080;
    }
}
"""
    normalized = _normalize_full_backup_upload_nginx_text(old)
    assert "/maintenance/full-backups/restore" in normalized
    assert "/maintenance/full-backups/verify" in normalized
    assert normalized.count("client_max_body_size 0;") == 2


def test_safe_updater_applies_and_verifies_only_upload_contract_migration() -> None:
    updater = _text("deploy/update-from-github.sh")
    assert "_ensure_full_restore_upload_nginx" in updater
    assert "nginx-static-before.sha256" in updater
    assert "nginx-site-before.conf" in updater
    assert "_normalize_full_backup_upload_nginx_text" in updater
    assert "Full Backup upload contract migration: OK" in updater
    assert "Full Backup upload contract changed outside the expected normalization" in updater


def test_02206_manifest_declares_integrated_verify_and_unlimited_upload() -> None:
    manifest = json.loads(_text("release-manifest.json"))
    assert manifest["build"] == "DEV-02206-FULL-BACKUP-VERIFY-UNLIMITED-R1"
    full = manifest["portable_full_backup"]
    assert "max_upload_mib" not in full
    assert full["upload_size_limit"] == "unlimited"
    assert full["verify_button_integrated"] is True
    fix = manifest["development_fix"]
    assert fix["id"] == "full-backup-verify-unlimited-r1"
    assert fix["legacy_upload_limit_migration"] is True
    assert fix["panel_update_migration_scope"] == "full-backup-upload-contract-only"
''',
)
