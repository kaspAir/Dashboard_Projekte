"""Durchführungsauftrag: Seed-Store laden + Ingestion-Routing-Shape."""
from app.da import get_da, load_da
from app.ingestion import run_ingestion


def test_da_seed_store():
    da = load_da("musterstadt")
    assert len(da) == 15                                  # 12 Projekt-DA + 3 Programm-DA
    r = da["M-2024-006"]
    assert r["typ"] == "projekt"
    assert r["budget_soll"] == 920000 and r["aufwand_soll"] == 540
    assert len(r["organisation"]) == 5 and len(r["ressourcen"]) == 5
    assert r["kosten_phasen"]["Realisierung (klassisch)"] == 368000
    p = da["PG-SC"]
    assert p["typ"] == "programm" and p["budget_soll"] == 1600000


def test_get_da():
    assert get_da("musterstadt", "M-2024-006")["name"] == "Verkehrsleitsystem"
    assert get_da("musterstadt", "gibtsnicht") is None


def test_ingestion_routet_da(tmp_path):
    res = run_ingestion({"type": "folder", "path": str(tmp_path)})
    assert "da_records" in res and res["da_ingested"] == 0 and res["ingested"] == 0
