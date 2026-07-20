"""Filtres couleur et disponibilité dans la boutique."""
from conftest import register_and_login


def test_color_filter_vert(client):
    register_and_login(client)
    resp = client.get("/client/shop?color=vert").get_data(as_text=True)
    assert "Vert Atlantique" in resp  # #3b5d56
    assert "Laque Carrosserie Rouge Rallye" not in resp  # #b3261e -> rouge


def test_color_filter_rouge(client):
    register_and_login(client)
    resp = client.get("/client/shop?color=rouge").get_data(as_text=True)
    assert "Laque Carrosserie Rouge Rallye" in resp
    assert "Vert Atlantique" not in resp


def test_color_filter_noir(client):
    register_and_login(client)
    resp = client.get("/client/shop?color=noir").get_data(as_text=True)
    assert "Laque Carrosserie Noir Onyx" in resp  # #1b1b1e
    assert "Vert Atlantique" not in resp


def test_in_stock_filter_excludes_depleted_products(client):
    import app as kronocolor_app
    register_and_login(client)
    with kronocolor_app.app.app_context():
        db = kronocolor_app.get_db()
        db.execute("UPDATE products SET stock=0 WHERE id='p6'")
        db.commit()

    resp = client.get("/client/shop?in_stock=1").get_data(as_text=True)
    assert "Laque Carrosserie Rouge Rallye" not in resp

    resp_all = client.get("/client/shop").get_data(as_text=True)
    assert "Laque Carrosserie Rouge Rallye" in resp_all
