"""Quellen-Verwaltung (Seite, sichere Leer-Ingestion)."""
import os

from app.sources.registry import ACTIVE_SOURCE_FILE


def _cleanup():
    if os.path.exists(ACTIVE_SOURCE_FILE):
        os.remove(ACTIVE_SOURCE_FILE)


def test_quellen_page_ok(client):
    resp = client.get("/quellen")
    assert resp.status_code == 200
    assert "Wurzelverzeichnis" in resp.get_data(as_text=True)


def test_quellen_ingest_empty_dir_is_safe(client, tmp_path):
    try:
        resp = client.post("/quellen", data={"action": "ingest", "path": str(tmp_path)})
        assert resp.status_code == 200
        assert "0 PSR gefunden" in resp.get_data(as_text=True)
    finally:
        _cleanup()
