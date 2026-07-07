"""Testet den Ordner-Connector + die Ingestion (inhaltsbasierte PSR-Erkennung)."""
import os

from app.ingestion import run_ingestion


def test_folder_ingestion_finds_psr():
    cfg = {"type": "folder", "path": os.path.join(os.path.dirname(__file__), "fixtures")}
    result = run_ingestion(cfg)
    assert result["ingested"] >= 1
    rec = result["records"][0]
    assert rec["status"]["gesamt"] in {"grün", "gelb", "rot"}
    assert rec["periode"]            # YYYY-MM aus dem Inhalt abgeleitet
    assert rec["name"]               # Projekt-Identität aus dem Inhalt
