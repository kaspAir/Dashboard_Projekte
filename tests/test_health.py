"""Rauchtest: beweist, dass die App startet und der Health-Check antwortet.

Haelt die Regressionstest-Stufe der Pipeline von Beginn an gruen.
"""
from app import create_app


def test_healthz_ok():
    client = create_app().test_client()
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_index_ok():
    client = create_app().test_client()
    assert client.get("/").status_code == 200
