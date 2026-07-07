"""Deterministische Extraktion aus einem PSR (.docx) -> kanonische Werte + Provenienz.

MIM-gesteuert bei der Normalisierung der Ampeln (vocab.rag). Jeder extrahierte Wert
trägt Fundstelle (source) und Konfidenz. Wird ein Wert nicht sicher erkannt, bleibt
das Feld leer (kein Raten).
"""
from __future__ import annotations

from .reader import metadata_kv, read_tables, tables_with_header

# Die 8 Ampel-Bereiche der HERMES-Übersichtstabelle -> kanonische MIM-Feld-IDs.
RAG_LABEL_TO_FIELD = {
    "Gesamtbeurteilung": "status_overall",
    "Termine": "status_schedule",
    "Kosten": "status_cost",
    "Personalaufwand": "status_effort",
    "Ergebnisse": "status_results",
    "Projektziele": "status_objectives",
    "Projektrisiken": "status_risks",
    "Einhaltung Governance": "status_governance",
}

META_MAP = {
    "project_name": "Projektname",
    "project_number": "Projektnummer",
    "report_date": "Bearbeitungsdatum",
    "project_lead": "Projektleiter/in",
    "sponsor": "Auftraggeber/in",
    "org_unit": "Verwaltungseinheit",
    "business_area": "Geschäftsbereich",
    "phase": "Projektphase",
}


def normalize_rag(text: str, vocab: dict):
    """Freitext -> kanonischer Ampelwert (grün/gelb/rot) via MIM-Vokabular."""
    t = text.strip().lower()
    for canon, synonyms in vocab.items():
        if t == canon.lower() or t in [s.lower() for s in synonyms]:
            return canon, 1.0
    return None, 0.0


def normalize_lifecycle(text: str) -> str:
    t = text.lower()
    if "abgeschlossen" in t:
        return "completed"
    if "abgebrochen" in t:
        return "aborted"
    return "active"


def _num(s: str) -> str:
    return s.replace("'", "").replace("+", "").strip()


def extract_snapshot(path: str, mim: dict) -> dict:
    tables = read_tables(path)
    kv = metadata_kv(tables)
    vocab = mim.get("vocab", {}).get("rag", {})
    prov: dict = {}

    def put(field, value, source, confidence):
        prov[field] = {"value": value, "source": source, "confidence": confidence}

    # -- Metadaten --
    for fid, key in META_MAP.items():
        if kv.get(key):
            put(fid, kv[key], f"Metadaten-Tabelle, Zeile '{key}'", 1.0)
    if kv.get("Projektstatus (Lebenszyklus)"):
        put("lifecycle_state", normalize_lifecycle(kv["Projektstatus (Lebenszyklus)"]),
            "Metadaten-Tabelle, Zeile 'Projektstatus (Lebenszyklus)'", 1.0)

    # -- 8 Ampel-Bereiche --
    status_tables = tables_with_header(tables, ["Bereich", "Status"])
    if status_tables:
        for row in status_tables[0][1:]:
            if len(row) < 2:
                continue
            fid = RAG_LABEL_TO_FIELD.get(row[0])
            if not fid:
                continue
            value, conf = normalize_rag(row[1], vocab)
            if value is not None:
                put(fid, value, f"Tabelle 'Gesamtstatus im Überblick', Zeile '{row[0]}'", conf)

    # -- Kennzahlen: Kosten und Aufwand (gleiche Kopfzeile, Reihenfolge: Kosten, Aufwand) --
    metric_tables = tables_with_header(tables, ["Position", "Ist", "Plan"])
    for fid, table in zip(["cost", "effort"], metric_tables):
        label = "Kosten (CHF)" if fid == "cost" else "Aufwand (Personentage)"
        for row in table[1:]:
            if row and row[0] == "Total" and len(row) >= 4:
                put(fid, {"ist": _num(row[1]), "plan": _num(row[2]), "prognose": _num(row[3])},
                    f"Tabelle '{label}', Zeile 'Total'", 1.0)

    return {"provenance": prov, "fields": {f: v["value"] for f, v in prov.items()}}
