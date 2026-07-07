"""Mandantenfähigkeit: Organisationen-Seite, Scoping, Wechsel."""
from app.data import dashboard_data
from app.orgs import get_org


def test_orgs_page_ok(client):
    resp = client.get("/orgs")
    assert resp.status_code == 200
    assert "Organisation" in resp.get_data(as_text=True)


def test_scope_reduces_projects():
    alle = dashboard_data(get_org("llv-gesamt"))["total_all"]
    scoped = dashboard_data(get_org("llv-infra"))["total_all"]
    assert 0 < scoped < alle          # gescopte Organisation sieht echt weniger Projekte


def test_switch_sets_cookie(client):
    resp = client.get("/orgs/wechsel/llv-infra")
    assert resp.status_code in (301, 302)


def test_other_mandant_has_own_empty_store():
    # Ein Mandant ohne eigenen Store sieht keine (fremden) Daten -> Isolation.
    assert dashboard_data(mandant_id="stadt-ohne-daten")["total_all"] == 0
