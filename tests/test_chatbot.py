"""
Tests du moteur de connaissance local du chatbot (domain_answer).

Ces cas couvrent spécifiquement les bugs de collision par sous-chaîne trouvés
et corrigés pendant le développement (ex: "fer" matchait dans "différence",
"mat" matchait dans "climat"/"matière", "peint" matchait dans "peinture") —
ce sont les régressions les plus faciles à réintroduire par erreur.
"""
import app as kronocolor_app


def _db():
    return kronocolor_app.get_db()


def test_word_boundary_fer_does_not_match_difference(client):
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer("quelle est la difference entre mat et satine", _db())
    assert answer is not None
    assert "mat" in answer.lower()
    assert "métal" not in answer.lower() and "époxy" not in answer.lower()


def test_word_boundary_mat_does_not_match_climat_or_matiere(client):
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer("je cherche de la peinture resistante", _db())
    # Should fall through to no domain match (None), not the "mat" finish glossary entry,
    # since "resistante" contains no jargon keyword as a whole word.
    assert answer is None


def test_word_boundary_peint_does_not_match_inside_peinture(client):
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer(
            "vous avez de la peinture pour mur exterieur ?", _db()
        )
    assert answer is not None
    assert "Papier peint" not in answer


def test_product_lookup_by_name(client):
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer("vous avez encore du Oxyde de Merzouga ?", _db())
    assert answer is not None
    assert "Oxyde de Merzouga" in answer
    assert "420" in answer


def test_jargon_takes_priority_over_surface_product_collision(client):
    # "façade" is both a surface keyword and a word inside "Façade Extérieure Mat" —
    # the écaillage question should win over the incidental product-name match.
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer("j'ai de l'ecaillage sur ma facade", _db())
    assert answer is not None
    assert "écaillage" in answer.lower() or "accroche" in answer.lower()
    assert "Façade Extérieure Mat" not in answer


def test_surface_and_climate_gives_technical_recommendation(client):
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer("quelle peinture pour du bois en climat humide", _db())
    assert answer is not None
    assert "finition" in answer.lower()
    assert "liant" in answer.lower()


def test_bare_category_mention_lists_products(client):
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer("vous avez de la peinture carrosserie ?", _db())
    assert answer is not None
    assert "Voiture & Carrosserie" in answer


def test_jargon_plural_and_feminine_forms_match(client):
    with kronocolor_app.app.app_context():
        assert kronocolor_app.domain_answer("ma peinture fait des cloques", _db()) is not None
        assert kronocolor_app.domain_answer("je veux une peinture mate", _db()) is not None
        assert kronocolor_app.domain_answer("il y a de la rouille sur mon metal", _db()) is not None


def test_unrelated_message_returns_none(client):
    with kronocolor_app.app.app_context():
        answer = kronocolor_app.domain_answer("je cherche mes clefs", _db())
    assert answer is None


def test_faq_shipping_keyword_via_http(client):
    resp = client.post("/api/chatbot", json={"message": "quels sont vos delais de livraison"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["source"] == "faq"
    assert "24" in data["reply"]


def test_domain_answer_via_http(client):
    resp = client.post("/api/chatbot", json={"message": "vous avez encore du Oxyde de Merzouga ?"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["source"] == "domain"
    assert "Oxyde de Merzouga" in data["reply"]
