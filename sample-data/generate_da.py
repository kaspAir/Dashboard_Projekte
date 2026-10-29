# -*- coding: utf-8 -*-
"""Erzeugt vorlagengetreue Durchführungsaufträge (DA) je Projekt und
Programmdurchführungsaufträge je Programm, indem die ORIGINAL-HERMES-Vorlage
(sample-data/vorlagen/durchfuehrungsauftrag.docx) je Vorhaben chirurgisch
befüllt wird – Titelseite, Kosten/Aufwand je Phase, Projektorganisation,
Risiken, Konsequenzen, Verbindlichkeiten, Dokument-Protokoll.

Der DA ist die Baseline / Startbedingung → speist später das Portfolio-Soll.
Inhalte sind konsistent zu portfolio-musterstadt.yaml und den PSR-Stammdaten.

Aufruf (Repo-Root):  python sample-data/generate_da.py
"""
import os
import re
import shutil
import sys

import yaml
from docx import Document

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from generate_psr import chf  # noqa: E402
from psr_data_demo import PROJECTS  # noqa: E402

TEMPLATE = os.path.join(HERE, "vorlagen", "durchfuehrungsauftrag.docx")
OUT = os.path.join(HERE, "da-drive")

PHASE_KLASSISCH = [("Initialisierung", 0.10), ("Konzept (klassisch)", 0.20),
                   ("Realisierung (klassisch)", 0.40), ("Einführung (klassisch)", 0.20),
                   ("Abschluss", 0.10)]
PHASE_AGIL = [("Initialisierung", 0.15), ("Umsetzung (agil)", 0.70), ("Abschluss", 0.15)]
PHASE_PROGRAMM = [("Initialisierung", 0.10), ("Realisierung (klassisch)", 0.80), ("Abschluss", 0.10)]
ALL_PHASES = ["Initialisierung", "Konzept (klassisch)", "Realisierung (klassisch)",
              "Einführung (klassisch)", "Umsetzung (agil)", "Abschluss"]
STATUS_DE = {"idee": "Idee", "beantragt": "Beantragt", "freigegeben": "Freigegeben",
             "laufend": "In Durchführung", "zurueckgestellt": "Zurückgestellt",
             "abgeschlossen": "Abgeschlossen", "abgebrochen": "Abgebrochen"}
TRANS = {ord(c): " " for c in "  ​ ﻿   \t"}


def cl(s):
    return re.sub(r"\s+", " ", (s or "").translate(TRANS)).strip()


def _safe(name):
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, "")
    return name.strip()


def kuerzel(name):
    parts = [p for p in name.replace(".", " ").split() if p]
    if not parts:
        return ""
    return (parts[0][0] + parts[-1][:2]).lower() if len(parts) > 1 else parts[0][:3].lower()


def de(d):
    if not d:
        return ""
    y, m, day = (str(d).split("-") + ["01", "01"])[:3]
    return f"{day}.{m}.{y}"


# ---- Füll-Helfer ----------------------------------------------------------
def set_cell(cell, text):
    """Setzt den Zelltext und behält die Formatierung des ersten Runs."""
    p = cell.paragraphs[0]
    if p.runs:
        p.runs[0].text = str(text)
        for r in p.runs[1:]:
            r.text = ""
    else:
        p.add_run(str(text))


def set_title_meta(doc, meta):
    for p in doc.paragraphs:
        if not p.runs:
            continue
        lab = cl(p.runs[0].text)
        if lab not in meta:
            continue
        val = meta[lab]
        last = p.runs[-1]
        if len(p.runs) > 1 and cl(last.text):
            last.text = str(val)                     # Platzhalter-Wert ersetzen (auch wenn = Label)
        else:
            p.add_run("\t\t" + str(val))             # Label-Zeile ohne Wert-Run: Wert anfügen


def find_table(doc, *keys):
    for t in doc.tables:
        hdr = " | ".join(cl(c.text) for c in t.rows[0].cells).lower()
        if all(k.lower() in hdr for k in keys):
            return t
    return None


def fill_phase_table(t, values):
    if not t:
        return
    for row in t.rows[1:]:
        key = cl(row.cells[0].text).rstrip("*").strip()
        if key in values:
            set_cell(row.cells[1], values[key])


def phase_values(total, defs, suffix=""):
    vals = {ph: "–" for ph in ALL_PHASES}
    acc = 0
    for lab, prop in defs:
        v = round(total * prop)
        acc += v
        vals[lab] = f"{chf(v)}{suffix}"
    vals["Total"] = f"{chf(total)}{suffix}"
    return vals


