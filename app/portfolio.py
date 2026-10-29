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

import datetime
import os
from collections import defaultdict

import yaml

from .data import RANK, _snaps, worst_of

FRIST_FENSTER_TAGE = 180        # ab hier gilt eine Pflichtfrist als "knapp"

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


def load_katalog(mandant_id=None):
    return _load_doc(mandant_id).get("kpi_katalog", []) or []


def get_vorhaben(mandant_id, ref):
    for v in load_vorhaben(mandant_id):
        if str(v.get("ref")) == str(ref):
            return v
    return None


def save_doc(mandant_id, doc):
    """Schreibt den (bearbeiteten) Portfolio-Store als Live-Override."""
    os.makedirs(PORTFOLIO_DIR, exist_ok=True)
    path = os.path.join(PORTFOLIO_DIR, f"{mandant_id}.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
    return path


def _editable_doc(mandant_id):
    """Arbeitskopie des aktuellen Stands (Live falls vorhanden, sonst Seed)."""
    import copy
    doc = copy.deepcopy(_load_doc(mandant_id))
    doc.setdefault("kpi_katalog", [])
    doc.setdefault("vorhaben", [])
    doc.setdefault("budgetrahmen", {})
    return doc


def save_katalog(mandant_id, katalog):
    doc = _editable_doc(mandant_id)
    doc["kpi_katalog"] = katalog
    return save_doc(mandant_id, doc)


def upsert_vorhaben(mandant_id, data):
    doc = _editable_doc(mandant_id)
    vs = doc["vorhaben"]
    for i, v in enumerate(vs):
        if str(v.get("ref")) == str(data.get("ref")):
            vs[i] = data
            break
    else:
        vs.append(data)
    return save_doc(mandant_id, doc)


def delete_vorhaben(mandant_id, ref):
    doc = _editable_doc(mandant_id)
    doc["vorhaben"] = [v for v in doc["vorhaben"] if str(v.get("ref")) != str(ref)]
    return save_doc(mandant_id, doc)


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


def _priority(values, katalog):
    """Berechnet die Prioritätszahl aus dem konfigurierten KPI-Katalog.

    Gewichteter, normierter Mittelwert der bewerteten KPIs (0–100). Fehlende Werte
    gelten als „unbekannt" und werden NICHT als 0 gewertet. Das Muss-Tor sticht:
    es setzt kein Score, sondern eine Pflicht mit Frist.
    """
    muss = False
    tor = {"frist": None, "grund": "", "konsequenz": ""}
    num = den = 0.0
    breakdown = []
    for kpi in katalog:
        kid, art = kpi.get("id"), kpi.get("art")
        if art == "tor":
            t = values.get(kid)
            if isinstance(t, dict) and t.get("pflicht"):
                muss = True
                tor = {"frist": t.get("frist"), "grund": t.get("grund", ""),
                       "konsequenz": t.get("konsequenz", "")}
            continue
        if art != "bewertung":
            continue                               # Mess-KPIs getrennt (angezeigt, nicht hier gewertet)
        v = values.get(kid)
        w = kpi.get("gewicht", 0) or 0
        if v is None or w <= 0:
            continue                               # unbekannt oder ungewichtet -> überspringen
        skala = kpi.get("skala", 4) or 4
        norm = max(0.0, min(1.0, float(v) / skala))
        if kpi.get("richtung") == "negativ":
            norm = 1.0 - norm
        num += norm * w
        den += w
        breakdown.append({"name": kpi.get("name", kid), "wert": v, "gewicht": w})
    score = round(100 * num / den) if den else None
    return {"score": score, "muss": muss, "breakdown": breakdown, **tor}


def _frist_info(frist, status):
    """Restzeit bis zur Pflichtfrist + Ampelung (überfällig / knapp)."""
    out = {"frist": frist, "tage": None, "ueberfaellig": False, "knapp": False}
    if not frist:
        return out
    try:
        d = datetime.date.fromisoformat(str(frist))
    except ValueError:
        return out
    tage = (d - datetime.date.today()).days
    offen = status != "abgeschlossen"
    out["tage"] = tage
    out["ueberfaellig"] = tage < 0 and offen
    out["knapp"] = 0 <= tage <= FRIST_FENSTER_TAGE and offen
    return out


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


def portfolio_view(org=None, mandant_id=None, sort="prioritaet"):
    doc = _load_doc(mandant_id)
    vorhaben = doc.get("vorhaben", []) or []
    rahmen = (doc.get("budgetrahmen", {}) or {})
    katalog = doc.get("kpi_katalog", []) or []
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
        pr = _priority(v.get("kpis", {}) or {}, katalog)
        fi = _frist_info(pr["frist"], status)
        flags = []
        if pr["muss"]:
            flags.append("pflicht")
        if fi["ueberfaellig"]:
            flags.append("frist_ueberfaellig")
        elif fi["knapp"]:
            flags.append("frist_knapp")
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
            "prio_score": pr["score"], "kpi_breakdown": pr["breakdown"],
            "muss": pr["muss"], "muss_grund": pr["grund"], "muss_konsequenz": pr["konsequenz"],
            "frist": fi["frist"], "frist_tage": fi["tage"],
            "frist_ueberfaellig": fi["ueberfaellig"], "frist_knapp": fi["knapp"],
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
            "prio_score": None, "kpi_breakdown": [], "muss": False, "muss_grund": "",
            "muss_konsequenz": "", "frist": None, "frist_tage": None,
            "frist_ueberfaellig": False, "frist_knapp": False, "flags": ["ohne_auftrag"],
        })

    # Sortierung: standardmässig nach Prioritätszahl (höchste oben, ohne Auftrag zuunterst);
    # alternativ nach Handlungsbedarf (Warnungen/Muss zuerst).
    sev = {"frist_ueberfaellig": 5, "ohne_auftrag": 4, "budget": 3, "frist_knapp": 3,
           "ohne_bericht": 2, "aufwand": 2, "pflicht": 1}

    def rank_handlungsbedarf(r):
        s = max((sev.get(f, 0) for f in r["flags"]), default=0)
        frist_key = r["frist_tage"] if (r["muss"] and r["frist_tage"] is not None) else 10**9
        score = r["prio_score"] if r["prio_score"] is not None else -1
        return (-s, 0 if r["muss"] else 1, frist_key, -score, r["titel"])

    def rank_prioritaet(r):
        score = r["prio_score"] if r["prio_score"] is not None else -1
        return (-score, r["titel"])

    rows.sort(key=rank_prioritaet if sort == "prioritaet" else rank_handlungsbedarf)

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
            "name": name, "ref": str(v.get("ref")), "status": soll.get("status", ""),
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
        "pflicht": sum(1 for r in rows if r["muss"]),
        "frist_kritisch": sum(1 for r in rows if r["frist_ueberfaellig"] or r["frist_knapp"]),
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
        "katalog": katalog,
        "status_counts": dict(status_counts),
        "data_source": resolve_portfolio(mandant_id)[1],
    }


