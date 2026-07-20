"""Modèle ML local (finition/liant) et mélange de pigments."""
import app as kronocolor_app
from ml_model import recommender


def test_mix_colors_single_pigment_returns_its_own_hex():
    result = kronocolor_app.mix_colors([{"hex": "#9b3a2b", "pct": 100}])
    assert result == "#9b3a2b"


def test_mix_colors_weighted_average():
    # 50/50 white and black should land close to mid-gray.
    result = kronocolor_app.mix_colors([
        {"hex": "#ffffff", "pct": 50},
        {"hex": "#000000", "pct": 50},
    ])
    r = int(result[1:3], 16)
    assert 110 <= r <= 145  # roughly mid-gray, allowing for rounding


def test_recommender_returns_expected_shape():
    result = recommender.predict("Bois", "humide", "#8b5a2b")
    assert set(result.keys()) >= {"finish", "binder", "confidence", "lightness_bucket"}
    assert 0 <= result["confidence"] <= 100
    assert result["finish"] in {"Mat", "Satiné", "Laqué"}


def test_recommender_handles_unknown_surface_gracefully():
    # Falls back to the first known surface rather than raising.
    result = recommender.predict("Surface Inconnue", "humide", "#8b5a2b")
    assert result["finish"]


def test_surface_recommendation_api(client):
    from conftest import register_and_login
    register_and_login(client)
    resp = client.post("/api/surface-recommendation", json={
        "surface": "Bois", "climate": "humide", "hex": "#8b5a2b",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert "finish" in data and "binder" in data
