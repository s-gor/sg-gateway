from __future__ import annotations

from pathlib import Path

from flask import Flask, flash, redirect, request, url_for

from app.hostd.client import run_hostd_command
from app.maintenance.full_backups import stage_uploaded_full_backup_for_verification
from app.maintenance.operations import log_operation


VERIFY_ENDPOINT = "verify_full_backup_route"


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


def register_full_backup_verify(app: Flask) -> None:
    if VERIFY_ENDPOINT in app.view_functions:
        return

    def verify_full_backup_route():
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
            # hostd normally removes the verification upload itself. This is a
            # second cleanup path for transport/service failures.
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

    app.add_url_rule(
        "/maintenance/full-backups/verify",
        endpoint=VERIFY_ENDPOINT,
        view_func=verify_full_backup_route,
        methods=["POST"],
    )
