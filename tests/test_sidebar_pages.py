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
        "/system": ["Система", "Проверки состояния", "Память"],
        "/clients": ["Клиенты", "Создать клиента", "Сохранённые клиенты"],
        "/connections": ["Подключения", "AmneziaWG", "Xray Reality"],
        "/routing": ["Маршрутизация", "Маршрут AmneziaWG", "Маршрут Xray Reality"],
        "/maintenance": ["Обслуживание", "Создать резервную копию", "Операции"],
        "/security": ["Безопасность", "Аутентификация", "Сетевая доступность"],
        "/help": ["Справка", "Система", "Маршрутизация"],
    }

    for path, expected_texts in expectations.items():
        response = client.get(path)
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        for text in expected_texts:
            assert text in body
