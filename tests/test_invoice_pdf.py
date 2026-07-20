"""Facture PDF téléchargeable après commande."""
from conftest import register_and_login


def _place_order(client, email):
    client.post("/client/cart/add/p4")
    resp = client.post("/client/checkout", data={
        "name": "Facture Test", "email": email, "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    }, follow_redirects=True).get_data(as_text=True)
    start = resp.index('font-family:monospace">') if 'font-family:monospace">' in resp else None
    return resp


def _order_id(client, email):
    import app as kronocolor_app
    with kronocolor_app.app.app_context():
        row = kronocolor_app.get_db().execute(
            "SELECT id FROM orders WHERE customer_email=? ORDER BY created_at DESC LIMIT 1", (email,)
        ).fetchone()
    return row["id"]


def test_invoice_download_after_checkout(client):
    register_and_login(client, email="invoice1@test.ma")
    _place_order(client, "invoice1@test.ma")
    order_id = _order_id(client, "invoice1@test.ma")

    resp = client.get(f"/client/orders/{order_id}/invoice.pdf")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data[:4] == b"%PDF"


def test_invoice_link_on_order_history_page(client):
    register_and_login(client, email="invoice2@test.ma")
    _place_order(client, "invoice2@test.ma")
    orders_page = client.get("/client/orders").get_data(as_text=True)
    assert "Facture PDF" in orders_page


def test_invoice_denied_for_other_users_order(client):
    register_and_login(client, email="invoice3@test.ma")
    _place_order(client, "invoice3@test.ma")
    order_id = _order_id(client, "invoice3@test.ma")

    register_and_login(client, email="invoice4@test.ma")  # se reconnecte avec un autre compte
    resp = client.get(f"/client/orders/{order_id}/invoice.pdf", follow_redirects=True)
    assert b"Facture introuvable" in resp.data


def test_invoice_reflects_promo_discount(client):
    register_and_login(client, email="invoice5@test.ma")
    client.post("/client/cart/add/p4")
    client.post("/client/checkout/promo", data={"promo_code": "GROS20"})
    client.post("/client/checkout", data={
        "name": "Facture Promo", "email": "invoice5@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    }, follow_redirects=True)
    order_id = _order_id(client, "invoice5@test.ma")

    resp = client.get(f"/client/orders/{order_id}/invoice.pdf")
    assert resp.status_code == 200
    assert resp.data[:4] == b"%PDF"