# --- Roadmap / Timeline ----------------------------------------------------
PHASEN = {
    "klassisch": [("Initialisierung", 0.10), ("Konzept", 0.20), ("Realisierung", 0.40),
                  ("Einführung", 0.20), ("Abschluss", 0.10)],
    "agil": [("Initialisierung", 0.15), ("Umsetzung", 0.70), ("Abschluss", 0.15)],
    "programm": [("Programminitialisierung", 0.10), ("Programmdurchführung", 0.80),
                 ("Programmabschluss", 0.10)],
}


def _date(s):
    """'YYYY-MM-DD' oder 'YYYY-MM' -> date (sonst None)."""
    if not s:
        return None
    s = str(s)
    try:
        return datetime.date.fromisoformat(s if len(s) >= 10 else s + "-01")
    except ValueError:
        return None


def _phasen(method, start, ende):
    """Phasensegmente proportional über [start, ende] für die gewählte Methode."""
    defs = PHASEN.get(method, PHASEN["klassisch"])
    span = (ende - start).days or 1
    out, cum = [], 0.0
    for i, (name, prop) in enumerate(defs):
        s = start + datetime.timedelta(days=round(cum * span))
        cum += prop
        e = start + datetime.timedelta(days=round(cum * span))
        out.append({"name": name, "start": s, "ende": e,
                    "op": round(0.35 + 0.6 * (i + 1) / len(defs), 2)})
    return out


