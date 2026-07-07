"""Daten- und Aggregationsschicht des Dashboards.

Quelle (Phase 0): die Ground-Truth-Zeitreihe (sample-data/ground_truth.yaml).
Später wird dieselbe Struktur aus der Extraktion echter PSR gefüllt – die
Präsentation bleibt unverändert.
"""
from __future__ import annotations

import os
from collections import Counter, defaultdict

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOTS = os.path.join(ROOT, "sample-data", "ground_truth.yaml")

RANK = {"grün": 0, "gelb": 1, "rot": 2}
INV = {0: "grün", 1: "gelb", 2: "rot"}
STABILITY_THRESHOLD = 4        # ab so vielen Statuswechseln gilt ein Projekt als schwankend
TREND_WINDOW = 6              # Monate für die Trendrichtung
RELIABILITY_MIN_RED = 3      # min. Monate rot vor Abbruch, um als "ehrlich gewarnt" zu gelten


def worst_of(values):
    return INV[max(RANK[v] for v in values)] if values else "grün"


def load_snapshots(path: str | None = None):
    path = path or SNAPSHOTS
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or []


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
        groups[p[dim]].append(p["overall"])
    rows = [(name, worst_of(vals), len(vals), Counter(vals)) for name, vals in groups.items()]
    # schlechteste zuerst, dann alphabetisch
    return sorted(rows, key=lambda x: (-RANK[x[1]], x[0]))


def dashboard_data():
    projects = build_projects(load_snapshots())
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
        by_area=_rollup(active, "business_area"),
        by_unit=_rollup(active, "org_unit"),
        total_active=len(active),
        total_all=len(projects),
    )
