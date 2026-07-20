"""Avis clients avec photo du résultat."""
import io
import re

from conftest import register_and_login


def _csrf(html):
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def test_review_without_photo_still_works(client):
    register_and_login(client, email="rev1@test.ma")
    page = client.get("/client/product/p1").get_data(as_text=True)
    client.post("/client/product/p1/review", data={
        "csrf_token": _csrf(page), "rating": "5", "message": "Très bonne peinture, sans photo.",
    })
    detail = client.get("/client/product/p1").get_data(as_text=True)
    assert "Très bonne peinture, sans photo." in detail
    assert "review-photo" not in detail.split("Très bonne peinture")[0][-500:]


def test_review_with_valid_photo_is_saved_and_displayed(client):
    register_and_login(client, email="rev2@test.ma")
    page = client.get("/client/product/p1").get_data(as_text=True)
    fake_image = (io.BytesIO(b"\x89PNG\r\n\x1a\nfakecontent"), "mur.png")
    client.post("/client/product/p1/review", data={
        "csrf_token": _csrf(page), "rating": "4", "message": "Le rendu sur mon mur est superbe.",
        "photo": fake_image,
    }, content_type="multipart/form-data")

    detail = client.get("/client/product/p1").get_data(as_text=True)
    assert "Le rendu sur mon mur est superbe." in detail
    assert 'class="review-photo"' in detail
    assert "uploads/review_p1_" in detail


def test_review_with_invalid_photo_extension_is_ignored(client):
    register_and_login(client, email="rev3@test.ma")
    page = client.get("/client/product/p1").get_data(as_text=True)
    bad_file = (io.BytesIO(b"not really an executable, just text"), "malware.exe")
    resp = client.post("/client/product/p1/review", data={
        "csrf_token": _csrf(page), "rating": "3", "message": "Avis avec fichier invalide.",
        "photo": bad_file,
    }, content_type="multipart/form-data", follow_redirects=True)

    assert "format non support".encode("utf-8") in resp.data
    detail = client.get("/client/product/p1").get_data(as_text=True)
    assert "Avis avec fichier invalide." in detail
    assert "review-photo" not in detail.split("Avis avec fichier invalide.")[0][-500:]
