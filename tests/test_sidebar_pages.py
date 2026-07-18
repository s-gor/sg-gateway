from app.main import create_app


def _login(client):
    return client.post("/login", data={"password": "secret"})


def test_sidebar_links_are_english(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SG_GATEWAY_ADMIN_PASSWORD", "secret")
    client = create_app().test_client()
    _login(client)

    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    for href, label in [
        ("/system", "System"),
        ("/clients", "Clients"),
        ("/connections", "Connections"),
        ("/routing", "Routing"),
        ("/maintenance", "Maintenance"),
        ("/security", "Security"),
        ("/help", "Help"),
    ]:
        assert f'href="{href}"' in body
        assert f">{label}</a>" in body


def test_sidebar_pages_load_real_content(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SG_GATEWAY_ADMIN_PASSWORD", "secret")
    client = create_app().test_client()
    _login(client)

    expectations = {
        "/system": ["System", "Health checks", "Resource usage"],
        "/clients": ["Clients", "Create client", "Stored clients"],
        "/connections": ["Connections", "AmneziaWG", "Xray Reality"],
        "/routing": ["Routing", "AmneziaWG route", "Xray Reality route"],
        "/maintenance": ["Maintenance", "Create backup", "Operation"],
        "/security": ["Security", "Authentication", "Network exposure"],
        "/help": ["Help", "System", "Routing"],
    }

    for path, expected_texts in expectations.items():
        response = client.get(path)
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        for text in expected_texts:
            assert text in body
