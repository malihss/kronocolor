"""Décrément de stock au checkout, alertes stock bas et export CSV admin."""
from conftest import register_and_login


def _checkout(client, email, product_id, qty):
    client.post("/client/cart/add/" + product_id)
    if qty != 1:
        client.post("/client/cart/update/" + product_id, data={"qty": str(qty)})
    return client.post("/client/checkout", data={
        "name": "Test", "email": email, "address": "1 rue Test",
        "city": "Casablanca", "phone": "0600000000", "zone": "casa", "payment_method": "card",
    }, follow_redirects=True)


def test_checkout_decrements_stock(client):
    register_and_login(client, email="stock1@test.ma")
    # p4 "Façade Extérieure Mat" a un stock par défaut de 300.
    _checkout(client, "stock1@test.ma", "p4", 5)
    detail = client.get("/client/product/p4").get_data(as_text=True)
    assert "295" in detail


def test_low_stock_alert_created_when_crossing_threshold(client):
    register_and_login(client, email="stock2@test.ma")
    # p7 "Laque Carrosserie Noir Onyx" a un stock par défaut de 35 (seuil = 20).
    _checkout(client, "stock2@test.ma", "p7", 20)

    register_and_login(client, email="admin-stock2@test.ma", name="Admin Stock",
                        role="admin", code="kronocolor-admin")
    stats = client.get("/admin").get_data(as_text=True)
    assert "Laque Carrosserie Noir Onyx" in stats
    assert "15 restant" in stats  # 35 - 20 = 15, sous le seuil de 20


def test_stock_stays_above_threshold_no_alert(client):
    register_and_login(client, email="stock3@test.ma")
    # p1 a un stock de 180 ; en retirer 5 reste largement au-dessus du seuil.
    _checkout(client, "stock3@test.ma", "p1", 5)

    register_and_login(client, email="admin-stock3@test.ma", name="Admin Stock2",
                        role="admin", code="kronocolor-admin")
    stats = client.get("/admin").get_data(as_text=True)
    assert "Aucun produit sous le seuil critique" in stats


def test_admin_orders_csv_export(client):
    register_and_login(client, email="stock4@test.ma")
    _checkout(client, "stock4@test.ma", "p4", 1)

    register_and_login(client, email="admin-csv@test.ma", name="Admin CSV",
                        role="admin", code="kronocolor-admin")
    resp = client.get("/admin/orders/export.csv")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    body = resp.get_data(as_text=True)
    assert "Façade Extérieure Mat" in body
    assert "stock4@test.ma" in body


def test_sales_chart_appears_on_stats_page(client):
    register_and_login(client, email="admin-chart@test.ma", name="Admin Chart",
                        role="admin", code="kronocolor-admin")
    resp = client.get("/admin").get_data(as_text=True)
    assert "Ventes des 14 derniers jours" in resp
