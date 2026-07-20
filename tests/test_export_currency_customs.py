"""Export international : multi-devise et frais de douane à la caisse."""
from conftest import register_and_login


def test_default_currency_is_mad(client):
    register_and_login(client)
    resp = client.get("/client/shop").get_data(as_text=True)
    assert "420 MAD" in resp  # Oxyde de Merzouga, p1


def test_switch_currency_to_eur_converts_prices(client):
    register_and_login(client)
    home_page = client.get("/client/shop").get_data(as_text=True)
    import re
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', home_page).group(1)
    client.post("/currency/EUR", data={"csrf_token": csrf})

    resp = client.get("/client/shop").get_data(as_text=True)
    assert "€" in resp
    assert "420 MAD" not in resp
    # 420 MAD * 0.092 = 38.64 EUR
    assert "38,64" in resp or "38.64" in resp


def test_switch_currency_to_usd(client):
    register_and_login(client)
    home_page = client.get("/client/shop").get_data(as_text=True)
    import re
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', home_page).group(1)
    client.post("/currency/USD", data={"csrf_token": csrf})
    resp = client.get("/client/shop").get_data(as_text=True)
    assert "$" in resp


def test_checkout_default_country_no_customs_fee(client):
    register_and_login(client, email="customs1@test.ma")
    client.post("/client/cart/add/p4")
    resp = client.get("/client/checkout").get_data(as_text=True)
    assert "Douane estimée" not in resp  # Maroc = 0% de droits de douane


def test_checkout_foreign_country_shows_customs_fee(client):
    register_and_login(client, email="customs2@test.ma")
    client.post("/client/cart/add/p4")  # 145 MAD
    resp = client.get("/client/checkout?country=FR").get_data(as_text=True)
    assert "Douane estimée" in resp
    assert "France" in resp
    # 145 MAD * 20% = 29 MAD
    assert "29 MAD" in resp


def test_order_total_includes_customs_fee(client):
    register_and_login(client, email="customs3@test.ma")
    client.post("/client/cart/add/p4")  # 145 MAD, zone casa fee > 0 since < 800
    client.post("/client/checkout", data={
        "name": "Customs Test", "email": "customs3@test.ma", "address": "1 rue Test",
        "city": "Paris", "phone": "0600000000", "zone": "casa", "payment_method": "card",
        "country": "FR",
    }, follow_redirects=True)

    import app as kronocolor_app
    with kronocolor_app.app.app_context():
        row = kronocolor_app.get_db().execute(
            "SELECT * FROM orders WHERE customer_email=?", ("customs3@test.ma",)
        ).fetchone()
    assert row["delivery_country"] == "FR"
    assert row["customs_fee"] == 29.0  # 145 * 0.20
    assert row["total"] == 145 + 29 + row["shipping_fee"]
