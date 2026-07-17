import json

from app.clients.repository import create_client
from app.db import init_db
from app.maintenance.diagnostics import build_diagnostic_report, build_diagnostic_report_json


def test_diagnostic_report_contains_core_sections(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_db()
    create_client("Irina", "recommended")

    report = build_diagnostic_report()

    assert report["service"] == "sg-gateway-panel"
    assert report["summary"]["clients"] == 1
    assert report["connections"]
    assert report["clients"][0]["name"] == "Irina"


def test_diagnostic_report_json_is_valid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_db()

    payload = build_diagnostic_report_json()
    report = json.loads(payload)

    assert report["service"] == "sg-gateway-panel"