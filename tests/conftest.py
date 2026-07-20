"""
Fixtures partagées pour les tests KRONOCOLOR.

Chaque test reçoit une base SQLite temporaire et isolée (jamais la vraie
kronocolor.db du projet) : on monkeypatch `app.DB_PATH` avant d'appeler
`app.init_db()`, ce qui recrée le schéma + les produits par défaut à un
emplacement jetable pour ce test uniquement.
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as kronocolor_app  # noqa: E402


def _csrf_from(html):
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return m.group(1) if m else None


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(kronocolor_app, "DB_PATH", str(tmp_path / "test.db"))
    kronocolor_app.init_db()
    monkeypatch.setattr(kronocolor_app, "_db_initialized", True)
    kronocolor_app.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with kronocolor_app.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def csrf_client(tmp_path, monkeypatch):
    """Comme `client`, mais avec la protection CSRF activée (pour la tester explicitement)."""
    monkeypatch.setattr(kronocolor_app, "DB_PATH", str(tmp_path / "test_csrf.db"))
    kronocolor_app.init_db()
    monkeypatch.setattr(kronocolor_app, "_db_initialized", True)
    kronocolor_app.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
    with kronocolor_app.app.test_client() as test_client:
        yield test_client


def register_and_login(client, email="client@test.ma", password="motdepasse123",
                        name="Client Test", role="client", code=""):
    """Inscrit, vérifie l'email (via le lien simulé) et connecte un utilisateur de test.
    Fonctionne que le client ait la protection CSRF activée ou non."""
    register_page = client.get("/register").get_data(as_text=True)
    client.post("/register", data={
        "csrf_token": _csrf_from(register_page),
        "role": role, "name": name, "email": email,
        "password": password, "confirm": password, "code": code,
    })
    with kronocolor_app.app.app_context():
        row = kronocolor_app.get_db().execute(
            "SELECT verification_token FROM users WHERE email=?", (email,)
        ).fetchone()
    client.get(f"/verify-email/{row['verification_token']}")

    login_page = client.get("/login").get_data(as_text=True)
    client.post("/login", data={
        "csrf_token": _csrf_from(login_page),
        "role": role, "email": email, "password": password,
    })
    return email
