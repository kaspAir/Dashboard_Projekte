"""Ressourcen-/Auslastungsanalyse (DA-Personaleinsatz × Zeitplan)."""
from app.resources import resource_analysis


def test_auslastung_erkennt_ueberlast():
    a = resource_analysis(mandant_id="musterstadt")
    assert len(a["persons"]) > 10
    assert a["capacity"] == 18
    assert a["n_overloads"] >= 1
    assert a["n_personen_ueberlastet"] >= 1
    assert any(o["ratio"] > 1.0 for o in a["overloads"])
    # jede Person hat eine Monatsreihe
    assert all(a["grid"][p] for p in a["persons"])


def test_kapazitaet_parametrisierbar():
    streng = resource_analysis(mandant_id="musterstadt", cap=10)
    locker = resource_analysis(mandant_id="musterstadt", cap=30)
    assert streng["n_overloads"] >= locker["n_overloads"]
