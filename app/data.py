"""Daten- und Aggregationsschicht des Dashboards.

Quelle (Phase 0): die Ground-Truth-Zeitreihe (sample-data/ground_truth.yaml).
Später wird dieselbe Struktur aus der Extraktion echter PSR gefüllt – die
Präsentation bleibt unverändert.
"""
from __future__ import annotations

import os
from collections import Counter, defaultdict

import yaml

from .orgs import in_scope

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORES_DIR = os.path.join(ROOT, "data", "stores")                 # Laufzeit-Ingestion je Mandant
SAMPLE = os.path.join(ROOT, "sample-data")
SEEDS = {                                                          # committete Seed-Stores je Mandant
    "llv": os.path.join(SAMPLE, "canonical_store.yaml"),
    "kaspair": os.path.join(SAMPLE, "store-kaspair.yaml"),
    "musterstadt": os.path.join(SAMPLE, "store-musterstadt.yaml"),
}


def resolve_source(mandant_id=None):
    mid = mandant_id or "llv"
    live = os.path.join(STORES_DIR, f"{mid}.yaml")
    if os.path.exists(live):
        return live, "Ingestion (Live)"
    seed = SEEDS.get(mid)
    if seed and os.path.exists(seed):
        return seed, "Seed-Daten"
    return None, "keine Daten"

RANK = {"grün": 0, "gelb": 1, "rot": 2}
INV = {0: "grün", 1: "gelb", 2: "rot"}
STABILITY_THRESHOLD = 4        # ab so vielen Statuswechseln gilt ein Projekt als schwankend
TREND_WINDOW = 6              # Monate für die Trendrichtung
RELIABILITY_MIN_RED = 3      # min. Monate rot vor Abbruch, um als "ehrlich gewarnt" zu gelten


def worst_of(values):
    return INV[max(RANK[v] for v in values)] if values else "grün"


def load_snapshots(mandant_id=None):
    path, _ = resolve_source(mandant_id)
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def _snaps(org=None, mandant_id=None):
    """Snapshots des Mandanten, auf die Organisation (Scope) gefiltert."""
    snaps = load_snapshots(mandant_id)
    if org:
        snaps = [r for r in snaps if in_scope(r, org)]
    return snaps


def _project_view(rs):
    """Aggregiert die Zeitreihe eines Projekts zu einer Dashboard-Zeile."""
    rs = sorted(rs, key=lambda r: r["periode"])
    seq = [r["status"]["gesamt"] for r in rs]
    last = rs[-1]
    window = seq[-TREND_WINDOW:]
    if RANK[window[-1]] < RANK[window[0]]:
        trend = "besser"
    elif RANK[window[-1]] > RANK[window[0]]:
        trend = "schlechter"
    else:
        trend = "stabil"
    changes = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    trailing_red = 0
    for s in reversed(seq):
        if s == "rot":
            trailing_red += 1
        else:
            break
    return dict(
        key=last["projekt"], name=last["name"], nummer=last["nummer"],
        org_unit=last["verwaltungseinheit"], business_area=last["geschaeftsbereich"],
        programm=last.get("programm", ""), method=last.get("method", "klassisch"),
        phase=last["phase"], lifecycle=last["lifecycle"],
        overall=seq[-1], status=last["status"], trend=trend,
        stability="schwankend" if changes >= STABILITY_THRESHOLD else "stabil",
        changes=changes, months=len(seq), trailing_red=trailing_red,
        kosten=last.get("kosten", {}),
    )


def build_projects(snapshots):
    by = defaultdict(list)
    for r in snapshots:
        by[r["projekt"]].append(r)
    return [_project_view(rs) for rs in by.values()]


def _rollup(projects, dim):
    groups = defaultdict(list)
    for p in projects:
        if not p.get(dim):          # leere Dimension (z. B. kein Programm) nicht gruppieren
            continue
        groups[p[dim]].append(p["overall"])
    rows = [(name, worst_of(vals), len(vals), Counter(vals)) for name, vals in groups.items()]
    # schlechteste zuerst, dann alphabetisch
    return sorted(rows, key=lambda x: (-RANK[x[1]], x[0]))


def dashboard_data(org=None, mandant_id=None):
    projects = build_projects(_snaps(org, mandant_id))
    active = [p for p in projects if p["lifecycle"] == "active"]
    inactive = [p for p in projects if p["lifecycle"] != "active"]
    aborted = [p for p in inactive if p["lifecycle"] == "aborted"]
    for p in aborted:
        p["verdict"] = "ehrlich" if p["trailing_red"] >= RELIABILITY_MIN_RED else "unehrlich"
    return dict(
        active=sorted(active, key=lambda p: (-RANK[p["overall"]], p["name"])),
        inactive=inactive,
        aborted=sorted(aborted, key=lambda p: p["trailing_red"]),
        completed=[p for p in inactive if p["lifecycle"] == "completed"],
        kpi=Counter(p["overall"] for p in active),
        by_programm=_rollup(active, "programm"),
        by_area=_rollup(active, "business_area"),
        by_unit=_rollup(active, "org_unit"),
        total_active=len(active),
        total_all=len(projects),
        data_source=resolve_source(mandant_id)[1],
    )


