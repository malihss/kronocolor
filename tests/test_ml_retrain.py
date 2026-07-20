"""Ré-entraînement du modèle ML sur les commandes réelles (quiz/diagnostic -> achat)."""
import pytest

from conftest import register_and_login
from ml_model import recommender


@pytest.fixture(autouse=True)
def _reset_recommender():
    # Le recommandeur est un singleton partagé par tout le process ; on repart
    # d'un état propre (règles de base uniquement) avant chaque test de ce fichier.
    recommender.retrain([])
    yield
    recommender.retrain([])


def _do_quiz(client, surface="Mur extérieur", climate="chaud_sec"):
    quiz_page = client.get("/client/quiz").get_data(as_text=True)
    import re
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', quiz_page).group(1)
    client.post("/client/quiz", data={
        "csrf_token": csrf, "surface": surface, "climate": climate,
        "lightness": "moyen", "budget": "standard", "surface_size": "moyenne",
    })


def _checkout(client, email, product_id):
    client.post("/client/cart/add/" + product_id)
    return client.post("/client/checkout", data={
        "name": "ML Test", "email": email, "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    }, follow_redirects=True)


def test_quiz_then_purchase_creates_training_sample(client):
    register_and_login(client, email="ml1@test.ma")
    _do_quiz(client, surface="Mur extérieur", climate="chaud_sec")
    _checkout(client, "ml1@test.ma", "p1")  # Oxyde de Merzouga: Mat / Silicate

    import app as kronocolor_app
    with kronocolor_app.app.app_context():
        rows = kronocolor_app.get_db().execute("SELECT * FROM training_samples").fetchall()
    assert len(rows) == 1
    assert rows[0]["surface"] == "Mur extérieur"
    assert rows[0]["climate"] == "chaud_sec"
    assert rows[0]["finish"] == "Mat"
    assert rows[0]["binder"] == "Silicate"
    assert recommender.n_real_samples == 1


def test_purchase_without_prior_quiz_creates_no_sample(client):
    register_and_login(client, email="ml2@test.ma")
    _checkout(client, "ml2@test.ma", "p1")

    import app as kronocolor_app
    with kronocolor_app.app.app_context():
        rows = kronocolor_app.get_db().execute("SELECT * FROM training_samples").fetchall()
    assert len(rows) == 0
    assert recommender.n_real_samples == 0


def test_purchase_of_non_paint_item_creates_no_sample(client):
    register_and_login(client, email="ml3@test.ma")
    _do_quiz(client)
    _checkout(client, "ml3@test.ma", "w1")  # papier peint : pas de finition/liant

    import app as kronocolor_app
    with kronocolor_app.app.app_context():
        rows = kronocolor_app.get_db().execute("SELECT * FROM training_samples").fetchall()
    assert len(rows) == 0


def test_admin_stats_shows_real_sample_count(client):
    register_and_login(client, email="ml4@test.ma")
    _do_quiz(client)
    _checkout(client, "ml4@test.ma", "p1")

    register_and_login(client, email="ml-admin1@test.ma", name="ML Admin",
                        role="admin", code="kronocolor-admin")
    resp = client.get("/admin").get_data(as_text=True)
    assert "Machine Learning" in resp
    assert "Mur extérieur" in resp


def test_admin_manual_retrain_button(client):
    register_and_login(client, email="ml5@test.ma")
    _do_quiz(client)
    _checkout(client, "ml5@test.ma", "p1")

    register_and_login(client, email="ml-admin2@test.ma", name="ML Admin2",
                        role="admin", code="kronocolor-admin")
    resp = client.post("/admin/ml/retrain", follow_redirects=True)
    assert resp.status_code == 200
    assert "ré-entraîné".encode("utf-8") in resp.data or b"r\xc3\xa9-entra\xc3\xaen\xc3\xa9" in resp.data
