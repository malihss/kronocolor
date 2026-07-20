"""Recommandation alternative du modèle ML (deuxième meilleur choix, si assez probable)."""
import pytest

from ml_model import recommender


@pytest.fixture(autouse=True)
def _reset_recommender():
    # Le recommandeur est un singleton partagé par tout le process ; on repart d'un
    # état propre (règles de base uniquement) avant/après chaque test de ce fichier.
    recommender.retrain([])
    yield
    recommender.retrain([])


def test_prediction_always_has_alternative_key():
    result = recommender.predict("Bois", "humide", "#8b5a2b")
    assert "alternative" in result
    assert result["alternative"] is None or isinstance(result["alternative"], dict)


def test_alternative_differs_from_main_recommendation_when_present():
    result = recommender.predict("Mur intérieur", "humide", "#9b7b5a")
    alt = result["alternative"]
    if alt is not None:
        assert {"finish", "binder", "confidence"} <= set(alt.keys())
        assert 15 <= alt["confidence"] <= 100
        assert (alt["finish"], alt["binder"]) != (result["finish"], result["binder"])


def test_alternative_confidence_never_exceeds_main_confidence():
    for surface in ["Mur extérieur", "Bois", "Métal", "Carrosserie auto"]:
        for climate in ["chaud_sec", "froid", "humide", "vent"]:
            result = recommender.predict(surface, climate, "#9b7b5a")
            if result["alternative"]:
                assert result["alternative"]["confidence"] <= result["confidence"]


def test_camera_api_exposes_alternative_field(client):
    from conftest import register_and_login
    register_and_login(client)
    resp = client.post("/api/surface-recommendation", json={
        "surface": "Mur intérieur", "climate": "humide", "hex": "#9b7b5a",
    })
    data = resp.get_json()
    assert "alternative" in data
