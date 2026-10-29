"""Portfolioschicht: verbindet das gepflegte **Soll** (Durchführungsaufträge,
Budgets, Priorität) mit dem **Ist** aus den Statusberichten.

Trennung bewusst nach Datenherkunft:
  - Soll  = gepflegt im Portfolio-Store (data/portfolio/<mandant>.yaml, Seed in
            sample-data/portfolio-<mandant>.yaml). Langsam beweglich, bei der
            Freigabe gesetzt.
  - Ist   = kommt automatisch aus den PSR (Kosten/Aufwand Ist + Prognose, Ampel).

Die Portfolioebene rechnet nichts, was nicht belegt ist: fehlt ein Bericht oder
ein Auftrag, wird genau das ausgewiesen (Governance-Befund), nicht geraten.
"""
from __future__ import annotations

import os
from collections import defaultdict

import yaml

from .data import RANK, _snaps, worst_of

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTFOLIO_DIR = os.path.join(ROOT, "data", "portfolio")        # gepflegt (Laufzeit)
SAMPLE = os.path.join(ROOT, "sample-data")
SEEDS = {                                                       # committete Seeds je Mandant
    "musterstadt": os.path.join(SAMPLE, "portfolio-musterstadt.yaml"),
}

STATUS_LABEL = {
    "idee": "Idee", "beantragt": "Beantragt", "freigegeben": "Freigegeben",
    "laufend": "Laufend", "zurueckgestellt": "Zurückgestellt",
    "abgeschlossen": "Abgeschlossen", "abgebrochen": "Abgebrochen",
}
# Status, bei denen ein laufender Bericht erwartet wird (sonst „ohne Bericht").
BERICHT_ERWARTET = {"freigegeben", "laufend"}


def resolve_portfolio(mandant_id=None):
    mid = mandant_id or ""
    live = os.path.join(PORTFOLIO_DIR, f"{mid}.yaml")
    if os.path.exists(live):
        return live, "gepflegt (Live)"
    seed = SEEDS.get(mid)
    if seed and os.path.exists(seed):
        return seed, "Seed"
    return None, "kein Portfolio"


def _load_doc(mandant_id=None):
    path, _ = resolve_portfolio(mandant_id)
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    if isinstance(doc, list):                 # Rückwärtskompatibel (reine Liste)
        return {"vorhaben": doc}
    return doc


def load_vorhaben(mandant_id=None):
    return _load_doc(mandant_id).get("vorhaben", []) or []


def _num(x):
    """'920000' / 920000 / '' -> float | None (kein Raten bei leer/unbekannt)."""
    if x is None or x == "":
        return None
    try:
        return float(str(x).replace("'", "").replace(" ", "").replace("+", ""))
    except ValueError:
        return None


def _last_by_project(snaps):
    by = defaultdict(list)
    for r in snaps:
        by[str(r["projekt"])].append(r)
    out = {}
    for key, rs in by.items():
        rs.sort(key=lambda z: z["periode"])
        out[key] = rs[-1]
    return out


def _metrics(budget_soll, ist, prognose):
    """Ausschöpfung (Ist/Soll) und prognostizierte Abweichung (Prognose-Soll)."""
    m = {"ausschoepfung": None, "prognose_pct": None, "abweichung": None, "ueber_budget": False}
    if budget_soll:
        if ist is not None:
            m["ausschoepfung"] = ist / budget_soll
        if prognose is not None:
            m["prognose_pct"] = prognose / budget_soll
            m["abweichung"] = prognose - budget_soll
            m["ueber_budget"] = prognose > budget_soll
    return m


def _prio_score(prio):
    """Summe der gestaltbaren Kriterien (0–4 je Kriterium). Pflicht sticht separat."""
    krit = (prio or {}).get("kriterien") or {}
    werte = [v for v in krit.values() if isinstance(v, (int, float))]
    return sum(werte) if werte else None


