"""Calculateur de quantité (m² -> litres/rouleaux) sur la fiche produit."""
from conftest import register_and_login


def test_calculator_shown_for_paint_product(client):
    register_and_login(client)
    resp = client.get("/client/product/p1").get_data(as_text=True)  # Murs
    assert "CALCULATEUR DE QUANTITÉ" in resp
    assert 'data-m2-per-unit="10"' in resp
    assert 'data-coats="2"' in resp


def test_calculator_uses_wallpaper_coverage(client):
    register_and_login(client)
    resp = client.get("/client/product/w1").get_data(as_text=True)  # Papier peint
    assert "CALCULATEUR DE QUANTITÉ" in resp
    assert 'data-m2-per-unit="5"' in resp
    assert 'data-coats="1"' in resp


def test_calculator_hidden_for_tools(client):
    register_and_login(client)
    resp = client.get("/client/product/t1").get_data(as_text=True)  # Outils de peinture
    assert "CALCULATEUR DE QUANTITÉ" not in resp


def test_calculator_respects_selected_currency(client):
    import re
    register_and_login(client)
    shop_page = client.get("/client/shop").get_data(as_text=True)
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', shop_page).group(1)
    client.post("/currency/EUR", data={"csrf_token": csrf})

    resp = client.get("/client/product/p1").get_data(as_text=True)
    assert 'data-currency-symbol="€"' in resp
    assert 'data-currency-is-mad="false"' in resp
