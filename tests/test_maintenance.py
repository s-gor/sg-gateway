from app.clients.repository import create_client
from app.maintenance.service import collect_diagnostics


def test_collect_diagnostics(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    create_client("Samsung", "recommended")

    diagnostics = collect_diagnostics()
    labels = {item.label: item.value for item in diagnostics}

    assert labels["Клиенты"] == "1"
    assert labels["Клиенты AmneziaWG"] == "1"
    assert labels["Клиенты Xray"] == "1"
