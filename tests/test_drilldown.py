"""Testet das Drilldown: Projektliste + Projekt-Detail (Verlauf)."""
from app import create_app
from app.data import all_projects


def test_projects_list_ok():
    resp = create_app().test_client().get("/projekte")
    assert resp.status_code == 200
    assert "Lebenszyklus" in resp.get_data(as_text=True)


def test_projects_filter_by_bereich():
    projs = all_projects()
    bereich = projs[0]["business_area"]
    resp = create_app().test_client().get("/projekte", query_string={"bereich": bereich})
    assert resp.status_code == 200


def test_project_detail_ok():
    key = all_projects()[0]["key"]
    resp = create_app().test_client().get(f"/projekt/{key}")
    assert resp.status_code == 200
    assert "Statusverlauf" in resp.get_data(as_text=True)


def test_project_detail_unknown_404():
    assert create_app().test_client().get("/projekt/gibt-es-nicht").status_code == 404
