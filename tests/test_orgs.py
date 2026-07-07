"""Testet Mandantenfähigkeit: Organisationen-Seite, Scoping, Wechsel."""
from app import create_app
from app.data import dashboard_data
from app.orgs import get_org


def test_orgs_page_ok():
    resp = create_app().test_client().get("/orgs")
    assert resp.status_code == 200
    assert "Mandant" in resp.get_data(as_text=True)


def test_scope_reduces_projects():
    alle = dashboard_data(get_org("llv"))["total_all"]
    scoped = dashboard_data(get_org("demo-infrastruktur"))["total_all"]
    assert 0 < scoped < alle          # gescopter Mandant sieht echt weniger Projekte


def test_switch_sets_cookie():
    resp = create_app().test_client().get("/orgs/wechsel/demo-infrastruktur")
    assert resp.status_code in (301, 302)
    assert "org=demo-infrastruktur" in "".join(
        v for k, v in resp.headers if k.lower() == "set-cookie")