def timeline_view(org=None, mandant_id=None, bereich=None, einheit=None):
    pv = portfolio_view(org, mandant_id)
    doc = _load_doc(mandant_id)
    zeit = doc.get("zeitplan", {}) or {}

    rows = pv["rows"]
    if bereich:
        rows = [r for r in rows if r.get("bereich") == bereich]
    if einheit:
        rows = [r for r in rows if r.get("einheit") == einheit]

    prog_ampel = {p["name"]: p["ampel"] for p in pv["programme"]}
    prog_ref = {}
    for v in doc.get("vorhaben", []):
        if v.get("art") == "programm":
            prog_ref[v.get("titel") or v.get("ref")] = str(v.get("ref"))

    def make(ref, name, status, prio, kind, indent, reports):
        z = zeit.get(str(ref)) or {}
        s, e = _date(z.get("start")), _date(z.get("ende"))
        method = z.get("method") or ("programm" if kind == "programm" else "klassisch")
        if not s or not e:
            return None
        return {"ref": ref, "name": name, "status": status, "prio": prio,
                "kind": kind, "indent": indent, "reports": reports,
                "method": method, "start": s, "ende": e}

    # Projekte gruppiert: je Programm (Projekte darunter), dann eigenständige
    by_prog = defaultdict(list)
    standalone = []
    for r in rows:
        (by_prog[r["programm"]] if r.get("programm") else standalone).append(r)

    def prio_key(r):
        return (0 if r.get("muss") else 1, -(r.get("prio_score") or -1), r["titel"])

    lanes = []
    for pname in sorted(by_prog, key=lambda n: (-RANK.get(prog_ampel.get(n), -1), n)):
        pl = make(prog_ref.get(pname, pname), pname, prog_ampel.get(pname), None, "programm", False, True)
        if pl:
            lanes.append(pl)
        for r in sorted(by_prog[pname], key=prio_key):
            lane = make(r["ref"], r["titel"], r["ampel"], r.get("prio_score"), "projekt", True, r["reports"])
            if lane:
                lanes.append(lane)
    for r in sorted(standalone, key=prio_key):
        lane = make(r["ref"], r["titel"], r["ampel"], r.get("prio_score"), "projekt", False, r["reports"])
        if lane:
            lanes.append(lane)

    if not lanes:
        return {"lanes": [], "jahre": [], "today_pct": None, "heute": datetime.date.today().isoformat()}

    t_min = min(l["start"] for l in lanes)
    t_max = max(l["ende"] for l in lanes)
    total = (t_max - t_min).days or 1

    def pct(d):
        return round(100 * (d - t_min).days / total, 3)

    for l in lanes:
        l["left"] = pct(l["start"])
        l["width"] = round(pct(l["ende"]) - pct(l["start"]), 3)
        l["phasen"] = [{"name": ph["name"], "op": ph["op"],
                        "left": round(pct(ph["start"]) - l["left"], 3),
                        "width": round(pct(ph["ende"]) - pct(ph["start"]), 3)}
                       for ph in _phasen(l["method"], l["start"], l["ende"])]

    jahre = [{"jahr": y, "pct": pct(datetime.date(y, 1, 1))}
             for y in range(t_min.year, t_max.year + 1)
             if t_min <= datetime.date(y, 1, 1) <= t_max]
    heute = datetime.date.today()
    today_pct = pct(heute) if t_min <= heute <= t_max else (0 if heute < t_min else 100)

    return {"lanes": lanes, "jahre": jahre, "today_pct": today_pct,
            "heute": heute.isoformat(), "t_min": t_min.isoformat(), "t_max": t_max.isoformat(),
            "bereich": bereich, "einheit": einheit}
