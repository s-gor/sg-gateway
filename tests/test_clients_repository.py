from app.clients.repository import count_clients, create_client, list_clients


def test_create_client_with_recommended_access(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    create_client("Irina iPhone", "recommended")

    clients = list_clients()
    assert count_clients() == 1
    assert clients[0].name == "Irina iPhone"
    assert clients[0].awg_status == "pending"
    assert clients[0].xray_status == "pending"