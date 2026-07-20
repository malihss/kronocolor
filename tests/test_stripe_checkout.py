"""Paiement carte réel via Stripe Embedded Checkout (mode test) — le formulaire de
carte s'affiche dans un iframe sur notre propre page (pas de redirection vers
stripe.com), avec repli simulé si Stripe n'est pas configuré."""
import sys
import types

import app as kronocolor_app
from conftest import register_and_login


class _FakeSession:
    def __init__(self, session_id, client_secret, payment_status="paid"):
        self.id = session_id
        self.client_secret = client_secret
        self.payment_status = payment_status


def _install_fake_stripe(monkeypatch, payment_status="paid", raise_on_create=False):
    fake_module = types.ModuleType("stripe")
    created = {}

    class FakeCheckout:
        class Session:
            @staticmethod
            def create(**kwargs):
                if raise_on_create:
                    raise RuntimeError("clé Stripe invalide (simulation de test)")
                created["kwargs"] = kwargs
                created["session"] = _FakeSession("cs_test_123", "cs_test_123_secret_fake")
                return created["session"]

            @staticmethod
            def retrieve(session_id):
                return _FakeSession(session_id, "cs_test_123_secret_fake", payment_status)

    fake_module.checkout = FakeCheckout
    fake_module.api_key = None
    monkeypatch.setitem(sys.modules, "stripe", fake_module)
    return created


