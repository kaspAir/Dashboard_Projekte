"""Drilldown: Projektliste + Projekt-Detail (Verlauf)."""
from app.data import all_projects


def test_projects_list_ok(client):
    resp = client.get("/projekte")
    assert resp.status_code == 200
    assert "Lebenszyklus" in resp.get_data(as_text=True)


def test_projects_filter_by_bereich(client):
    bereich = all_projects()[0]["business_area"]
    assert client.get("/projekte", query_string={"bereich": bereich}).status_code == 200


def test_project_detail_ok(client):
    key = all_projects()[0]["key"]
    resp = client.get(f"/projekt/{key}")
    assert resp.status_code == 200
    assert "Statusverlauf" in resp.get_data(as_text=True)


def test_project_detail_unknown_404(client):
    assert client.get("/projekt/gibt-es-nicht").status_code == 404
