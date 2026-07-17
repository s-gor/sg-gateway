from app.help.content import get_topic, list_topics
from app.main import create_app


def test_help_topics_exist():
    topics = list_topics()

    assert get_topic("clients") is not None
    assert len(topics) >= 5


def test_help_page_loads(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = create_app().test_client()

    response = client.get("/help")

    assert response.status_code == 200
    assert "Ð¡Ð¿Ñ€Ð°Ð²ÐºÐ°" in response.get_data(as_text=True)


def test_help_topic_loads(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = create_app().test_client()

    response = client.get("/help/clients")

    assert response.status_code == 200
    assert "ÐšÐ»Ð¸ÐµÐ½Ñ‚Ñ‹" in response.get_data(as_text=True)