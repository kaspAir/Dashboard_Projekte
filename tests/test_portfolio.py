"""Portfolio Slice 1: Soll-Ist-Join, Governance-Befunde, Budget-Roll-up je Bereich."""
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


def test_pflicht_und_prioritaet():
    p = portfolio_view(mandant_id="musterstadt")
    r = _row(p, "M-2024-004")                                  # E-Rechnung (rechtlich Pflicht)
    assert r["pflicht"] is True
    assert r["prio_wert"] == 9


def test_bereichsrahmen_und_abgebrochen_ausgenommen():
    p = portfolio_view(mandant_id="musterstadt")
    bau = next(b for b in p["by_bereich"] if b["name"] == "Ressort Bau & Umwelt")
    assert bau["rahmen"] == 1800000
    assert bau["ueber_rahmen"] is True                         # Prognose über dem Rahmen
    # abgebrochenes 1.1-Mio-Vorhaben zählt nicht in die Budgetsumme
    assert p["kpi"]["budget_soll"] < 5000000
