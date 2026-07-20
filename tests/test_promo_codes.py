"""Codes promo à la caisse."""
from conftest import register_and_login


def test_checkout_page_shows_promo_form(client):
    register_and_login(client, email="promo1@test.ma")
    client.post("/client/cart/add/p4")
    resp = client.get("/client/checkout").get_data(as_text=True)
    assert "Code promo" in resp


def test_apply_valid_promo_code_shows_discount(client):
    register_and_login(client, email="promo2@test.ma")
    client.post("/client/cart/add/p4")  # 145 MAD
    client.post("/client/checkout/promo", data={"promo_code": "bienvenue10"})  # insensible à la casse
    resp = client.get("/client/checkout").get_data(as_text=True)
    assert "BIENVENUE10" in resp
    assert "-14 MAD" in resp  # 10% de 145 = 14.5 -> arrondi 14


def test_apply_invalid_promo_code_shows_no_discount(client):
    register_and_login(client, email="promo3@test.ma")
    client.post("/client/cart/add/p4")
    client.post("/client/checkout/promo", data={"promo_code": "FAUXCODE"})
    resp = client.get("/client/checkout").get_data(as_text=True)
    assert "appliqué" not in resp


def test_remove_promo_code(client):
    register_and_login(client, email="promo4@test.ma")
    client.post("/client/cart/add/p4")
    client.post("/client/checkout/promo", data={"promo_code": "GROS20"})
    client.get("/client/checkout")  # consomme le message flash d'application du code
    client.post("/client/checkout/promo/remove")
    resp = client.get("/client/checkout").get_data(as_text=True)
    assert "GROS20" not in resp


def test_order_total_reflects_promo_discount(client):
    register_and_login(client, email="promo5@test.ma")
    client.post("/client/cart/add/p4")  # 145 MAD, zone casa fee=zone fee since <800
    client.post("/client/checkout/promo", data={"promo_code": "GROS20"})  # -20%
    client.post("/client/checkout", data={
        "name": "Promo Test", "email": "promo5@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    }, follow_redirects=True)

    orders_page = client.get("/client/orders").get_data(as_text=True)
    assert "Façade Extérieure Mat" in orders_page

    # Une fois la commande passée, le code promo en session est consommé.
    client.post("/client/cart/add/p4")
    checkout_after = client.get("/client/checkout").get_data(as_text=True)
    assert "GROS20" not in checkout_after
