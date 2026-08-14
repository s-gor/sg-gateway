from __future__ import annotations

from flask import Flask

from app.maintenance import full_backup_verify_http as verify_http


def test_verify_reuses_existing_restore_upload_endpoint(monkeypatch):
    app = Flask(__name__)

    @app.post("/maintenance/full-backups/restore", endpoint="restore_full_backup_route")
    def restore():
        return "RESTORE"

    monkeypatch.setattr(verify_http, "_verify_uploaded_backup", lambda: "VERIFY")
    verify_http.register_full_backup_verify(app)

    client = app.test_client()
    verify_response = client.post(
        "/maintenance/full-backups/restore",
        data={"backup_action": "verify"},
    )
    restore_response = client.post("/maintenance/full-backups/restore", data={})

    assert verify_response.status_code == 200
    assert verify_response.get_data(as_text=True) == "VERIFY"
    assert restore_response.status_code == 200
    assert restore_response.get_data(as_text=True) == "RESTORE"
    assert "/maintenance/full-backups/verify" not in {rule.rule for rule in app.url_map.iter_rules()}


def test_verify_mux_registration_is_idempotent(monkeypatch):
    app = Flask(__name__)

    @app.post("/maintenance/full-backups/restore", endpoint="restore_full_backup_route")
    def restore():
        return "RESTORE"

    monkeypatch.setattr(verify_http, "_verify_uploaded_backup", lambda: "VERIFY")
    verify_http.register_full_backup_verify(app)
    first = app.view_functions["restore_full_backup_route"]
    verify_http.register_full_backup_verify(app)
    second = app.view_functions["restore_full_backup_route"]

    assert first is second
    assert getattr(second, "_sg_full_backup_verify_mux", False) is True
