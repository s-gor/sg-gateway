from __future__ import annotations

from functools import wraps
from pathlib import Path

from flask import Flask, flash, redirect, request, url_for

from app.hostd.client import run_hostd_command
from app.maintenance.full_backups import stage_uploaded_full_backup_for_verification
from app.maintenance.operations import log_operation


RESTORE_ENDPOINT = "restore_full_backup_route"
VERIFY_ACTION = "verify"


def _format_bytes(value: object) -> str:
    try:
        size = float(max(0, int(value or 0)))
    except (TypeError, ValueError):
        return "0 B"
    units = ("B", "KiB", "MiB", "GiB")
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{int(size)} B"


def _verify_uploaded_backup():
    upload = request.files.get("backup")
    original_name = str(getattr(upload, "filename", "") or "").strip() if upload is not None else ""
    if upload is None or not original_name:
        flash("Выберите файл .sgbackup для проверки", "error")
        return redirect(url_for("maintenance", tab="backups"))

    staged: Path | None = None
    try:
        staged = stage_uploaded_full_backup_for_verification(upload)
        result = run_hostd_command("backup.full.verify", timeout=180)
    except ValueError as exc:
        log_operation("backup.full.verify", f"backup:{original_name}", str(exc), status="error")
        flash(str(exc), "error")
        return redirect(url_for("maintenance", tab="backups"))
    except Exception as exc:
        message = f"Проверка backup не выполнена: {exc}"
        log_operation("backup.full.verify", f"backup:{original_name}", message, status="error")
        flash(message, "error")
        return redirect(url_for("maintenance", tab="backups"))
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)

    if result.status != "ok":
        message = result.message or "Backup не прошёл проверку"
        log_operation("backup.full.verify", f"backup:{original_name}", message, status="error")
        flash(f"Backup НЕ прошёл проверку: {message}", "error")
        return redirect(url_for("maintenance", tab="backups"))

    payload = result.payload or {}
    sha256 = str(payload.get("sha256") or "")
    source_version = str(payload.get("source_version") or "unknown")
    created_at = str(payload.get("created_at") or "не указано")
    tables = int(payload.get("database_tables") or 0)
    database_size = _format_bytes(payload.get("database_size_bytes"))
    certificates = "есть" if payload.get("contains_letsencrypt_certificates") else "нет"
    message = (
        f"Backup исправен: {original_name}. "
        f"SG-Gateway {source_version}; создан {created_at}; "
        f"SQLite: OK, таблиц {tables}, {database_size}; "
        f"сертификаты: {certificates}; SHA-256: {sha256}. "
        "Восстановление не выполнялось."
    )
    log_operation("backup.full.verify", f"backup:{original_name}", message)
    flash(message, "success")
    return redirect(url_for("maintenance", tab="backups"))


def register_full_backup_verify(app: Flask) -> None:
    """Route Verify through the proven Full Restore upload endpoint.

    The 021.12 Nginx contract already allows large .sgbackup uploads only on
    /maintenance/full-backups/restore.  Verification is therefore a submitter
    action on that existing endpoint, not a second upload URL.
    """
    original = app.view_functions.get(RESTORE_ENDPOINT)
    if original is None:
        raise RuntimeError(f"Full Restore endpoint is not registered: {RESTORE_ENDPOINT}")
    if getattr(original, "_sg_full_backup_verify_mux", False):
        return

    @wraps(original)
    def restore_or_verify(*args, **kwargs):
        if request.form.get("backup_action", "").strip().lower() == VERIFY_ACTION:
            return _verify_uploaded_backup()
        return original(*args, **kwargs)

    setattr(restore_or_verify, "_sg_full_backup_verify_mux", True)
    app.view_functions[RESTORE_ENDPOINT] = restore_or_verify