def fill_org(doc, ag, ag_kuerzel, ag_funktion, pl, pl_kuerzel, pl_funktion):
    t = find_table(doc, "Rolle in der Projektorganisation") or find_table(doc, "Projektorganisation")
    if not t:
        return
    for row in t.rows[1:]:
        rolle = cl(row.cells[0].text)
        if rolle.startswith("Auftraggeber"):
            set_cell(row.cells[2], ag); set_cell(row.cells[4], ag_kuerzel); set_cell(row.cells[6], ag_funktion)
        elif rolle.startswith("Projektleiter") or rolle.startswith("Programmleit"):
            set_cell(row.cells[2], pl); set_cell(row.cells[4], pl_kuerzel); set_cell(row.cells[6], pl_funktion)


def fill_risiken(doc, risks, pl):
    t = find_table(doc, "Risikobeschreibung")
    if not t:
        return
    data = [r for r in t.rows[1:] if re.match(r"R\d", cl(r.cells[0].text))]
    sev = [(2, 2), (3, 2), (2, 3)]
    for i, row in enumerate(data):
        if i < len(risks):
            ew, ag = sev[i % len(sev)]
            set_cell(row.cells[1], risks[i]); set_cell(row.cells[2], ew)
            set_cell(row.cells[3], ag); set_cell(row.cells[4], ew * ag)
            set_cell(row.cells[5], "Gegensteuernde Massnahme definiert")
            set_cell(row.cells[6], pl); set_cell(row.cells[7], "")
        else:
            for c in range(1, 8):
                set_cell(row.cells[c], "")


def fill_rows_col(t, texts, col=1, start=1):
    if not t:
        return
    data = [r for r in t.rows[start:] if cl(r.cells[0].text) and cl(r.cells[0].text) != "…"]
    for row, txt in zip(data, texts):
        set_cell(row.cells[col], txt)


def fill_protokoll(doc, version, name, datum, bemerkung):
    for t in doc.tables:
        hdr = " | ".join(cl(c.text) for c in t.rows[0].cells).lower()
        if "version" in hdr and "bemerkungen" in hdr and len(t.rows) > 1:
            if cl(t.rows[1].cells[0].text).startswith(version):
                set_cell(t.rows[1].cells[1], name)
                set_cell(t.rows[1].cells[2], datum)
                set_cell(t.rows[1].cells[3], bemerkung)
                return


def set_doc_title(doc, title):
    for p in doc.paragraphs:
        if (p.style and p.style.name == "Title") and cl(p.text).startswith("Durchführungsauftrag"):
            if p.runs:
                p.runs[0].text = title
                for r in p.runs[1:]:
                    r.text = ""
            return


