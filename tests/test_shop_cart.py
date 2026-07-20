"""Boutique (filtres, tri, recherche), panier et commande."""
from conftest import register_and_login


def test_shop_lists_all_categories(client):
    register_and_login(client)
    resp = client.get("/client/shop")
    assert resp.status_code == 200
    for cat in [b"Murs", b"Bois", b"Papier peint", b"Outils de peinture"]:
        assert cat in resp.data


def test_shop_category_filter(client):
    register_and_login(client)
    resp = client.get("/client/shop?cat=Bois")
    assert resp.status_code == 200
    assert b"Or de F\xc3\xa8s" in resp.data
    assert b"Papier peint Indigo Chefchaouen" not in resp.data


def test_shop_price_filter(client):
    register_and_login(client)
    resp = client.get("/client/shop?price_range=under_200")
    assert resp.status_code == 200
    assert b"Fa\xc3\xa7ade Ext\xc3\xa9rieure Mat" in resp.data  # 145 MAD
    assert b"Laque Carrosserie Rouge Rallye" not in resp.data  # 780 MAD


def test_shop_search(client):
    register_and_login(client)
    resp = client.get("/client/shop?q=Merzouga")
    assert resp.status_code == 200
    assert b"Oxyde de Merzouga" in resp.data
    assert b"Vernis Teck Dor\xc3\xa9" not in resp.data


def test_shop_sort_price_ascending(client):
    register_and_login(client)
    resp = client.get("/client/shop?cat=Murs&sort=price_asc").get_data(as_text=True)
    pos_facade = resp.index("Façade Extérieure Mat")  # 145 MAD, cheapest in Murs
    pos_oxyde = resp.index("Oxyde de Merzouga")  # 420 MAD
    assert pos_facade < pos_oxyde


def test_add_to_cart_and_view(client):
    register_and_login(client)
    resp = client.post("/client/cart/add/p1", follow_redirects=True)
    assert resp.status_code == 200
    cart = client.get("/client/cart")
    assert b"Oxyde de Merzouga" in cart.data


def test_cart_add_twice_increments_quantity(client):
    register_and_login(client)
    client.post("/client/cart/add/p1")
    client.post("/client/cart/add/p1")
    cart = client.get("/client/cart")
    assert b"2" in cart.data


def test_cart_remove(client):
    register_and_login(client)
    client.post("/client/cart/add/p1")
    client.post("/client/cart/remove/p1")
    cart = client.get("/client/cart")
    assert b"Votre panier est vide" in cart.data


def test_cart_respects_stock_limit(client):
    register_and_login(client)
    # t2 "Rouleau + bac de peinture" has stock=150 by default; requesting far more should clamp.
    client.post("/client/cart/add/t2")
    client.post("/client/cart/update/t2", data={"qty": "99999"})
    cart = client.get("/client/cart")
    assert b"99999" not in cart.data


def test_checkout_creates_order(client):
    register_and_login(client, email="checkout@test.ma")
    client.post("/client/cart/add/p4")  # cheapest product, 145 MAD
    resp = client.post("/client/checkout", data={
        "name": "Checkout Test", "email": "checkout@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"onfirm" in resp.data  # "Confirmée" / order_done page wording

    orders_page = client.get("/client/orders")
    assert b"Fa\xc3\xa7ade Ext\xc3\xa9rieure Mat" in orders_page.data


def test_product_detail_page(client):
    register_and_login(client)
    resp = client.get("/client/product/p1")
    assert resp.status_code == 200
    assert b"Oxyde de Merzouga" in resp.data


def test_toggle_favorite(client):
    register_and_login(client)
    client.post("/client/favorites/toggle/p1", follow_redirects=True)
    favs = client.get("/client/favorites")
    assert b"Oxyde de Merzouga" in favs.data
    client.post("/client/favorites/toggle/p1", follow_redirects=True)
    favs = client.get("/client/favorites")
    assert b"Oxyde de Merzouga" not in favs.data
