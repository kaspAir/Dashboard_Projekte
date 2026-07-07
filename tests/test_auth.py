"""Login-Gate und Rollen."""
from app import create_app


def test_anonymous_redirected_to_login(anon):
    resp = anon.get("/dashboard")
    assert resp.status_code in (301, 302)
    assert "/login" in resp.headers.get("Location", "")


def test_login_page_open(anon):
    assert anon.get("/login").status_code == 200


def test_healthz_open(anon):
    assert anon.get("/healthz").status_code == 200


def test_super_admin_sees_admin_pages(client):
    assert client.get("/mandanten").status_code == 200
    assert client.get("/users").status_code == 200
    assert client.get("/quellen").status_code == 200