# ---- Projekt-DA -----------------------------------------------------------
def build_projekt_da(p, soll, zeit, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    a = soll.get("auftrag", {})
    z = zeit or {}
    method = z.get("method", "klassisch")
    status = a.get("status", "freigegeben")
    budget = a.get("budget_soll", p["cost_plan"])
    aufwand = a.get("aufwand_soll", p["eff_plan"])
    freigegeben = status in ("freigegeben", "laufend", "abgeschlossen")

    doc = Document(TEMPLATE)
    set_title_meta(doc, {
        "Projektname / Projektnummer": f"{p['name']} / {p['nummer']}",
        "Bearbeitungsdatum": de(a.get("datum", z.get("start", ""))),
        "Version": "1.0" if freigegeben else "0.1",
        "Autor/-in": p["pl"],
        "Projektleiter/in": p["pl"],
        "Auftraggeber/in": p["ag"],
        "Verwaltungseinheit": p["ve"],
        "Geschäftsbereich": p["gb"],
        "Projektnummer": p["nummer"],
    })
    defs = PHASE_AGIL if method == "agil" else PHASE_KLASSISCH
    fill_phase_table(find_table(doc, "Phase", "Geplant CHF"), phase_values(budget, defs, ".--"))
    fill_phase_table(find_table(doc, "Phase", "Arbeitstage"), phase_values(aufwand, defs))
    fill_org(doc, p["ag"], kuerzel(p["ag"]), p["gb"], p["pl"], kuerzel(p["pl"]), p["ve"])
    fill_risiken(doc, p["risks"], p["pl"])
    fill_rows_col(find_table(doc, "Zeitpunkt", "Beschreibung"), [
        f"Das Projektziel «{p['ziel'][1]}» kann termingerecht erreicht werden.",
        "Verzögerung mit Mehrkosten; der Nutzen tritt später ein.",
        "Handlungsbedarf bleibt ungelöst; das Ziel wird nicht erreicht."])
    vt = find_table(doc, "Verbindlichkeit", "Verantwortlich")
    if vt and len(vt.rows) > 2:
        set_cell(vt.rows[1].cells[1], "Budget")
        set_cell(vt.rows[1].cells[2], f"Genehmigtes Budget {chf(budget)} CHF einhalten.")
        set_cell(vt.rows[1].cells[3], p["pl"])
        set_cell(vt.rows[2].cells[1], "Berichterstattung")
        set_cell(vt.rows[2].cells[2], "Monatlicher Projektstatusbericht (PSR) an den Auftraggeber.")
        set_cell(vt.rows[2].cells[3], p["pl"])
    fill_protokoll(doc, "1.0", p["ag"], de(a.get("datum", "")),
                   "Durchführung freigegeben" if freigegeben else "Entwurf zur Prüfung")
    doc.save(path)


# ---- Programm-DA ----------------------------------------------------------
def build_programm_da(name, ref, soll, zeit, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    a = soll.get("auftrag", {})
    z = zeit or {}
    budget = a.get("budget_soll", 0)
    aufwand = a.get("aufwand_soll", 0)

    doc = Document(TEMPLATE)
    set_doc_title(doc, "Programmdurchführungsauftrag")
    set_title_meta(doc, {
        "Projektname / Projektnummer": f"{name} / {ref}",
        "Bearbeitungsdatum": de(a.get("datum", z.get("start", ""))),
        "Version": "1.0",
        "Autor/-in": "Programmleitung",
        "Projektleiter/in": "N. N. (Programmleitung)",
        "Auftraggeber/in": "Stadtrat Musterstadt",
        "Verwaltungseinheit": "Stabsstelle PMO",
        "Geschäftsbereich": "Programmleitung",
        "Projektnummer": ref,
    })
    fill_phase_table(find_table(doc, "Phase", "Geplant CHF"), phase_values(budget, PHASE_PROGRAMM, ".--"))
    fill_phase_table(find_table(doc, "Phase", "Arbeitstage"), phase_values(aufwand, PHASE_PROGRAMM))
    fill_org(doc, "Stadtrat Musterstadt", "str", "Stadtrat",
             "N. N.", "", "Stabsstelle PMO")
    fill_risiken(doc, ["Abhängigkeiten zwischen den Projekten", "Ressourcenkonkurrenz im Programm"], "Programmleitung")
    fill_rows_col(find_table(doc, "Zeitpunkt", "Beschreibung"), [
        "Die Projekte des Programms können koordiniert umgesetzt werden.",
        "Verzögerung des Programmnutzens; Abhängigkeiten geraten in Verzug.",
        "Die Digitalisierungsziele des Programms werden nicht erreicht."])
    fill_protokoll(doc, "1.0", "Stadtrat Musterstadt", de(a.get("datum", "")),
                   "Programmdurchführung freigegeben")
    doc.save(path)


def _stub(ref, v):
    a = v.get("auftrag", {})
    bereich = v.get("bereich", "")
    return {"name": v.get("titel") or ref, "nummer": ref, "pl": "N. N.",
            "ag": "Ressortleitung " + (bereich.replace("Ressort ", "") or "–"),
            "ve": v.get("einheit", "–"), "gb": bereich or "–",
            "cost_plan": a.get("budget_soll", 0), "eff_plan": a.get("aufwand_soll", 0),
            "ziel": ("Nutzen", (v.get("titel") or "das Vorhaben") + " umsetzen"),
            "risks": ["Datenübernahme aus Altsystem", "Verfügbarkeit Fachressourcen"]}


def main():
    if not os.path.exists(TEMPLATE):
        print("FEHLER: Vorlage fehlt:", TEMPLATE)
        return
    pf = yaml.safe_load(open(os.path.join(HERE, "portfolio-musterstadt.yaml"), encoding="utf-8"))
    soll = {v["ref"]: v for v in pf["vorhaben"]}
    zeit = pf.get("zeitplan", {})
    by_nr = {p["nummer"]: p for p in PROJECTS}

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    n_proj = n_prog = 0
    for ref, v in soll.items():
        if v.get("art") == "programm":
            name = v.get("titel") or ref
            path = os.path.join(OUT, "Programme", _safe(name), "Programmdurchfuehrungsauftrag.docx")
            build_programm_da(name, ref, v, zeit.get(ref), path)
            n_prog += 1
        else:
            p = by_nr.get(ref) or _stub(ref, v)
            prog = v.get("programm")
            if prog:
                folder = os.path.join(OUT, "Programme", _safe(prog), _safe(p["name"]))
            else:
                folder = os.path.join(OUT, "Fachbereiche", _safe(p["gb"]), _safe(p["name"]))
            build_projekt_da(p, v, zeit.get(ref), os.path.join(folder, "Durchfuehrungsauftrag.docx"))
            n_proj += 1

    print(f"Durchführungsaufträge (vorlagengetreu) in {OUT}")
    print(f"  {n_proj} Projekt-DA, {n_prog} Programm-DA")


if __name__ == "__main__":
    main()