def _budget_rollup(rows, dim, rahmen_map):
    """Budget je Bereich/Einheit: zugeteilter Rahmen vs. Summe Soll vs. Summe Prognose.

    Die Abteilung erhält einen Budgetrahmen und führt damit ihre Projekte durch –
    überschreitet die Prognose den Rahmen, ist das ein Steuerungssignal.
    """
    groups = defaultdict(lambda: {"soll": 0.0, "prognose": 0.0, "ampeln": [], "n": 0})
    for r in rows:
        name = r.get(dim)
        if not name or r.get("status") == "abgebrochen":    # abgebrochen: Budget freigegeben
            continue
        g = groups[name]
        g["soll"] += r["budget_soll"] or 0
        g["prognose"] += r["k_prog"] or 0
        g["n"] += 1
        if r["ampel"]:
            g["ampeln"].append(r["ampel"])
    out = []
    for name, g in groups.items():
        rah = _num(rahmen_map.get(name))
        out.append({
            "name": name, "rahmen": rah, "summe_soll": g["soll"],
            "summe_prognose": g["prognose"], "projekte": g["n"],
            "abweichung": (g["prognose"] - rah) if rah else None,
            "ueber_rahmen": bool(rah and g["prognose"] > rah),
            "ampel": worst_of(g["ampeln"]) if g["ampeln"] else None,
        })
    out.sort(key=lambda x: (0 if x["ueber_rahmen"] else 1, -RANK.get(x["ampel"], -1), x["name"]))
    return out


