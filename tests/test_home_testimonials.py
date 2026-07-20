"""Section témoignages clients sur la page d'accueil."""
from conftest import register_and_login


def test_home_shows_testimonials_section(client):
    register_and_login(client)
    resp = client.get("/client").get_data(as_text=True)
    assert "Ce que disent nos clients" in resp
    assert "★★★★★" in resp


def test_home_testimonials_show_seeded_reviews(client):
    register_and_login(client)
    resp = client.get("/client").get_data(as_text=True)
    # Un avis 3 étoiles ne doit pas apparaître (seuls les >=4 étoiles sont mis en avant)
    assert "Correct mais sechage un peu long" not in resp
