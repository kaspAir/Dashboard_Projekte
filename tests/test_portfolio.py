"""Portfolio: Soll-Ist-Join, Governance-Befunde, Budget-Roll-up, KPI-Scoring,
konfigurierbarer Katalog und Pflege-Roundtrip."""
import os

from app import portfolio as P
from app.portfolio import portfolio_view


def _row(p, ref):
    return next(r for r in p["rows"] if r["ref"] == ref)


def test_governance_befunde():
    p = portfolio_view(mandant_id="musterstadt")
    # berichtet, aber kein erfasster Durchführungsauftrag
    assert "ohne_auftrag" in _row(p, "M-2025-011")["flags"]
    # freigegeben, aber noch kein Statusbericht
    assert "ohne_bericht" in _row(p, "M-2026-013")["flags"]


def test_budget_warnung_nur_bei_laufenden():
    p = portfolio_view(mandant_id="musterstadt")
    assert "budget" in _row(p, "M-2024-006")["flags"]          # Verkehrsleit, laufend, Prognose > Soll
    assert "budget" not in _row(p, "M-2022-007")["flags"]      # abgebrochen -> keine Warnung


def test_muss_tor_mit_frist():
    p = portfolio_view(mandant_id="musterstadt")
    er = _row(p, "M-2024-004")                                 # E-Rechnung: Pflicht, Frist 2026-12-31
    assert er["muss"] is True and er["frist"] == "2026-12-31"
    assert er["frist_knapp"] is True                           # Frist nah -> knapp
    ew = _row(p, "M-2022-007")                                 # Einwohnerregister: Frist überschritten
    assert ew["muss"] is True and "frist_ueberfaellig" in ew["flags"]


def test_prioritaetszahl_berechnet():
    p = portfolio_view(mandant_id="musterstadt")
    r = _row(p, "M-2023-001")                                  # bewertete KPIs -> Score 0..100
    assert isinstance(r["prio_score"], int) and 0 <= r["prio_score"] <= 100
    assert any(k["id"] == "strategie" for k in p["katalog"])   # Katalog ausgeliefert


def test_bereichsrahmen_und_abgebrochen_ausgenommen():
    p = portfolio_view(mandant_id="musterstadt")
    bau = next(b for b in p["by_bereich"] if b["name"] == "Ressort Bau & Umwelt")
    assert bau["rahmen"] == 1800000
    assert bau["ueber_rahmen"] is True                         # Prognose über dem Rahmen
    # abgebrochenes 1.1-Mio-Vorhaben zählt nicht in die Budgetsumme
    assert p["kpi"]["budget_soll"] < 5000000


def test_pflege_roundtrip(tmp_path, monkeypatch):
    # isolierter Portfolio-Store, damit echte Seeds unberührt bleiben
    monkeypatch.setattr(P, "PORTFOLIO_DIR", str(tmp_path))
    mid = "pytest-portfolio"
    P.save_katalog(mid, [{"id": "nutzen", "name": "Nutzen", "art": "bewertung",
                          "skala": 4, "richtung": "positiv", "gewicht": 2}])
    P.upsert_vorhaben(mid, {"ref": "X-1", "art": "projekt", "titel": "Test",
                            "auftrag": {"status": "laufend", "budget_soll": 100000},
                            "kpis": {"nutzen": 4}})
    v = P.get_vorhaben(mid, "X-1")
    assert v and v["kpis"]["nutzen"] == 4
    assert any(k["id"] == "nutzen" for k in P.load_katalog(mid))
    P.delete_vorhaben(mid, "X-1")
    assert P.get_vorhaben(mid, "X-1") is None
