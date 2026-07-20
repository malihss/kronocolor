"""Échantillons avant achat : pots d'essai 50ml (catalogue + mélange diagnostic)."""
import re

from conftest import register_and_login


def _csrf(html):
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def test_sample_button_shown_for_paint_product(client):
    register_and_login(client)
    resp = client.get("/client/product/p1").get_data(as_text=True)  # Murs (peinture)
    assert "Commander un échantillon 50ml" in resp
    assert "35 MAD" in resp


def test_sample_button_hidden_for_non_paint_product(client):
    register_and_login(client)
    resp = client.get("/client/product/w1").get_data(as_text=True)  # Papier peint
    assert "Commander un échantillon 50ml" not in resp


def test_add_catalog_sample_to_cart(client):
    register_and_login(client)
    client.post("/client/product/p1/sample")
    resp = client.get("/client/cart").get_data(as_text=True)
    assert "Échantillons (50ml)" in resp
    assert "Oxyde de Merzouga — Échantillon 50ml" in resp
    assert "35 MAD" in resp


def test_diagnostic_sample_uses_custom_hex(client):
    register_and_login(client)
    client.post("/client/diagnostic/sample", data={"hex_color": "#a1b2c3"})
    resp = client.get("/client/cart").get_data(as_text=True)
    assert "Mélange personnalisé — Échantillon 50ml" in resp
    assert "#a1b2c3" in resp.lower() or "#A1B2C3" in resp


def test_diagnostic_sample_rejects_invalid_hex(client):
    register_and_login(client)
    resp = client.post("/client/diagnostic/sample", data={"hex_color": "not-a-color"}, follow_redirects=True)
    assert "invalide".encode("utf-8") in resp.data
    cart = client.get("/client/cart").get_data(as_text=True)
    assert "Échantillons" not in cart


def test_sample_max_cap_enforced(client):
    register_and_login(client)
    for i in range(3):
        client.post("/client/diagnostic/sample", data={"hex_color": "#111111"})
    resp = client.post("/client/diagnostic/sample", data={"hex_color": "#222222"}, follow_redirects=True)
    assert "maximum".encode("utf-8") in resp.data

    cart = client.get("/client/cart").get_data(as_text=True)
    assert cart.count("Mélange personnalisé") == 3


def test_remove_sample_from_cart(client):
    register_and_login(client)
    client.post("/client/product/p1/sample")

    import app as kronocolor_app
    with client.session_transaction() as sess:
        sample_id = sess["cart_samples"][0]["id"]
    client.post(f"/client/cart/samples/remove/{sample_id}")

    resp = client.get("/client/cart").get_data(as_text=True)
    assert "Échantillons (50ml)" not in resp


def test_sample_included_in_checkout_and_order_total(client):
    register_and_login(client, email="sample1@test.ma")
    client.post("/client/product/p4/sample")  # 35 MAD, no other item in cart

    checkout_page = client.get("/client/checkout").get_data(as_text=True)
    assert "Façade Extérieure Mat — Échantillon 50ml" in checkout_page

    client.post("/client/checkout", data={
        "name": "Sample Test", "email": "sample1@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    })

    import app as kronocolor_app
    with kronocolor_app.app.app_context():
        row = kronocolor_app.get_db().execute(
            "SELECT * FROM orders WHERE customer_email=?", ("sample1@test.ma",)
        ).fetchone()
    assert row is not None
    import json
    items = json.loads(row["items_json"])
    assert any("Échantillon 50ml" in i["name"] for i in items)

    with client.session_transaction() as sess:
        assert sess.get("cart_samples", []) == []


def test_sample_does_not_affect_product_stock(client):
    register_and_login(client, email="sample2@test.ma")
    client.post("/client/product/p4/sample")
    client.post("/client/checkout", data={
        "name": "Sample Test2", "email": "sample2@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    })

    import app as kronocolor_app
    with kronocolor_app.app.app_context():
        row = kronocolor_app.get_db().execute("SELECT stock FROM products WHERE id='p4'").fetchone()
    assert row["stock"] == 300  # stock de départ inchangé, l'échantillon n'est pas un vrai produit stocké
