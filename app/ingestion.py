"""Ingestion: konfigurierte Quelle scannen -> PSR erkennen -> extrahieren ->
historisierter kanonischer Store.

Quell-agnostisch: nutzt einen Connector (discover) und die Extraktion. Die
Projekt-Identität und die Periode kommen aus dem INHALT (Projektnummer/-name,
Berichtsdatum), nicht aus dem Dateipfad – so funktioniert es auch, wenn PSR
verstreut in einem grossen Verzeichnisbaum liegen.
"""
from __future__ import annotations

import os

import yaml

from .extraction import extract_snapshot
from .mim import load_mim
from .sources.config import build_connector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME_STORE = os.path.join(ROOT, "data", "canonical_store.yaml")

# MIM-Feld-ID -> Schlüssel im kanonischen Snapshot (Statusampeln)
FIELD_TO_STATUS = {
    "status_overall": "gesamt", "status_schedule": "termine", "status_cost": "kosten",
    "status_effort": "personalaufwand", "status_results": "ergebnisse",
    "status_objectives": "projektziele", "status_risks": "projektrisiken",
    "status_governance": "governance",
}
# Kriterium „ist ein PSR": Kernfelder erkannt
REQUIRED = ("project_name", "status_overall")
MIN_STATUS_FIELDS = 6


def _period(report_date: str) -> str:
    """'DD.MM.YYYY' -> 'YYYY-MM' (leer, wenn nicht parsebar)."""
    parts = report_date.split(".")
    if len(parts) == 3 and parts[2].isdigit():
        return f"{parts[2]}-{parts[1].zfill(2)}"
    return ""


def _val(prov, fid, default=""):
    return prov.get(fid, {}).get("value", default)


def is_psr(prov: dict) -> bool:
    if not all(k in prov for k in REQUIRED):
        return False
    return sum(1 for fid in FIELD_TO_STATUS if fid in prov) >= MIN_STATUS_FIELDS


def to_record(prov: dict) -> dict:
    status = {gt: prov[fid]["value"] for fid, gt in FIELD_TO_STATUS.items() if fid in prov}
    cost = _val(prov, "cost", {}) or {}
    key = _val(prov, "project_number") or _val(prov, "project_name")
    return {
        "projekt": key,
        "name": _val(prov, "project_name"),
        "nummer": _val(prov, "project_number"),
        "verwaltungseinheit": _val(prov, "org_unit"),
        "geschaeftsbereich": _val(prov, "business_area"),
        "lifecycle": _val(prov, "lifecycle_state", "active"),
        "phase": _val(prov, "phase"),
        "periode": _period(_val(prov, "report_date")),
        "status": status,
        "kosten": {k: cost.get(k, "") for k in ("plan", "ist", "prognose")},
    }


def run_ingestion(source_config: dict, mim: dict | None = None) -> dict:
    mim = mim or load_mim()
    connector = build_connector(source_config)
    records, scanned, skipped = [], 0, 0
    for artifact in connector.discover():
        scanned += 1
        try:
            prov = extract_snapshot(artifact.local_path, mim)["provenance"]
        except Exception:
            skipped += 1
            continue
        if not is_psr(prov):
            skipped += 1
            continue
        records.append(to_record(prov))
    # stabile Sortierung: Projekt, dann Periode (Zeitreihe)
    records.sort(key=lambda r: (str(r["projekt"]), r["periode"]))
    return {"records": records, "scanned": scanned, "ingested": len(records), "skipped": skipped}


def write_store(records, path: str | None = None) -> str:
    """Schreibt den kanonischen Store (Laufzeit) – bevorzugte Datenquelle des Dashboards."""
    path = path or RUNTIME_STORE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(records, f, allow_unicode=True, sort_keys=False)
    return path
