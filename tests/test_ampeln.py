"""Ampel-Drilldown: eigener Verlauf, methodengerechte Belege + Fundstelle,
und Programm-Roll-up – geprüft an den Musterstadt-Seed-Daten."""
from app.data import dashboard_data, project_detail


def _ampel(d, key):
    return next(a for a in d["ampeln"] if a["key"] == key)


def test_drilldown_klassisch_hat_belege_und_fundstelle():
    d = project_detail("M-2024-006", mandant_id="musterstadt")   # Verkehrsleitsystem
    assert d and len(d["ampeln"]) == 8
    assert d["method"] == "klassisch"

    kosten = _ampel(d, "kosten")
    assert kosten["kind"] == "cost"
    assert kosten["cost"].get("ist")                 # Kennzahl extrahiert
    assert kosten["fundstelle"].startswith("PSR ")   # Fundstelle vorhanden

    # klassisch -> Meilensteine bei Ergebnissen
    assert _ampel(d, "ergebnisse")["kind"] == "milestones"
    # jede Ampel trägt ihren eigenen Verlauf
    assert all(a["history"] for a in d["ampeln"])


def test_drilldown_agil_zeigt_sprints():
    d = project_detail("M-2023-001", mandant_id="musterstadt")   # Bürgerportal (agil)
    assert d["method"] == "agil"
    erg = _ampel(d, "ergebnisse")
    assert erg["kind"] == "sprints"
    assert erg["rows"]                                # Sprint-Zeilen vorhanden


def test_programm_rollup_im_dashboard():
    d = dashboard_data(mandant_id="musterstadt")
    namen = [r[0] for r in d["by_programm"]]
    assert "Smart City Infrastruktur" in namen
    assert "Digitale Verwaltung Musterstadt" in namen
