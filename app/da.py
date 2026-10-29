"""Durchführungsauftrag (DA) — Extraktion und Zugriff.

Der DA ist die Baseline / Startbedingung eines Vorhabens (genehmigtes Budget und
Aufwand je Phase, Organisation/Personen, Risiken, Ziele). Er wird – wie die PSR –
aus Dokumenten eingelesen; die Ingestion unterscheidet PSR und DA inhaltsbasiert.

extract_da() liest einen DA (.docx) in ein kanonisches Record. is_da() erkennt,
ob ein Dokument ein Durchführungsauftrag ist. load_da() liefert die DA je Mandant
(Live-Store data/da/<mandant>.yaml, sonst committeter Seed sample-data/da-<id>.yaml).
"""
from __future__ import annotations

import os
import re

import yaml

from .extraction.reader import read_paragraphs, read_tables

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DA_DIR = os.path.join(ROOT, "data", "da")
SAMPLE = os.path.join(ROOT, "sample-data")
SEEDS = {"musterstadt": os.path.join(SAMPLE, "da-musterstadt.yaml")}

PHASE_KEYS = ["Initialisierung", "Konzept (klassisch)", "Realisierung (klassisch)",
              "Einführung (klassisch)", "Umsetzung (agil)", "Abschluss",
              "Programminitialisierung", "Programmdurchführung", "Programmabschluss"]
META_LABELS = {
    "Projektleiter/in": "pl", "Auftraggeber/in": "ag", "Verwaltungseinheit": "einheit",
    "Geschäftsbereich": "bereich", "Projektnummer": "ref", "Bearbeitungsdatum": "datum",
    "Version": "version",
}


def _cl(s):
    trans = {ord(c): " " for c in "  ​ ﻿   \t"}
    return re.sub(r"\s+", " ", (s or "").translate(trans)).strip()


def _num(s):
    s = re.sub(r"[^\d]", "", str(s or ""))
    return int(s) if s else None


def _header(tbl):
    return " | ".join(_cl(c.text) for c in tbl.rows[0].cells) if tbl and tbl.rows else ""


def _find(tables, *keys):
    for t in tables:
        h = _header(t).lower()
        if all(k.lower() in h for k in keys):
            return t
    return None


def _rows(tbl, cols):
    """Datenzeilen als Dicts; cols = Liste von Ausgabeschlüsseln je Spaltenindex."""
    out = []
    if not tbl:
        return out
    for row in tbl.rows[1:]:
        cells = [_cl(c.text) for c in row.cells]
        # zusammengeführte Zellen entdoppeln
        dedup = []
        for x in cells:
            if not dedup or dedup[-1] != x:
                dedup.append(x)
        if not any(dedup) or dedup[0] in ("…", "-", "–"):
            continue
        rec = {cols[i]: (dedup[i] if i < len(dedup) else "") for i in range(len(cols))}
        out.append(rec)
    return out


def _phasen(tbl):
    vals = {}
    if not tbl:
        return vals, None
    total = None
    for row in tbl.rows[1:]:
        key = _cl(row.cells[0].text).rstrip("*").strip()
        val = _num(row.cells[1].text) if len(row.cells) > 1 else None
        if key == "Total":
            total = val
        elif key in PHASE_KEYS and val is not None:
            vals[key] = val
    return vals, total


def is_da(path):
    """Inhaltsbasiert: ein DA trägt den Titel 'Durchführungsauftrag' und eine
    Phasen-Kostentabelle – und KEINE PSR-Statusampel-Tabelle."""
    try:
        paras = read_paragraphs(path)
    except Exception:
        return False
    head = " ".join(_cl(p) for p in paras[:3]).lower()
    if "durchführungsauftrag" not in head:
        return False
    tables = read_tables_objs(path)
    return _find(tables, "Phase", "Geplant") is not None


def read_tables_objs(path):
    # python-docx Table-Objekte (read_tables liefert Strings) – hier direkt Document
    from docx import Document
    return Document(path).tables


