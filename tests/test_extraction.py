"""Testet den deterministischen Extraktor an einer committeten Beispiel-PSR."""
import os

from app.extraction import extract_snapshot
from app.mim import load_mim

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "psr_sample.docx")
RAG = {"grün", "gelb", "rot"}
STATUS_FIELDS = [
    "status_overall", "status_schedule", "status_cost", "status_effort",
    "status_results", "status_objectives", "status_risks", "status_governance",
]


def test_extraction_structure_and_provenance():
    prov = extract_snapshot(FIXTURE, load_mim())["provenance"]

    # alle 8 Ampeln erkannt, mit Provenienz und Konfidenz
    for fid in STATUS_FIELDS:
        assert prov[fid]["value"] in RAG, fid
        assert prov[fid]["source"], f"Provenienz fehlt für {fid}"
        assert prov[fid]["confidence"] == 1.0

    # Lebenszyklus normalisiert
    assert prov["lifecycle_state"]["value"] in {"active", "completed", "aborted"}

    # Kosten als Kennzahl mit plan/ist/prognose
    assert set(prov["cost"]["value"]) == {"plan", "ist", "prognose"}

    # Metadaten vorhanden
    assert prov["project_name"]["value"]
    assert prov["org_unit"]["value"]
