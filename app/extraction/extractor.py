"""Deterministische Extraktion aus einem PSR (.docx) -> kanonische Werte + Provenienz.

MIM-gesteuert bei der Normalisierung der Ampeln (vocab.rag). Jeder extrahierte Wert
trägt Fundstelle (source) und Konfidenz. Wird ein Wert nicht sicher erkannt, bleibt
das Feld leer (kein Raten).
"""
from __future__ import annotations

from .reader import (metadata_kv, read_paragraphs, read_tables,
                     tables_with_header, text_after_heading)

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

# Ampel-Label -> interner Dimensions-Schlüssel (für die Erläuterungs-Spalte).
RAG_LABEL_TO_DIM = {
    "Gesamtbeurteilung": "gesamt", "Termine": "termine", "Kosten": "kosten",
    "Personalaufwand": "personalaufwand", "Ergebnisse": "ergebnisse",
    "Projektziele": "projektziele", "Projektrisiken": "projektrisiken",
    "Einhaltung Governance": "governance",
}

META_MAP = {
    "project_name": "Projektname",
    "project_number": "Projektnummer",
    "report_date": "Bearbeitungsdatum",
    "project_lead": "Projektleiter/in",
    "sponsor": "Auftraggeber/in",
    "org_unit": "Verwaltungseinheit",
    "business_area": "Geschäftsbereich",
    "programm": "Programm",
    "phase": "Projektphase",
}


def normalize_method(text: str) -> str:
    """Vorgehensmodell -> 'agil' | 'klassisch' (Standard: klassisch)."""
    t = text.lower()
    if any(w in t for w in ("agil", "scrum", "safe", "kanban")):
        return "agil"
    return "klassisch"


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


def _col_index(header, *subs):
    """Spaltenindex der ersten Kopfzelle, die einen der Teilstrings enthält (sonst None)."""
    low = [h.lower() for h in header]
    for sub in subs:
        for i, h in enumerate(low):
            if sub in h:
                return i
    return None


def _rows_as_dicts(table, colmap):
    """Datenzeilen einer Tabelle als Dicts; Spalten per Kopfzeilen-Teilstring zugeordnet.

    colmap: {ausgabe_schlüssel: (teilstring, ...)}. Leere und Platzhalter-Zeilen ('–')
    werden übersprungen. Nur das wird übernommen, was wirklich dasteht (kein Raten).
    """
    if not table:
        return []
    header = table[0]
    idx = {k: _col_index(header, *subs) for k, subs in colmap.items()}
    out = []
    for row in table[1:]:
        cells = [c.strip() for c in row]
        if not any(cells) or (cells and cells[0] in ("–", "-")):
            continue
        rec = {k: (cells[i] if i is not None and i < len(cells) else "") for k, i in idx.items()}
        out.append(rec)
    return out


