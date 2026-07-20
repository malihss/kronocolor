"""Filtre par couleur dans le nuancier (comme dans la boutique)."""
from conftest import register_and_login


def test_nuancier_shows_color_filter(client):
    register_and_login(client)
    resp = client.get("/client/nuancier").get_data(as_text=True)
    assert "COULEUR" in resp
    assert "Toutes les couleurs" in resp


def test_nuancier_filter_by_vert(client):
    register_and_login(client)
    resp = client.get("/client/nuancier?color=vert").get_data(as_text=True)
    assert "Vert Atlantique" in resp
    assert "Laque Carrosserie Rouge Rallye" not in resp


def test_nuancier_filter_by_rouge(client):
    register_and_login(client)
    resp = client.get("/client/nuancier?color=rouge").get_data(as_text=True)
    assert "Laque Carrosserie Rouge Rallye" in resp
    assert "Vert Atlantique" not in resp
