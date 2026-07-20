"""Pont entre le nuancier et le diagnostic IA : lien croisé + teintes proches."""
import re

from conftest import register_and_login


def _csrf(html):
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def test_nuancier_links_to_diagnostic(client):
    register_and_login(client)
    resp = client.get("/client/nuancier").get_data(as_text=True)
    assert "Essayez le mélange" in resp
    assert '/client/diagnostic"' in resp


def test_diagnostic_shows_closest_catalog_products(client):
    register_and_login(client)
    page = client.get("/client/diagnostic").get_data(as_text=True)
    csrf = _csrf(page)

    # p1 "Oxyde de Merzouga" est #9b3a2b ; en mélangeant uniquement ce pigment
    # à 100%, le mélange résultant doit matcher p1 lui-même comme teinte la plus proche.
    resp = client.post("/client/diagnostic", data={
        "csrf_token": csrf, "surface": "Mur extérieur", "climate": "chaud_sec",
        "pct_p1": "100",
    }).get_data(as_text=True)

    assert "TEINTES PROCHES DANS NOTRE CATALOGUE" in resp
    assert "Oxyde de Merzouga" in resp


def test_diagnostic_no_similar_section_without_mix(client):
    register_and_login(client)
    resp = client.get("/client/diagnostic").get_data(as_text=True)
    assert "TEINTES PROCHES DANS NOTRE CATALOGUE" not in resp
