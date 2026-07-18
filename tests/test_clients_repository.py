from app.clients.repository import count_clients, create_client, list_clients
from app.maintenance.operations import list_operations


def test_create_client_with_recommended_access(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    create_client("Irina iPhone", "recommended")

    clients = list_clients()
    assert count_clients() == 1
    assert clients[0].name == "Irina iPhone"
    assert clients[0].awg_status == "generated"
    assert clients[0].xray_status == "generated"


def test_create_client_normalizes_name_whitespace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    client_id = create_client("  Irina   iPhone  ", "recommended")

    clients = list_clients()
    assert client_id is not None
    assert clients[0].name == "Irina iPhone"


def test_create_client_rejects_duplicate_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    first_id = create_client("Irina iPhone", "recommended")
    second_id = create_client("  irina   iphone  ", "xray")

    operations = list_operations()
    assert first_id is not None
    assert second_id is None
    assert count_clients() == 1
    assert operations[0].status == "error"
    assert "Rejected duplicate client name" in operations[0].message


def test_create_client_rejects_invalid_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    empty_id = create_client("    ", "recommended")
    long_id = create_client("A" * 81, "recommended")

    assert empty_id is None
    assert long_id is None
    assert count_clients() == 0