def extract_snapshot(path: str, mim: dict) -> dict:
    tables = read_tables(path)
    paras = read_paragraphs(path)
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
    if kv.get("Vorgehensmodell"):
        put("method", normalize_method(kv["Vorgehensmodell"]),
            "Metadaten-Tabelle, Zeile 'Vorgehensmodell'", 1.0)

    # -- 8 Ampel-Bereiche (+ Erläuterungen je Bereich, wenn vorhanden) --
    status_tables = tables_with_header(tables, ["Bereich", "Status"])
    notes: dict = {}
    if status_tables:
        for row in status_tables[0][1:]:
            if len(row) < 2:
                continue
            label = row[0]
            fid = RAG_LABEL_TO_FIELD.get(label)
            if not fid:
                continue
            value, conf = normalize_rag(row[1], vocab)
            if value is not None:
                put(fid, value, f"Tabelle 'Gesamtstatus im Überblick', Zeile '{label}'", conf)
            if len(row) >= 3 and row[2].strip():
                notes[RAG_LABEL_TO_DIM[label]] = row[2].strip()
    if notes:
        put("status_notes", notes,
            "Tabelle 'Gesamtstatus im Überblick', Spalte 'Erläuterungen wenn nicht grün'", 1.0)

    # -- Gesamtbeurteilung / Fazit (Fliesstext) --
    fazit = text_after_heading(paras, "Gesamtbeurteilung / Fazit")
    if fazit:
        put("fazit", fazit, "Absatz 'Gesamtbeurteilung / Fazit'", 1.0)

    # -- Kennzahlen: Kosten und Aufwand (gleiche Kopfzeile, Reihenfolge: Kosten, Aufwand) --
    metric_tables = tables_with_header(tables, ["Position", "Ist", "Plan"])
    for fid, table in zip(["cost", "effort"], metric_tables):
        label = "Kosten (CHF)" if fid == "cost" else "Aufwand (Personentage)"
        for row in table[1:]:
            if row and row[0] == "Total" and len(row) >= 4:
                put(fid, {"ist": _num(row[1]), "plan": _num(row[2]), "prognose": _num(row[3])},
                    f"Tabelle '{label}', Zeile 'Total'", 1.0)

    # -- Prognose der Zielerreichung --
    ziel_tables = tables_with_header(tables, ["Zielformulierung", "Prognose"])
    if ziel_tables:
        objectives = _rows_as_dicts(ziel_tables[0], {
            "nr": ("nr",), "kategorie": ("kategorie",),
            "ziel": ("zielformulierung",), "prognose": ("prognose",)})
        if objectives:
            put("objectives", objectives, "Tabelle 'Prognose der Zielerreichung'", 1.0)

    # -- Meilensteine: erreicht (0) und geplant (1), gleiche Kopfzeile --
    ms_tables = tables_with_header(tables, ["Meilenstein", "Plan", "Ist"])
    ms_cols = {"name": ("meilenstein",), "plan": ("plan",),
               "prognose": ("prognose",), "ist": ("ist",)}
    if len(ms_tables) >= 1:
        done = _rows_as_dicts(ms_tables[0], ms_cols)
        if done:
            put("milestones_done", done, "Tabelle 'Erreichte Meilensteine'", 1.0)
    if len(ms_tables) >= 2:
        nxt = _rows_as_dicts(ms_tables[1], ms_cols)
        if nxt:
            put("milestones_next", nxt, "Tabelle 'Geplante Meilensteine'", 1.0)

    # -- Sprints / Inkremente (agile Projekte): abgeschlossen (0), geplant (1) --
    sprint_tables = tables_with_header(tables, ["Sprint", "Zeitraum"])
    sp_cols = {"sprint": ("sprint",), "zeitraum": ("zeitraum",),
               "inhalt": ("inkrement", "ziel", "inhalt"),
               "points": ("story", "points")}
    if len(sprint_tables) >= 1:
        done = _rows_as_dicts(sprint_tables[0], sp_cols)
        if done:
            put("sprints_done", done, "Tabelle 'Abgeschlossene Sprints'", 1.0)
    if len(sprint_tables) >= 2:
        nxt = _rows_as_dicts(sprint_tables[1], sp_cols)
        if nxt:
            put("sprints_next", nxt, "Tabelle 'Nächste Sprints'", 1.0)

    # -- Probleme und Massnahmen --
    issue_tables = tables_with_header(tables, ["Problembeschreibung", "Massnahme"])
    if issue_tables:
        issues = _rows_as_dicts(issue_tables[0], {
            "nr": ("nr",), "problem": ("problembeschreibung",),
            "massnahme": ("massnahme",), "verantwortlich": ("verantwortlich",),
            "termin": ("termin",)})
        if issues:
            put("issues", issues, "Tabelle 'Probleme und Massnahmen'", 1.0)

    # -- Risiken --
    risk_tables = tables_with_header(tables, ["Risikobeschreibung", "EW"])
    if risk_tables:
        risks = _rows_as_dicts(risk_tables[0], {
            "nr": ("nr",), "risiko": ("risikobeschreibung",),
            "ew": ("ew",), "ag": ("ag",), "rz": ("rz",),
            "verantwortlich": ("verantwortlich",)})
        if risks:
            put("risks", risks, "Tabelle 'Risiken'", 1.0)

    return {"provenance": prov, "fields": {f: v["value"] for f, v in prov.items()}}
