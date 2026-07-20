"""Inscription, vérification email, connexion, et protection CSRF."""
import re

from conftest import register_and_login


def get_csrf(html):
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return m.group(1) if m else None


def test_register_creates_unverified_user(client):
    resp = client.post("/register", data={
        "role": "client", "name": "Alice", "email": "alice@test.ma",
        "password": "secret123", "confirm": "secret123",
    })
    assert resp.status_code == 200
    assert b"V\xc3\xa9rifiez votre adresse email" in resp.data


def test_login_blocked_before_verification(client):
    client.post("/register", data={
        "role": "client", "name": "Bob", "email": "bob@test.ma",
        "password": "secret123", "confirm": "secret123",
    })
    resp = client.post("/login", data={"role": "client", "email": "bob@test.ma", "password": "secret123"})
    assert "vérifier votre adresse email".encode() in resp.data


def test_full_register_verify_login_flow(client):
    register_and_login(client, email="carol@test.ma", password="secret123", name="Carol")
    resp = client.get("/client", follow_redirects=True)
    assert resp.status_code == 200
    assert "Carol".encode() in resp.data


def test_login_rejects_wrong_password(client):
    register_and_login(client, email="dave@test.ma", password="rightpass1")
    client.get("/logout")
    resp = client.post("/login", data={"role": "client", "email": "dave@test.ma", "password": "wrongpass"})
    assert b"incorrect" in resp.data


def test_login_rejects_role_mismatch(client):
    register_and_login(client, email="erin@test.ma", password="secret123", role="client")
    client.get("/logout")
    resp = client.post("/login", data={"role": "admin", "email": "erin@test.ma", "password": "secret123"})
    assert "enregistré comme".encode() in resp.data


def test_register_admin_requires_valid_code(client):
    resp = client.post("/register", data={
        "role": "admin", "name": "Fake Admin", "email": "fake-admin@test.ma",
        "password": "secret123", "confirm": "secret123", "code": "wrong-code",
    })
    assert "invalide".encode() in resp.data
    resp = client.post("/register", data={
        "role": "admin", "name": "Real Admin", "email": "real-admin@test.ma",
        "password": "secret123", "confirm": "secret123", "code": "kronocolor-admin",
    })
    assert b"V\xc3\xa9rifiez votre adresse email" in resp.data


def test_passwords_are_hashed_not_plaintext(client):
    register_and_login(client, email="hashcheck@test.ma", password="supersecret1")
    with client.application.app_context():
        import app as kronocolor_app
        row = kronocolor_app.get_db().execute(
            "SELECT password_hash FROM users WHERE email=?", ("hashcheck@test.ma",)
        ).fetchone()
    assert row["password_hash"] != "supersecret1"
    assert row["password_hash"].startswith("scrypt:") or row["password_hash"].startswith("pbkdf2:")


def test_csrf_rejects_post_without_token(csrf_client):
    register_and_login(csrf_client, email="csrf1@test.ma", password="secret123")
    resp = csrf_client.post("/client/cart/add/p1", data={})
    assert resp.status_code == 400


def test_csrf_accepts_post_with_valid_token(csrf_client):
    register_and_login(csrf_client, email="csrf2@test.ma", password="secret123")
    shop_page = csrf_client.get("/client/shop")
    token = get_csrf(shop_page.get_data(as_text=True))
    assert token
    resp = csrf_client.post("/client/cart/add/p1", data={"csrf_token": token}, follow_redirects=True)
    assert resp.status_code == 200
    cart_page = csrf_client.get("/client/cart")
    assert b"Oxyde de Merzouga" in cart_page.data
