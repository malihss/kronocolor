"""Accessibilité daltonisme : motifs + nom de la couleur sur les nuances."""
import re

from conftest import register_and_login


def _csrf(html):
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def test_colorblind_mode_off_by_default(client):
    register_and_login(client)
    resp = client.get("/client/shop").get_data(as_text=True)
    assert 'class=""' in resp or 'colorblind-mode' not in resp.split("<body")[1][:50]


def test_toggle_colorblind_mode_adds_body_class(client):
    register_and_login(client)
    shop_page = client.get("/client/shop").get_data(as_text=True)
    client.post("/accessibility/colorblind-mode", data={"csrf_token": _csrf(shop_page)})

    resp = client.get("/client/shop").get_data(as_text=True)
    assert 'body class="colorblind-mode"' in resp


def test_toggle_is_a_flip_flop(client):
    register_and_login(client)
    shop_page = client.get("/client/shop").get_data(as_text=True)
    csrf = _csrf(shop_page)
    client.post("/accessibility/colorblind-mode", data={"csrf_token": csrf})
    on = client.get("/client/shop").get_data(as_text=True)
    assert 'colorblind-mode' in on

    client.post("/accessibility/colorblind-mode", data={"csrf_token": csrf})
    off = client.get("/client/shop").get_data(as_text=True)
    assert 'body class="colorblind-mode"' not in off


def test_color_family_label_present_on_product_tile(client):
    register_and_login(client)
    resp = client.get("/client/product/p1").get_data(as_text=True)
    assert "Couleur : Rouge" in resp  # p1 #9b3a2b -> famille "rouge"


def test_color_family_label_on_shop_filter_dots(client):
    register_and_login(client)
    resp = client.get("/client/shop").get_data(as_text=True)
    assert "Vert" in resp  # libellé de famille sous le rond de couleur vert


def test_toggle_works_via_plain_link_get(client):
    # Le bouton est un simple lien <a> (pas un formulaire POST) : un clic dessus,
    # ou une page mise en cache qui pointe dessus, doit fonctionner en GET sans 405.
    register_and_login(client)
    resp = client.get("/accessibility/colorblind-mode", follow_redirects=True)
    assert resp.status_code == 200
    shop = client.get("/client/shop").get_data(as_text=True)
    assert 'body class="colorblind-mode"' in shop
