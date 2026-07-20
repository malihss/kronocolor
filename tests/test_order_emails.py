"""Emails simulés : confirmation de commande et changements de statut."""
import app as kronocolor_app
from conftest import register_and_login


def test_checkout_sends_confirmation_email(client):
    register_and_login(client, email="email1@test.ma")
    client.post("/client/cart/add/p4")
    client.post("/client/checkout", data={
        "name": "Email Test", "email": "email1@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    })

    with kronocolor_app.app.app_context():
        rows = kronocolor_app.get_db().execute(
            "SELECT * FROM sent_emails WHERE to_email=?", ("email1@test.ma",)
        ).fetchall()
    assert len(rows) == 1
    assert "Confirmation de votre commande" in rows[0]["subject"]


def _place_order(client, email):
    client.post("/client/cart/add/p4")
    client.post("/client/checkout", data={
        "name": "Email Test", "email": email, "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    })
    with kronocolor_app.app.app_context():
        row = kronocolor_app.get_db().execute(
            "SELECT id FROM orders WHERE customer_email=? ORDER BY created_at DESC LIMIT 1", (email,)
        ).fetchone()
    return row["id"]


def test_status_change_to_expediee_sends_email(client):
    register_and_login(client, email="email2@test.ma")
    order_id = _place_order(client, "email2@test.ma")

    register_and_login(client, email="email-admin1@test.ma", name="Email Admin",
                        role="admin", code="kronocolor-admin")
    client.post(f"/admin/orders/{order_id}/status", data={"status": "Expédiée"})

    with kronocolor_app.app.app_context():
        rows = kronocolor_app.get_db().execute(
            "SELECT * FROM sent_emails WHERE order_id=? ORDER BY id", (order_id,)
        ).fetchall()
    subjects = [r["subject"] for r in rows]
    assert any("expédiée" in s.lower() for s in subjects)


def test_status_change_to_livree_sends_email(client):
    register_and_login(client, email="email3@test.ma")
    order_id = _place_order(client, "email3@test.ma")

    register_and_login(client, email="email-admin2@test.ma", name="Email Admin2",
                        role="admin", code="kronocolor-admin")
    client.post(f"/admin/orders/{order_id}/status", data={"status": "Livrée"})

    with kronocolor_app.app.app_context():
        rows = kronocolor_app.get_db().execute(
            "SELECT * FROM sent_emails WHERE order_id=? ORDER BY id", (order_id,)
        ).fetchall()
    subjects = [r["subject"] for r in rows]
    assert any("livrée" in s.lower() for s in subjects)


def test_admin_orders_page_shows_sent_emails(client):
    register_and_login(client, email="email4@test.ma")
    _place_order(client, "email4@test.ma")

    register_and_login(client, email="email-admin3@test.ma", name="Email Admin3",
                        role="admin", code="kronocolor-admin")
    resp = client.get("/admin/orders").get_data(as_text=True)
    assert "Emails envoyés" in resp
    assert "email4@test.ma" in resp
