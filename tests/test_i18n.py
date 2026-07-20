"""Multi-langue (FR/EN/AR) et bascule RTL pour l'arabe."""
import re
from conftest import register_and_login


def _csrf(html):
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return m.group(1)


def test_default_language_is_french(client):
    resp = client.get("/login").get_data(as_text=True)
    assert 'lang="fr"' in resp
    assert 'dir="ltr"' in resp
    assert "Bon retour" in resp


def test_switch_to_english(client):
    home = client.get("/login").get_data(as_text=True)
    client.post("/lang/en", data={"csrf_token": _csrf(home)})
    resp = client.get("/login").get_data(as_text=True)
    assert 'lang="en"' in resp
    assert "Welcome back" in resp


def test_switch_to_arabic_enables_rtl(client):
    home = client.get("/login").get_data(as_text=True)
    client.post("/lang/ar", data={"csrf_token": _csrf(home)})
    resp = client.get("/login").get_data(as_text=True)
    assert 'lang="ar"' in resp
    assert 'dir="rtl"' in resp
    assert "مرحبًا بعودتك" in resp


def test_language_persists_across_pages_after_login(client):
    home = client.get("/login").get_data(as_text=True)
    client.post("/lang/en", data={"csrf_token": _csrf(home)})
    register_and_login(client, email="i18n1@test.ma")
    resp = client.get("/client/shop").get_data(as_text=True)
    assert 'lang="en"' in resp
    assert "Shop" in resp


def test_invalid_language_code_ignored(client):
    home = client.get("/login").get_data(as_text=True)
    client.post("/lang/xx", data={"csrf_token": _csrf(home)})
    resp = client.get("/login").get_data(as_text=True)
    assert 'lang="fr"' in resp  # reste sur la langue par défaut
