"""Health-Endpoint und Startseite."""


def test_healthz_ok(anon):
    resp = anon.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_index_ok(client):
    assert client.get("/").status_code == 200
