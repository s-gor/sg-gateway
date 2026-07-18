from app.help.content import get_topic, list_topics
from app.main import create_app


def _login(client):
    return client.post("/login", data={"password": "secret"})


def test_help_topics_exist():
    topics = list_topics()

    assert get_topic("clients") is not None
    assert len(topics) >= 5


def test_help_page_loads(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SG_GATEWAY_ADMIN_PASSWORD", "secret")
    client = create_app().test_client()
    _login(client)

    response = client.get("/help")

    assert response.status_code == 200
    assert "ÃƒÂÃ‚Â¡ÃƒÂÃ‚Â¿Ãƒâ€˜Ã¢â€šÂ¬ÃƒÂÃ‚Â°ÃƒÂÃ‚Â²ÃƒÂÃ‚ÂºÃƒÂÃ‚Â°" in response.get_data(as_text=True)


def test_help_topic_loads(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SG_GATEWAY_ADMIN_PASSWORD", "secret")
    client = create_app().test_client()
    _login(client)

    response = client.get("/help/clients")

    assert response.status_code == 200
    assert "ÃƒÂÃ…Â¡ÃƒÂÃ‚Â»ÃƒÂÃ‚Â¸ÃƒÂÃ‚ÂµÃƒÂÃ‚Â½Ãƒâ€˜Ã¢â‚¬Å¡Ãƒâ€˜Ã¢â‚¬Â¹" in response.get_data(as_text=True)