def _enable_stripe(monkeypatch):
    monkeypatch.setattr(kronocolor_app, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(kronocolor_app, "STRIPE_PUBLISHABLE_KEY", "pk_test_fake")


def test_checkout_without_stripe_key_uses_simulated_flow(client, monkeypatch):
    monkeypatch.setattr(kronocolor_app, "STRIPE_SECRET_KEY", None)
    register_and_login(client, email="stripe1@test.ma")
    client.post("/client/cart/add/p4")
    resp = client.post("/client/checkout", data={
        "name": "Stripe Test", "email": "stripe1@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert "onfirm".encode() in resp.data  # page order_done ("Commande confirmée")
    assert "(simul".encode() in resp.data  # paiement simulé, pas de vraie transaction Stripe

    with kronocolor_app.app.app_context():
        row = kronocolor_app.get_db().execute(
            "SELECT * FROM orders WHERE customer_email=?", ("stripe1@test.ma",)
        ).fetchone()
    assert row is not None


def test_checkout_missing_publishable_key_falls_back_to_simulated(client, monkeypatch):
    # La clé secrète seule ne suffit pas : le checkout embarqué a besoin de la clé
    # publique côté navigateur — sans elle, on doit rester sur le flux simulé.
    monkeypatch.setattr(kronocolor_app, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(kronocolor_app, "STRIPE_PUBLISHABLE_KEY", None)
    register_and_login(client, email="stripe1b@test.ma")
    client.post("/client/cart/add/p4")
    resp = client.post("/client/checkout", data={
        "name": "Stripe Test1b", "email": "stripe1b@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    }, follow_redirects=True)
    assert "onfirm".encode() in resp.data


def test_checkout_with_stripe_shows_embedded_checkout(client, monkeypatch):
    _enable_stripe(monkeypatch)
    _install_fake_stripe(monkeypatch)
    register_and_login(client, email="stripe2@test.ma")
    client.post("/client/cart/add/p4")

    resp = client.post("/client/checkout", data={
        "name": "Stripe Test2", "email": "stripe2@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    })
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "cs_test_123_secret_fake" in body  # client_secret transmis au JS Stripe
    assert "pk_test_fake" in body
    assert 'id="checkout"' in body

    # Aucune commande ne doit exister tant que le paiement n'est pas confirmé.
    with kronocolor_app.app.app_context():
        row = kronocolor_app.get_db().execute(
            "SELECT * FROM orders WHERE customer_email=?", ("stripe2@test.ma",)
        ).fetchone()
    assert row is None

    with client.session_transaction() as sess:
        assert sess["pending_order"]["email"] == "stripe2@test.ma"
        assert sess["cart"] == {"p4": 1}  # panier conservé jusqu'à confirmation


def test_stripe_paypal_still_uses_simulated_flow(client, monkeypatch):
    # PayPal reste simulé même quand Stripe est configuré pour la carte.
    _enable_stripe(monkeypatch)
    _install_fake_stripe(monkeypatch)
    register_and_login(client, email="stripe3@test.ma")
    client.post("/client/cart/add/p4")
    resp = client.post("/client/checkout", data={
        "name": "Stripe Test3", "email": "stripe3@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "paypal",
    }, follow_redirects=True)
    assert resp.status_code == 200
    with kronocolor_app.app.app_context():
        row = kronocolor_app.get_db().execute(
            "SELECT * FROM orders WHERE customer_email=?", ("stripe3@test.ma",)
        ).fetchone()
    assert row is not None  # commande créée immédiatement (simulé), pas de paiement Stripe


def test_stripe_success_creates_order_after_payment_confirmed(client, monkeypatch):
    _enable_stripe(monkeypatch)
    _install_fake_stripe(monkeypatch, payment_status="paid")
    register_and_login(client, email="stripe4@test.ma")
    client.post("/client/cart/add/p4")
    client.post("/client/checkout", data={
        "name": "Stripe Test4", "email": "stripe4@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    })

    resp = client.get("/client/checkout/stripe/success?session_id=cs_test_123", follow_redirects=True)
    assert resp.status_code == 200
    assert "onfirm".encode() in resp.data
    # Le paiement étant réellement passé par Stripe, la page ne doit pas dire "(simulé)".
    assert "Stripe (mode test)".encode() in resp.data
    assert b"(simul" not in resp.data

    with kronocolor_app.app.app_context():
        row = kronocolor_app.get_db().execute(
            "SELECT * FROM orders WHERE customer_email=?", ("stripe4@test.ma",)
        ).fetchone()
    assert row is not None
    assert row["status"] == "Confirmée"

    with client.session_transaction() as sess:
        assert "pending_order" not in sess
        assert sess["cart"] == {}


def test_stripe_success_rejects_unpaid_session(client, monkeypatch):
    _enable_stripe(monkeypatch)
    _install_fake_stripe(monkeypatch, payment_status="unpaid")
    register_and_login(client, email="stripe5@test.ma")
    client.post("/client/cart/add/p4")
    client.post("/client/checkout", data={
        "name": "Stripe Test5", "email": "stripe5@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    })

    resp = client.get("/client/checkout/stripe/success?session_id=cs_test_123", follow_redirects=True)
    assert "pas été confirmé".encode() in resp.data  # apostrophe HTML-échappée par Jinja (n&#39;a)

    with kronocolor_app.app.app_context():
        row = kronocolor_app.get_db().execute(
            "SELECT * FROM orders WHERE customer_email=?", ("stripe5@test.ma",)
        ).fetchone()
    assert row is None  # aucune commande créée : paiement non confirmé


def test_stripe_cancel_preserves_cart_without_creating_order(client, monkeypatch):
    _enable_stripe(monkeypatch)
    _install_fake_stripe(monkeypatch)
    register_and_login(client, email="stripe6@test.ma")
    client.post("/client/cart/add/p4")
    client.post("/client/checkout", data={
        "name": "Stripe Test6", "email": "stripe6@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    })

    resp = client.get("/client/checkout/stripe/cancel", follow_redirects=True)
    assert resp.status_code == 200
    assert "annul".encode() in resp.data.lower()

    with client.session_transaction() as sess:
        assert "pending_order" not in sess
        assert sess["cart"] == {"p4": 1}


def test_stripe_session_creation_failure_falls_back_gracefully(client, monkeypatch):
    _enable_stripe(monkeypatch)
    _install_fake_stripe(monkeypatch, raise_on_create=True)
    register_and_login(client, email="stripe7@test.ma")
    client.post("/client/cart/add/p4")
    resp = client.post("/client/checkout", data={
        "name": "Stripe Test7", "email": "stripe7@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert "indisponible".encode() in resp.data


def test_checkout_page_shows_stripe_test_card_note_when_enabled(client, monkeypatch):
    _enable_stripe(monkeypatch)
    register_and_login(client, email="stripe8@test.ma")
    client.post("/client/cart/add/p4")
    resp = client.get("/client/checkout").get_data(as_text=True)
    assert "4242 4242 4242 4242" in resp