def all_projects(org=None, mandant_id=None):
    """Alle Projekte des Mandanten (jeder Lebenszyklus), schlechteste zuerst."""
    return sorted(build_projects(_snaps(org, mandant_id)),
                  key=lambda p: (-RANK[p["overall"]], p["name"]))


# Reihenfolge und Beschriftung der 8 Ampeln im Drilldown.
AMPEL_ORDER = [
    ("gesamt", "Gesamtbeurteilung"), ("termine", "Termine"), ("kosten", "Kosten"),
    ("personalaufwand", "Personalaufwand"), ("ergebnisse", "Ergebnisse"),
    ("projektziele", "Projektziele"), ("projektrisiken", "Projektrisiken"),
    ("governance", "Einhaltung Governance"),
]


def _fundstelle(quellen, key, periode):
    src = quellen.get(key)
    return f"PSR {periode} · {src}" if src else ""


def _ampeln(snaps):
    """Pro Ampel: aktueller Wert, Erläuterung, eigener Verlauf und die konkreten
    Belege aus dem PSR (methodengerecht: Meilensteine klassisch / Sprints agil),
    jeweils mit Fundstelle. Nur was wirklich extrahiert wurde – kein Raten."""
    cur = snaps[-1]
    per = cur["periode"]
    ev = cur.get("evidence", {}) or {}
    q = cur.get("quellen", {}) or {}
    notes = ev.get("status_notes", {}) or {}
    method = cur.get("method", "klassisch")
    status = cur.get("status", {})

    def history(dim):
        return [{"periode": s["periode"], "status": s.get("status", {}).get(dim)}
                for s in snaps if dim in s.get("status", {})]

    out = []
    for dim, label in AMPEL_ORDER:
        if dim not in status:
            continue
        e = {"key": dim, "label": label, "value": status[dim], "note": notes.get(dim, ""),
             "history": history(dim), "kind": "text", "rows": [], "text": "",
             "fundstelle": "", "issues": [], "issues_fundstelle": ""}
        if dim == "gesamt":
            e["text"] = ev.get("fazit", "")
            e["fundstelle"] = _fundstelle(q, "fazit", per)
            e["issues"] = ev.get("issues", [])
            e["issues_fundstelle"] = _fundstelle(q, "issues", per)
        elif dim == "kosten":
            e["kind"] = "cost"
            e["cost"] = cur.get("kosten", {})
            e["fundstelle"] = _fundstelle(q, "cost", per)
        elif dim == "personalaufwand":
            e["kind"] = "effort"
            e["cost"] = ev.get("effort", {})
            e["fundstelle"] = _fundstelle(q, "effort", per)
        elif dim in ("termine", "ergebnisse"):
            if method == "agil":
                e["kind"] = "sprints"
                src_key = "sprints_done" if dim == "ergebnisse" else ("sprints_next" if ev.get("sprints_next") else "sprints_done")
                e["rows"] = ev.get(src_key, [])
                e["fundstelle"] = _fundstelle(q, src_key, per)
            else:
                e["kind"] = "milestones"
                src_key = "milestones_done" if dim == "ergebnisse" else ("milestones_next" if ev.get("milestones_next") else "milestones_done")
                e["rows"] = ev.get(src_key, [])
                e["fundstelle"] = _fundstelle(q, src_key, per)
        elif dim == "projektziele":
            e["kind"] = "objectives"
            e["rows"] = ev.get("objectives", [])
            e["fundstelle"] = _fundstelle(q, "objectives", per)
        elif dim == "projektrisiken":
            e["kind"] = "risks"
            e["rows"] = ev.get("risks", [])
            e["fundstelle"] = _fundstelle(q, "risks", per)
        elif dim == "governance":
            if notes.get("governance"):
                e["fundstelle"] = _fundstelle(q, "status_notes", per)
        out.append(e)
    return out


def project_detail(key, org=None, mandant_id=None):
    """Zeitreihe + Zusammenfassung eines Projekts (per Projekt-Schlüssel)."""
    snaps = [r for r in _snaps(org, mandant_id) if str(r.get("projekt")) == str(key)]
    if not snaps:
        return None
    snaps.sort(key=lambda r: r["periode"])
    return {
        "summary": _project_view(snaps),
        "timeline": [{
            "periode": r["periode"], "gesamt": r["status"]["gesamt"],
            "status": r["status"], "kosten": r.get("kosten", {}),
            "phase": r["phase"], "lifecycle": r["lifecycle"],
        } for r in snaps],
        "current": snaps[-1]["status"],
        "ampeln": _ampeln(snaps),
        "method": snaps[-1].get("method", "klassisch"),
    }
