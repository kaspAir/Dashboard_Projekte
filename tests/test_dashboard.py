"""Dashboard-Ansicht (aus der aktiven Datenquelle gerendert)."""
from app.data import dashboard_data


def test_dashboard_route_ok(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Projekt-Dashboard" in body
    assert "Verlässlichkeit" in body


def test_dashboard_data_shape():
    d = dashboard_data()
    assert d["total_active"] > 0
    assert d["by_area"], "Roll-up je Bereich darf nicht leer sein"
    assert all("verdict" in p for p in d["aborted"])