def portfolio_view(org=None, mandant_id=None):
    doc = _load_doc(mandant_id)
    vorhaben = doc.get("vorhaben", []) or []
    rahmen = (doc.get("budgetrahmen", {}) or {})
    last = _last_by_project(_snaps(org, mandant_id))      # Ist je Projekt (letzter Bericht)
    referenced = set()

    def ist_prog(key, feld):
        snap = last.get(str(key))
        if not snap:
            return None, None, None, None
        k = snap.get("kosten", {}) or {}
        eff = (snap.get("evidence", {}) or {}).get("effort", {}) or {}
        src = k if feld == "kosten" else eff
        return (_num(src.get("ist")), _num(src.get("prognose")),
                snap.get("status", {}).get("gesamt"), snap.get("periode"))

    rows = []
    for v in vorhaben:
        if v.get("art") == "programm":
            continue                                     # Programme separat (unten)
        ref = str(v.get("ref"))
        soll = v.get("auftrag", {}) or {}
        status = soll.get("status", "idee")
        budget_soll = _num(soll.get("budget_soll"))
        aufwand_soll = _num(soll.get("aufwand_soll"))
        k_ist, k_prog, ampel, periode = ist_prog(ref, "kosten")
        a_ist, a_prog, _, _ = ist_prog(ref, "aufwand")
        reports = ref in last
        if reports:
            referenced.add(ref)
        km = _metrics(budget_soll, k_ist, k_prog)
        am = _metrics(aufwand_soll, a_ist, a_prog)
        prio = v.get("prioritaet", {}) or {}
        flags = []
        if prio.get("pflicht"):
            flags.append("pflicht")
        if km["ueber_budget"] and status == "laufend":          # nur laufende = Handlungsbedarf
            flags.append("budget")
        if am["ueber_budget"] and status == "laufend":
            flags.append("aufwand")
        if not reports and status in BERICHT_ERWARTET:
            flags.append("ohne_bericht")
        snap = last.get(ref, {}) or {}
        rows.append({
            "ref": ref, "titel": v.get("titel") or snap.get("name") or ref,
            "programm": v.get("programm", ""),
            "einheit": v.get("einheit") or snap.get("verwaltungseinheit", ""),
            "bereich": v.get("bereich") or snap.get("geschaeftsbereich", ""),
            "status": status,
            "status_label": STATUS_LABEL.get(status, status),
            "ampel": ampel, "periode": periode, "reports": reports,
            "budget_soll": budget_soll, "k_ist": k_ist, "k_prog": k_prog, "km": km,
            "aufwand_soll": aufwand_soll, "a_prog": a_prog, "am": am,
            "pflicht": bool(prio.get("pflicht")), "pflicht_grund": prio.get("pflicht_grund", ""),
            "prio_score": _prio_score(prio), "prio_wert": prio.get("wert"),
            "prio_begruendung": prio.get("begruendung", ""),
            "flags": flags,
        })

    # PSR-Projekte ohne erfassten Auftrag -> Governance-Befund
    for key, snap in last.items():
        if key in referenced:
            continue
        rows.append({
            "ref": key, "titel": snap.get("name") or key, "programm": snap.get("programm", ""),
            "einheit": snap.get("verwaltungseinheit", ""), "bereich": snap.get("geschaeftsbereich", ""),
            "status": None, "status_label": "— kein Auftrag —",
            "ampel": snap.get("status", {}).get("gesamt"), "periode": snap.get("periode"),
            "reports": True, "budget_soll": None, "k_ist": _num((snap.get("kosten") or {}).get("ist")),
            "k_prog": _num((snap.get("kosten") or {}).get("prognose")), "km": _metrics(None, None, None),
            "aufwand_soll": None, "a_prog": None, "am": _metrics(None, None, None),
            "pflicht": False, "pflicht_grund": "", "prio_score": None, "prio_wert": None,
            "prio_begruendung": "", "flags": ["ohne_auftrag"],
        })

    # Sortierung: Handlungsbedarf zuerst
    sev = {"ohne_auftrag": 4, "budget": 3, "ohne_bericht": 2, "aufwand": 2, "pflicht": 1}

    def rank(r):
        s = max((sev.get(f, 0) for f in r["flags"]), default=0)
        amp = RANK.get(r["ampel"], -1)
        return (-s, -amp, r["titel"])

    rows.sort(key=rank)

    # Programm-Rahmen: Soll des Programms vs. Summe der Projekte
    programme = []
    proj_by_prog = defaultdict(list)
    for r in rows:
        if r["programm"]:
            proj_by_prog[r["programm"]].append(r)
    for v in vorhaben:
        if v.get("art") != "programm":
            continue
        name = v.get("titel") or v.get("ref")
        soll = v.get("auftrag", {}) or {}
        kinder = proj_by_prog.get(name, [])
        summe_soll = sum(r["budget_soll"] or 0 for r in kinder)
        summe_prog = sum(r["k_prog"] or 0 for r in kinder)
        ampeln = [r["ampel"] for r in kinder if r["ampel"]]
        programme.append({
            "name": name, "status": soll.get("status", ""),
            "status_label": STATUS_LABEL.get(soll.get("status"), soll.get("status", "")),
            "budget_soll": _num(soll.get("budget_soll")), "kinder": len(kinder),
            "summe_soll": summe_soll, "summe_prognose": summe_prog,
            "ampel": worst_of(ampeln) if ampeln else None,
        })
    programme.sort(key=lambda p: (-RANK.get(p["ampel"], -1), p["name"]))

    # KPI (Summe auf Projekt-Ebene – kein Doppelzählen über Programme;
    # abgebrochene Vorhaben zählen nicht in die Budgetsummen)
    proj_rows = [r for r in rows if "ohne_auftrag" not in r["flags"]]
    aktiv = [r for r in proj_rows if r["status"] != "abgebrochen"]
    kpi = {
        "vorhaben": len(proj_rows),
        "budget_soll": sum(r["budget_soll"] or 0 for r in aktiv),
        "prognose": sum(r["k_prog"] or 0 for r in aktiv if r["k_prog"]),
        "ueber_budget": sum(1 for r in rows if "budget" in r["flags"]),
        "ohne_auftrag": sum(1 for r in rows if "ohne_auftrag" in r["flags"]),
        "ohne_bericht": sum(1 for r in rows if "ohne_bericht" in r["flags"]),
        "pflicht": sum(1 for r in rows if r["pflicht"]),
    }
    status_counts = defaultdict(int)
    for r in rows:
        if r["status"]:
            status_counts[r["status"]] += 1

    by_bereich = _budget_rollup(rows, "bereich", rahmen.get("bereich", {}) or {})
    by_einheit = _budget_rollup(rows, "einheit", rahmen.get("einheit", {}) or {})

    return {
        "rows": rows, "programme": programme, "kpi": kpi,
        "by_bereich": by_bereich, "by_einheit": by_einheit,
        "status_counts": dict(status_counts),
        "data_source": resolve_portfolio(mandant_id)[1],
    }