def extract_da(path):
    from docx import Document
    doc = Document(path)
    paras = [_cl(p) for p in [pp.text for pp in doc.paragraphs]]
    tables = doc.tables
    title = (paras[0] if paras else "").lower()
    typ = "programm" if "programm" in title else "projekt"

    rec = {"typ": typ, "ref": "", "name": "", "status": "", "version": "", "datum": "",
           "ag": "", "pl": "", "einheit": "", "bereich": "", "programm": ""}

    # Untertitel = prominenter Name "Name (REF)"
    for t in paras[1:6]:
        m = re.match(r"(.+?)\s*\(([^)]+)\)\s*$", t)
        if t and m:
            rec["name"] = m.group(1).strip()
            rec["ref"] = rec["ref"] or m.group(2).strip()
            break

    if typ == "projekt":
        for t in paras:
            for lab, key in META_LABELS.items():
                if t.startswith(lab + " "):
                    rec[key] = t[len(lab):].strip()
        rec["status"] = "Freigegeben"
    else:
        meta = _find(tables, "Klassifizierung")
        mm = {"Programmnummer": "ref", "Programmleiter": "pl", "Auftraggeber": "ag",
              "Version": "version", "Datum": "datum"}
        if meta:
            for row in meta.rows:
                k = _cl(row.cells[0].text)
                if k in mm and len(row.cells) > 1:
                    rec[mm[k]] = _cl(row.cells[1].text)

    # Kosten / Aufwand je Phase
    rec["kosten_phasen"], rec["budget_soll"] = _phasen(_find(tables, "Phase", "Geplant CHF"))
    rec["aufwand_phasen"], rec["aufwand_soll"] = _phasen(_find(tables, "Phase", "Arbeitstage"))
    rec["method"] = "agil" if rec["kosten_phasen"].get("Umsetzung (agil)") else "klassisch"

    # Organisation
    org = _find(tables, "Rolle in der Projektorganisation") or _find(tables, "Rolle in der Programmorganisation")
    rec["organisation"] = _rows(org, ["rolle", "name", "kuerzel", "funktion"]) if org else []

    # Ressourcen (Rolle/Person/Aufwand) – nur Projekt-DA
    res = _find(tables, "Rolle", "Person", "Aufwand")
    rec["ressourcen"] = [{"rolle": r["rolle"], "person": r["person"], "pt": _num(r["pt"])}
                         for r in _rows(res, ["rolle", "person", "pt"]) if r.get("rolle") != "Total"] if res else []

    # Risiken
    rk = _find(tables, "Risikobeschreibung")
    rec["risiken"] = _rows(rk, ["nr", "risiko", "ew", "ag", "rz", "massnahme", "verantwortlich", "termin"]) if rk else []

    # Ziele (Projekt: Zielbeschreibung; Programm: erste Ziele-Tabelle mit Messgrösse)
    zt = _find(tables, "Zielbeschreibung") or _find(tables, "Beschreibung", "Messgr")
    rec["ziele"] = _rows(zt, ["nr", "kategorie", "beschreibung", "messgroesse", "prioritaet", "prognose"]) if zt else []

    return rec


# ---- Store-Zugriff --------------------------------------------------------
def resolve_da(mandant_id=None):
    mid = mandant_id or ""
    live = os.path.join(DA_DIR, f"{mid}.yaml")
    if os.path.exists(live):
        return live, "Ingestion (Live)"
    seed = SEEDS.get(mid)
    if seed and os.path.exists(seed):
        return seed, "Seed"
    return None, "kein DA"


def load_da(mandant_id=None):
    path, _ = resolve_da(mandant_id)
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        recs = yaml.safe_load(f) or []
    return {str(r.get("ref")): r for r in recs if r.get("ref")}


def get_da(mandant_id, ref):
    return load_da(mandant_id).get(str(ref))


def write_da_store(records, mandant_id):
    os.makedirs(DA_DIR, exist_ok=True)
    path = os.path.join(DA_DIR, f"{mandant_id}.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(records, f, allow_unicode=True, sort_keys=False)
    return path
