"""Produits récemment vus et comparateur."""
from conftest import register_and_login


def test_recently_viewed_appears_after_visiting_product(client):
    register_and_login(client)
    client.get("/client/product/p1")
    resp = client.get("/client/shop").get_data(as_text=True)
    assert "VU RÉCEMMENT" in resp
    assert "Oxyde de Merzouga" in resp.split("VU RÉCEMMENT")[1]


def test_recently_viewed_most_recent_first_and_deduped(client):
    register_and_login(client)
    client.get("/client/product/p1")
    client.get("/client/product/p2")
    client.get("/client/product/p1")  # revisite p1 : doit repasser en tête, pas de doublon

    resp = client.get("/client/shop").get_data(as_text=True)
    section = resp.split("VU RÉCEMMENT")[1]
    # Chaque vignette référence le nom deux fois (aria-label + libellé visible) :
    # une seule vignette pour p1 doit donc donner exactement 2 occurrences, pas 4.
    assert section.count("Oxyde de Merzouga") == 2
    pos_p1 = section.index("Oxyde de Merzouga")
    pos_p2 = section.index("Or de Fès")
    assert pos_p1 < pos_p2


def test_recently_viewed_not_shown_with_empty_history(client):
    register_and_login(client)
    resp = client.get("/client/shop").get_data(as_text=True)
    assert "VU RÉCEMMENT" not in resp


def test_toggle_compare_adds_and_removes_product(client):
    register_and_login(client)
    client.post("/client/compare/toggle/p1", follow_redirects=True)
    page = client.get("/client/shop").get_data(as_text=True)
    assert "Comparer (1/3)" in page

    client.post("/client/compare/toggle/p1", follow_redirects=True)
    page2 = client.get("/client/shop").get_data(as_text=True)
    assert "Comparer (" not in page2


def test_compare_page_shows_selected_products(client):
    register_and_login(client)
    client.post("/client/compare/toggle/p1")
    client.post("/client/compare/toggle/p3")
    resp = client.get("/client/compare").get_data(as_text=True)
    assert "Oxyde de Merzouga" in resp
    assert "Vert Atlantique" in resp
    assert "Mat" in resp  # finition de p1
    assert "Silicate" in resp  # liant de p1


def test_compare_max_three_products(client):
    register_and_login(client)
    for pid in ["p1", "p2", "p3"]:
        client.post(f"/client/compare/toggle/{pid}")
    resp = client.post("/client/compare/toggle/p4", follow_redirects=True)
    assert "maximum".encode("utf-8") in resp.data or b"maximum" in resp.data

    compare_page = client.get("/client/compare").get_data(as_text=True)
    assert "Façade Ext" not in compare_page  # p4 non ajouté
    assert compare_page.count("Retirer") == 3


def test_remove_from_compare_page(client):
    register_and_login(client)
    client.post("/client/compare/toggle/p1")
    client.post("/client/compare/toggle/p1")  # toggle off directly via same endpoint
    resp = client.get("/client/compare").get_data(as_text=True)
    assert "Aucun produit" in resp
