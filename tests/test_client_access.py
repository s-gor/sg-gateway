from app.clients.access import build_access_cards
from app.clients.repository import create_client, get_client


def test_build_access_cards_for_recommended_client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client_id = create_client("Irina iPhone", "recommended")
    client = get_client(client_id)

    cards = build_access_cards(client)
    titles = [card.title for card in cards]

    assert "AmneziaWG" in titles
    assert "Xray Reality" in titles
    assert "SG Client" in titles
    assert all(card.qr_url.startswith(f"/clients/{client_id}/qr/") for card in cards)