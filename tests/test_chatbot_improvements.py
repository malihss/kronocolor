"""Nouvelles capacités du chatbot : salutations, couleur, suivi de commande,
et correction de l'ordre de priorité domain_answer avant la FAQ générique."""
import app as kronocolor_app
from conftest import register_and_login


def _db():
    return kronocolor_app.get_db()


def test_greeting_gets_friendly_reply(client):
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer("bonjour", _db())
    assert answer is not None
    assert "bonjour" in answer.lower()


def test_thanks_gets_friendly_reply(client):
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer("merci beaucoup", _db())
    assert answer is not None
    assert "plaisir" in answer.lower()


def test_greeting_ignored_when_part_of_longer_question(client):
    # "Bonjour, avez-vous de la peinture pour bois ?" ne doit pas être traité comme
    # une simple salutation — la vraie question (surface bois) doit primer.
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer("Bonjour, vous avez de la peinture pour bois exterieur en hiver ?", _db())
    assert answer is not None
    assert "bonjour" not in answer.lower()


def test_color_family_lookup_returns_matching_products(client):
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer("vous avez du rouge ?", _db())
    assert answer is not None
    assert "rouge" in answer.lower()
    assert "Oxyde de Merzouga" in answer or "Laque Carrosserie Rouge Rallye" in answer


def test_color_family_lookup_for_green(client):
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer("je cherche une teinte verte", _db())
    assert answer is not None
    assert "Vert Atlantique" in answer


def test_order_status_requires_login(client):
    resp = client.post("/api/chatbot", json={"message": "ou est ma commande"})
    data = resp.get_json()
    assert "connectez" in data["reply"].lower()


def test_order_status_no_orders_yet(client):
    register_and_login(client, email="chatorder1@test.ma")
    resp = client.post("/api/chatbot", json={"message": "ou est ma commande"})
    data = resp.get_json()
    assert "aucune commande" in data["reply"].lower()


def test_order_status_reports_latest_order(client):
    register_and_login(client, email="chatorder2@test.ma")
    client.post("/client/cart/add/p4")
    client.post("/client/checkout", data={
        "name": "Chat Order", "email": "chatorder2@test.ma", "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    })
    resp = client.post("/api/chatbot", json={"message": "ou est ma commande ?"})
    data = resp.get_json()
    assert data["source"] == "domain"
    assert "Confirmée" in data["reply"]


def test_specific_product_stock_question_not_shadowed_by_faq(client):
    # Avant la correction : la FAQ interceptait "stock" avant que domain_answer() ne
    # puisse répondre avec le stock exact du produit demandé.
    resp = client.post("/api/chatbot", json={"message": "le Vernis Teck Dore est en stock ?"})
    data = resp.get_json()
    assert data["source"] == "domain"
    assert "Vernis Teck Doré" in data["reply"]
    assert "110" in data["reply"]  # stock par défaut de p5


def test_faq_word_boundary_carte_does_not_match_inside_other_words(client):
    # "cartable" ne doit pas déclencher la FAQ paiement ("carte") via une correspondance
    # de sous-chaîne — la limite de mot doit l'en empêcher.
    resp = client.post("/api/chatbot", json={"message": "j'ai perdu mon cartable"})
    data = resp.get_json()
    assert data.get("source") != "faq"
