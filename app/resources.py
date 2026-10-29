"""Ressourcen-/Auslastungsanalyse pro Person über die Zeitachse.

Quelle: der Personaleinsatz je Person (Rolle · Person · PT) aus den Durchführungs-
aufträgen (Baseline) × der Zeitplan (Start/Ende/Methode → Phasen). Der geplante
Aufwand je Person wird phasengewichtet über die Projektmonate verteilt und über alle
Projekte summiert. Überschreitet die Summe die Monatskapazität, ist eine geplante
Überlast erkannt.
"""
from __future__ import annotations

import datetime
from collections import defaultdict

from .da import load_da
from .portfolio import PHASEN, _load_doc

KAPAZITAET_PT_MONAT = 18        # verfügbare Projekt-Personentage je Person und Monat


def _date(s):
    if not s:
        return None
    s = str(s)
    try:
        return datetime.date.fromisoformat(s if len(s) >= 10 else s + "-01")
    except ValueError:
        return None


def _mkey(d):
    return f"{d.year}-{d.month:02d}"


def _month_firsts(start, ende):
    out, y, m = [], start.year, start.month
    while (y, m) <= (ende.year, ende.month):
        out.append(datetime.date(y, m, 1))
        m += 1
        if m > 12:
            y += 1
            m = 1
    return out


def _month_weights(method, start, ende):
    """Verteilt 1.0 phasengewichtet über die Projektmonate (Anteile aus PHASEN)."""
    months = _month_firsts(start, ende)
    if not months:
        return {}
    defs = PHASEN.get(method, PHASEN["klassisch"])
    total = (ende - start).days or 1
    weights = {_mkey(m): 0.0 for m in months}
    cum = 0.0
    for _name, prop in defs:
        p_start = start + datetime.timedelta(days=round(cum * total))
        cum += prop
        p_end = start + datetime.timedelta(days=round(cum * total))
        pm = [m for m in months if p_start <= m.replace(day=15) < p_end]
        for m in pm:
            weights[_mkey(m)] += prop / len(pm)
    s = sum(weights.values()) or 1.0
    return {k: v / s for k, v in weights.items()}


def resource_analysis(org=None, mandant_id=None, cap=KAPAZITAET_PT_MONAT):
    da = load_da(mandant_id)
    zeit = _load_doc(mandant_id).get("zeitplan", {}) or {}

    load = defaultdict(lambda: defaultdict(float))
    projekte = defaultdict(set)
    for ref, rec in da.items():
        if rec.get("typ") != "projekt":
            continue
        z = zeit.get(ref)
        start, ende = (_date((z or {}).get("start")), _date((z or {}).get("ende")))
        if not z or not start or not ende or ende <= start:
            continue
        w = _month_weights(z.get("method", "klassisch"), start, ende)
        for r in rec.get("ressourcen", []):
            person, pt = r.get("person"), (r.get("pt") or 0)
            if not person or not pt:
                continue
            for mk, wt in w.items():
                if wt > 0:
                    load[person][mk] += pt * wt
                    projekte[person].add(ref)

    months = sorted({mk for pm in load.values() for mk in pm})
    persons = sorted(load.keys(), key=lambda p: -sum(load[p].values()))
    grid = {p: {m: round(load[p].get(m, 0), 1) for m in months} for p in persons}

    overloads = []
    for p in persons:
        for m in months:
            v = load[p].get(m, 0)
            if v > cap:
                overloads.append({"person": p, "month": m, "pt": round(v, 1),
                                  "ratio": round(v / cap, 2)})
    overloads.sort(key=lambda o: -o["ratio"])

    today = datetime.date.today()
    return {
        "persons": persons, "months": months, "grid": grid, "capacity": cap,
        "projekte": {p: len(projekte[p]) for p in persons},
        "overloads": overloads, "n_overloads": len(overloads),
        "n_personen_ueberlastet": len({o["person"] for o in overloads}),
        "today_m": _mkey(today),
        "data_source": "Durchführungsaufträge (Baseline) × Zeitplan",
    }
