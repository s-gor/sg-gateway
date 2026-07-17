from app.main import create_app


def _login(client):
    return client.post("/login", data={"password": "secret"})


def test_post_requires_csrf_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SG_GATEWAY_ADMIN_PASSWORD", "secret")
    app = create_app()
    app.config.update(TESTING=True)

    with app.test_client() as client:
        _login(client)
        response = client.post("/clients", data={"name": "Irina", "access": "recommended"})

    assert response.status_code == 400


def test_post_accepts_csrf_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SG_GATEWAY_ADMIN_PASSWORD", "secret")
    app = create_app()
    app.config.update(TESTING=True)

    with app.test_client() as client:
        _login(client)
        client.get("/clients")
        with client.session_transaction() as session:
            token = session["csrf_token"]
        response = client.post(
            "/clients",
            data={"name": "Irina", "access": "recommended", "csrf_token": token},
        )

    assert response.status_code == 302
