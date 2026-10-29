# -*- coding: utf-8 -*-
"""Erzeugt vorlagengetreue, VOLLSTÄNDIG ausgefüllte Durchführungsaufträge (DA) je
Projekt und Programmdurchführungsaufträge je Programm für die Stadt Musterstadt.

Befüllt die Original-HERMES-Vorlagen chirurgisch:
  - sample-data/vorlagen/durchfuehrungsauftrag.docx            (Projekt-DA)
  - sample-data/vorlagen/programmdurchfuehrungsauftrag.docx    (Programm-DA)

Alle Kapitel werden gefüllt: Titelseite/Metadaten, Fliesstext je Abschnitt
(HERMES-2022-konform), Kosten/Aufwand je Phase, Organisation (erfundene Personen),
Ziele/Rahmenbedingungen/Abgrenzungen/Strategiebezug/Vorgaben, Meilensteine,
Risiken, Konsequenzen, Verbindlichkeiten, Protokoll. Vorlagen-Hilfetexte werden
entfernt. Namen/Rollen sind fiktiv; rechtliche Grundlagen bleiben generisch
(keine erfundenen Fundstellen).

Aufruf (Repo-Root):  python sample-data/generate_da.py
"""
import os
import re
import shutil
import sys

import yaml
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))   # Projektwurzel für 'app'-Import
from generate_psr import chf  # noqa: E402
from psr_data_demo import PROJECTS  # noqa: E402

VORLAGEN = os.path.join(HERE, "vorlagen")
TPL_PROJEKT = os.path.join(VORLAGEN, "durchfuehrungsauftrag.docx")
TPL_PROGRAMM = os.path.join(VORLAGEN, "programmdurchfuehrungsauftrag.docx")
OUT = os.path.join(HERE, "da-drive")

PHASE_KLASSISCH = [("Initialisierung", 0.10), ("Konzept (klassisch)", 0.20),
                   ("Realisierung (klassisch)", 0.40), ("Einführung (klassisch)", 0.20),
                   ("Abschluss", 0.10)]
PHASE_AGIL = [("Initialisierung", 0.15), ("Umsetzung (agil)", 0.70), ("Abschluss", 0.15)]
PHASE_PROGRAMM = [("Programminitialisierung", 0.10), ("Programmdurchführung", 0.80),
                  ("Programmabschluss", 0.10)]
ALL_PHASES = ["Initialisierung", "Konzept (klassisch)", "Realisierung (klassisch)",
              "Einführung (klassisch)", "Umsetzung (agil)", "Abschluss"]
STATUS_DE = {"idee": "Idee", "beantragt": "Beantragt", "freigegeben": "Freigegeben",
             "laufend": "In Durchführung", "zurueckgestellt": "Zurückgestellt",
             "abgeschlossen": "Abgeschlossen", "abgebrochen": "Abgebrochen"}
TRANS = {ord(c): " " for c in "  ​ ﻿   \t"}

# Fiktives Personal der Stadt Musterstadt (Name, Kürzel) je Rolle/Ressort.
AG_PERSON = {
    "Ressort Finanzen": ("Dr. Thomas Widmer", "twi", "Ressortleiter Finanzen"),
    "Ressort Bau & Umwelt": ("Roland Hofer", "rho", "Ressortleiter Bau & Umwelt"),
    "Ressort Bildung": ("Sandra Brunner", "sbr", "Ressortleiterin Bildung"),
    "Ressort Soziales & Gesundheit": ("Ursula Graf", "ugr", "Ressortleiterin Soziales"),
    "Ressort Sicherheit": ("Werner Steiner", "wst", "Ressortleiter Sicherheit"),
}
ISDS = ("Eva Schmid", "esc", "ISDS-Beauftragte, Stabsstelle")
PMO = ("Clara Meier", "cme", "Leiterin PMO")
AUSSCHUSS = ("Felix Baumann", "fba", "Vertreter Stadtrat")
ANWENDER = ("Gina Roth", "gro", "Anwendervertretung Fachbereich")

# Personen-Pools je Projektrolle – über die Projekte rotierend verteilt, damit die
# Auslastung je Person realistisch ist (manche Personen auf mehreren Projekten).
POOL_BA = ["Gina Roth", "Sabine Vogt", "Marco Lang"]
POOL_DEV = ["Daniel Huber", "Nina Weber", "Olaf Ziegler", "Paula Brandt"]
POOL_TEST = ["Hans Vogel", "Rita Suter"]
POOL_EINF = ["Beat Küng", "Timo Frei"]


def cl(s):
    return re.sub(r"\s+", " ", (s or "").translate(TRANS)).strip()


def _safe(name):
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, "")
    return name.strip()


def kuerzel(name):
    parts = [p for p in name.replace(".", " ").split() if p and p[0].isupper()]
    if not parts:
        return ""
    return (parts[0][0] + parts[-1][:2]).lower()


def de(d):
    if not d:
        return ""
    y, m, day = (str(d).split("-") + ["01", "01"])[:3]
    return f"{day}.{m}.{y}"


def is_heading(p):
    st = p.style.name or ""
    return "berschrift" in st or st.startswith("Heading") or st == "Title"


# ---- Füll-Helfer ----------------------------------------------------------
def set_cell(cell, text):
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
        last = p.runs[-1]
        if len(p.runs) > 1 and cl(last.text):
            last.text = str(meta[lab])
        else:
            p.add_run("\t\t" + str(meta[lab]))


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
    vals = {ph: "–" for ph in ALL_PHASES + [p[0] for p in PHASE_PROGRAMM]}
    for lab, prop in defs:
        vals[lab] = f"{chf(round(total * prop))}{suffix}"
    vals["Total"] = f"{chf(total)}{suffix}"
    return vals


def fill_rows_col(t, texts, col=1, start=1):
    if not t:
        return
    data = [r for r in t.rows[start:] if cl(r.cells[0].text) and cl(r.cells[0].text) != "…"]
    for row, txt in zip(data, texts):
        set_cell(row.cells[col], txt)


def fill_risiken(t, risks, pl):
    if not t:
        return
    data = [r for r in t.rows[1:] if re.match(r"R\d", cl(r.cells[0].text))]
    sev = [(2, 2), (3, 2), (2, 3), (3, 3)]
    for i, row in enumerate(data):
        if i < len(risks):
            ew, ag = sev[i % len(sev)]
            vals = ["", risks[i], ew, ag, ew * ag, "Gegensteuernde Massnahme definiert", pl, ""]
            for c in range(1, min(8, len(row.cells))):
                set_cell(row.cells[c], vals[c])
        else:
            for c in range(1, min(8, len(row.cells))):
                set_cell(row.cells[c], "")


def insert_paras_after(heading, texts, style=None):
    anchor = heading._p
    out = []
    for t in texts:
        new = OxmlElement("w:p")
        anchor.addnext(new)
        anchor = new
        np = Paragraph(new, heading._parent)
        if style:
            try:
                np.style = style
            except Exception:
                pass
        np.add_run(t)
        out.append(np)
    return out


def fill_section(doc, heading_text, texts):
    """Fügt Fliesstext direkt nach der (ersten) passenden Überschrift ein.
    Gibt die eingefügten Absätze zurück (für nachgelagerte Tabellen)."""
    if isinstance(texts, str):
        texts = [texts]
    for p in doc.paragraphs:
        if is_heading(p) and cl(p.text).lower().startswith(heading_text.lower()):
            return insert_paras_after(p, texts, style="Normal")
    return []


def insert_table_after(doc, anchor_para, headers, rows):
    """Erzeugt eine Tabelle und verschiebt sie direkt hinter anchor_para."""
    t = doc.add_table(rows=1, cols=len(headers))
    try:
        t.style = "Table Grid"
    except Exception:
        pass
    for i, h in enumerate(headers):
        set_cell(t.rows[0].cells[i], h)
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            set_cell(cells[i], v)
    anchor_para._p.addnext(t._tbl)
    return t


def insert_subtitle(doc, text):
    for p in doc.paragraphs:
        if p.style and p.style.name == "Title":
            paras = insert_paras_after(p, [text], style=None)
            if paras and paras[0].runs:
                r = paras[0].runs[0]
                r.bold = True
                r.font.size = Pt(15)
            return


def set_sdt(doc, alias, text):
    for sdt in doc.element.findall(".//" + qn("w:sdt")):
        pr = sdt.find(qn("w:sdtPr"))
        al = pr.find(qn("w:alias")) if pr is not None else None
        if al is not None and al.get(qn("w:val")) == alias:
            ts = sdt.findall(".//" + qn("w:t"))
            if ts:
                ts[0].text = text
                for n in ts[1:]:
                    n.text = ""
            return


def remove_placeholder_rows(doc):
    """Entfernt leere '…'-Platzhalterzeilen aus den Tabellen (nicht die Kopfzeile)."""
    for t in doc.tables:
        for row in list(t.rows[1:]):
            if cl(row.cells[0].text) == "…":
                row._tr.getparent().remove(row._tr)


def remove_guidance(doc):
    """Entfernt Hilfetexte (Stil 'Hilfstext' oder durchgehend kursive Absätze) und
    '…'-Platzhalter – aber nie Überschriften oder eingefügten Fliesstext."""
    for p in list(doc.paragraphs):
        if is_heading(p):
            continue
        st = p.style.name or ""
        if "Hilfstext" in st or cl(p.text) == "…":
            p._p.getparent().remove(p._p)
            continue
        runs = [r for r in p.runs if cl(r.text)]
        if runs and all(r.italic or (r.font is not None and r.font.italic) for r in runs):
            p._p.getparent().remove(p._p)


def set_doc_title(doc, title):
    for p in doc.paragraphs:
        if p.style and p.style.name == "Title" and cl(p.text).startswith("Durchführungsauftrag"):
            if p.runs:
                p.runs[0].text = title
                for r in p.runs[1:]:
                    r.text = ""
            return


# ---- Projekt-DA -----------------------------------------------------------
def build_projekt_da(p, soll, zeit, path, pi=0):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    a = soll.get("auftrag", {})
    z = zeit or {}
    method = z.get("method", "klassisch")
    status = a.get("status", "freigegeben")
    budget = a.get("budget_soll", p["cost_plan"])
    aufwand = a.get("aufwand_soll", p["eff_plan"])
    freigegeben = status in ("freigegeben", "laufend", "abgeschlossen")
    vm = ("agile Umsetzung mit Releases und Inkrementen" if method == "agil"
          else "klassisches Vorgehen mit den Phasen Konzept, Realisierung und Einführung")
    ag_name, ag_k, ag_f = AG_PERSON.get(p["gb"], (p["ag"], kuerzel(p["ag"]), p["gb"]))

    doc = Document(TPL_PROJEKT)
    insert_subtitle(doc, f"{p['name']} ({p['nummer']})")

    # Fliesstext je Kapitel (vor dem Entfernen der Platzhalter einfügen)
    fill_section(doc, "Ziel und Zweck", [
        f"Dieser Durchführungsauftrag bildet die verbindliche Grundlage für die Durchführung "
        f"des Projekts «{p['name']}» ({p['nummer']}) der Stadt Musterstadt. Er hält Ausgangslage, "
        f"Ziele, Lösung, Kosten, Organisation und Risiken als Startbedingungen fest."])
    fill_section(doc, "Ausgangslage und Handlungsbedarf", [
        f"Die Organisationseinheit {p['ve']} erbringt heute die Leistungen im Bereich «{p['ziel'][0]}» mit Mitteln, die den "
        f"Anforderungen an Effizienz, Servicequalität und Nachvollziehbarkeit nicht mehr genügen. "
        f"Es besteht Handlungsbedarf, um {p['ziel'][1].lower()}.",
        "Eine Standortbestimmung hat den Verbesserungsbedarf bestätigt; das Vorhaben wurde in der "
        "Initialisierung als umsetzungswürdig beurteilt."])
    lz = fill_section(doc, "Lösungsziele", [
        "Die Lösungsziele werden gemessen und über den Projektverlauf nachverfolgt:"])
    if lz:
        insert_table_after(doc, lz[-1],
                           ["Nr.", "Kategorie", "Zielbeschreibung", "Messgrösse", "Priorität", "Prognose"],
                           [["LZ-01", p["ziel"][0], p["ziel"][1], "Grad der Zielerreichung in %", "hoch", "on track"],
                            ["LZ-02", "Qualität", "Medienbruchfreie, datenschutzkonforme Lösung",
                             "Abnahmekriterien erfüllt", "mittel", "on track"]])
    fill_section(doc, "Projektvorgehensziele", [
        f"Das Projekt wird nach HERMES 2022 geführt ({vm}). Qualität, Termine und Kosten werden über "
        "die Phasenfreigaben gesteuert; die Projektleitung berichtet monatlich mittels Projektstatusbericht (PSR)."])
    fill_section(doc, "Klassische / agile Vorgehensweise", [
        f"Gewähltes Vorgehen: {'Agil (Scrum)' if method == 'agil' else 'Klassisch (HERMES)'} – "
        f"{vm}. Die Wahl ergibt sich aus Umfang, Unsicherheit und Lieferkadenz des Vorhabens."])
    fill_section(doc, "Szenario", [
        "Umgesetzt wird das Zielszenario mit vollständiger Ablösung der bisherigen Lösung. Alternative "
        "Szenarien (Teilablösung, Zukauf) wurden in der Initialisierung geprüft und als weniger "
        "wirtschaftlich beurteilt."])
    fill_section(doc, "Weitere Projektvorgehensziele", [
        "Wissenstransfer in die Linie, durchgängige Dokumentation und ein geregelter Betriebsübergang "
        "an die Stammorganisation sind sicherzustellen."])
    fill_section(doc, "Rahmenbedingungen, Strategiebezug und Abgrenzungen", [
        f"Das Projekt zahlt auf die Digitalisierungs- und Servicestrategie der Stadt Musterstadt ein. "
        f"Massgebliche Rahmenbedingungen sind das genehmigte Budget ({chf(budget)} CHF), der Endtermin "
        f"und die Vorgaben der Stammorganisation. Nicht Teil des Projekts sind der Dauerbetrieb der "
        "Lösung sowie Anpassungen an angrenzenden Fachverfahren."])
    fill_section(doc, "Zusammenfassende Lösungsbeschreibung", [
        f"Umgesetzt wird eine Fachlösung mit dem Ziel: {p['ziel'][1]}. Bestehende Systeme werden über "
        "standardisierte Schnittstellen angebunden; die Einführung erfolgt begleitet durch Kommunikation, "
        "Schulung und Change-Management."])
    fill_section(doc, "Rechtliche Grundlagen", [
        "Massgebend sind die einschlägigen kommunalen und kantonalen Rechtsgrundlagen (u. a. Gemeinde- "
        "und Organisationsrecht sowie die Datenschutzgesetzgebung). Die konkreten Erlasse sind mit dem "
        "Rechtsdienst der Stadt Musterstadt vor Umsetzung zu verifizieren."])
    rz = fill_section(doc, "Ressourcen- und Hilfsmittelbedarf", [
        f"Der Personalaufwand beträgt rund {chf(aufwand)} Personentage über die Projektlaufzeit, verteilt "
        "auf die folgenden Rollen und Personen (Baseline für die Ressourcenplanung):"])
    if rz:
        res = [("Projektleitung", p["pl"], round(aufwand * 0.15)),
               ("Business-/Fachanalyse", POOL_BA[pi % len(POOL_BA)], round(aufwand * 0.20)),
               ("Realisierung / Entwicklung", POOL_DEV[pi % len(POOL_DEV)], round(aufwand * 0.40)),
               ("Test & Qualitätssicherung", POOL_TEST[pi % len(POOL_TEST)], round(aufwand * 0.15)),
               ("Einführung & Schulung", POOL_EINF[pi % len(POOL_EINF)], round(aufwand * 0.10))]
        rows = [[rolle, pers, pt] for rolle, pers, pt in res]
        rows.append(["Total", "", sum(r[2] for r in res)])
        insert_table_after(doc, rz[-1], ["Rolle", "Person", "Geplanter Aufwand (PT)"], rows)
    fill_section(doc, "Kosten / Nutzen / Wirtschaftlichkeit", [
        f"Das genehmigte Projektbudget beträgt {chf(budget)} CHF. Dem stehen Effizienzgewinne, bessere "
        "Servicequalität und Reduktion manueller Arbeit gegenüber; die Wirtschaftlichkeit wird im "
        "Projektverlauf anhand der Nutzenziele überprüft."])
    fill_section(doc, "Projektplanung", [
        f"Geplanter Start: {de(z.get('start', a.get('datum', '')))}, geplantes Ende: {de(z.get('ende', ''))}. "
        "Die Phasenplanung folgt den HERMES-Phasen mit Entscheidungs-Meilensteinen je Phasenübergang."])
    fill_section(doc, "Vorgehensweise", [
        f"Die Umsetzung erfolgt {vm}. Ergebnisse werden phasenweise abgenommen; offene Punkte und "
        "Massnahmen werden im PSR nachgeführt."])

    # Titelseite / Metadaten
    set_title_meta(doc, {
        "Projektname / Projektnummer": f"{p['name']} / {p['nummer']}",
        "Bearbeitungsdatum": de(a.get("datum", z.get("start", ""))),
        "Version": "1.0" if freigegeben else "0.1",
        "Autor/-in": PMO[0],
        "Projektleiter/in": p["pl"],
        "Auftraggeber/in": ag_name,
        "Verwaltungseinheit": p["ve"],
        "Geschäftsbereich": p["gb"],
        "Projektnummer": p["nummer"],
        "Innenauftragsnr.": f"IA-{p['nummer']}",
    })
    set_sdt(doc, "Dokument Status", "Freigegeben" if freigegeben else "In Arbeit")

    # Kennzahlen + Organisation + Tabellen
    defs = PHASE_AGIL if method == "agil" else PHASE_KLASSISCH
    fill_phase_table(find_table(doc, "Phase", "Geplant CHF"), phase_values(budget, defs, ".--"))
    fill_phase_table(find_table(doc, "Phase", "Arbeitstage"), phase_values(aufwand, defs))

    org = find_table(doc, "Rolle in der Projektorganisation")
    if org:
        rollen = {
            "Auftraggeber": (ag_name, ag_k, ag_f),
            "Projektausschuss": (AUSSCHUSS[0], AUSSCHUSS[1], AUSSCHUSS[2]),
            "Projektleiter": (p["pl"], kuerzel(p["pl"]), f"Projektleitung, {p['ve']}"),
            "ISDS": ISDS,
            "Anwendervertreter": (ANWENDER[0], ANWENDER[1], f"Anwendervertretung {p['ve']}"),
        }
        for row in org.rows[1:]:
            rolle = cl(row.cells[0].text)
            for key, (nm, ku, fu) in rollen.items():
                if rolle.startswith(key):
                    set_cell(row.cells[2], nm)
                    set_cell(row.cells[4], ku)
                    set_cell(row.cells[6], fu)
                    break

    fill_risiken(find_table(doc, "Risikobeschreibung"), p["risks"], p["pl"])
    fill_rows_col(find_table(doc, "Zeitpunkt", "Beschreibung"), [
        f"Das Projektziel «{p['ziel'][1]}» kann termingerecht erreicht werden.",
        "Verzögerung mit Mehrkosten; der Nutzen tritt später ein.",
        "Handlungsbedarf bleibt ungelöst; das Ziel wird nicht erreicht."])
    vt = find_table(doc, "Verbindlichkeit", "Verantwortlich")
    if vt and len(vt.rows) > 2:
        set_cell(vt.rows[1].cells[1], "Budget und Termine")
        set_cell(vt.rows[1].cells[2], f"Genehmigtes Budget {chf(budget)} CHF und Endtermin einhalten.")
        set_cell(vt.rows[1].cells[3], p["pl"])
        set_cell(vt.rows[2].cells[1], "Berichterstattung")
        set_cell(vt.rows[2].cells[2], "Monatlicher Projektstatusbericht (PSR) an den Auftraggeber.")
        set_cell(vt.rows[2].cells[3], p["pl"])

    ref = find_table(doc, "Nr.", "Name", "Nummer")
    if ref and len(ref.rows) > 1:
        set_cell(ref.rows[1].cells[1], "Projektinitialisierungsauftrag")
        set_cell(ref.rows[1].cells[2], p["nummer"])
    for t in doc.tables:                                   # Mitgeltende Unterlagen (Name|Nummer/Link, 2 Sp.)
        h = [cl(c.text) for c in t.rows[0].cells]
        if len(h) == 2 and h[0] == "Name" and "Nummer" in h[1] and len(t.rows) > 1:
            set_cell(t.rows[1].cells[0], "Projektmanagementplan")
            set_cell(t.rows[1].cells[1], "–")
            break
    hm = find_table(doc, "Hilfsmittel", "Beschreibung")
    if hm:
        fill_rows_col(hm, ["Projektraum für Sitzungen", "IT-Arbeitsplätze und Test-/Integrationsumgebung",
                           "Fachanwendung / Lizenzen"], col=1, start=1)

    datum = de(a.get("datum", z.get("start", "")))
    for t in doc.tables:                                   # Dokument-Protokoll: alle drei Versionen
        hdr = " | ".join(cl(c.text) for c in t.rows[0].cells).lower()
        if "version" in hdr and "bemerkungen" in hdr and len(t.rows) > 1:
            v = cl(t.rows[1].cells[0].text)
            if v.startswith("1.0"):
                nm, bem = ag_name, ("Durchführung freigegeben" if freigegeben else "Entwurf")
            elif v.startswith("0.1"):
                nm, bem = PMO[0], "Entwurf erstellt"
            else:
                nm, bem = p["pl"], "Geprüft"
            set_cell(t.rows[1].cells[1], nm)
            set_cell(t.rows[1].cells[2], datum)
            set_cell(t.rows[1].cells[3], bem)

    remove_guidance(doc)
    remove_placeholder_rows(doc)
    doc.save(path)


# ---- Programm-DA ----------------------------------------------------------
def build_programm_da(name, ref, soll, zeit, kinder, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    a = soll.get("auftrag", {})
    z = zeit or {}
    budget = a.get("budget_soll", 0)
    aufwand = a.get("aufwand_soll", 0)
    datum = de(a.get("datum", z.get("start", "")))

    doc = Document(TPL_PROGRAMM)

    # Untertitel auf der Titelseite (Platzhalter 'Projektname')
    for p in doc.paragraphs:
        if (p.style.name or "").startswith("Titel-Projektbezeichnung 2") and cl(p.text).startswith("Projektname"):
            if p.runs:
                p.runs[0].text = f"{name} ({ref})"
                for r in p.runs[1:]:
                    r.text = ""
            break

    fill_section(doc, "Ausgangslage und Handlungsbedarf", [
        f"Das Programm «{name}» ({ref}) bündelt {len(kinder)} Projekte der Stadt Musterstadt zu einem "
        "koordinierten Veränderungsvorhaben. Die Einzelvorhaben verfolgen gemeinsame strategische Ziele "
        "und teilen Abhängigkeiten, Ressourcen und Standards.",
        "Eine gebündelte Steuerung stellt sicher, dass Nutzen, Termine und Mittel über alle Projekte "
        "hinweg optimiert und Konflikte frühzeitig entschieden werden."])
    fill_section(doc, "Lösungsziele", [
        f"Das Programm realisiert einen durchgängigen, bürger- und verwaltungsfreundlichen Zielzustand "
        f"im Themenfeld «{name}». Die Projekte zahlen gemeinsam auf dieses Ziel ein."])
    fill_section(doc, "Vorgehensziele", [
        "Das Programm wird nach HERMES 2022 (Programm-Management) geführt: Programminitialisierung, "
        "Programmdurchführung mit Zwischenevaluationen und Programmabschluss. Die Projekte werden "
        "innerhalb der Programmdurchführung gesteuert."])
    fill_section(doc, "Zusammenfassende Lösungsbeschreibung", [
        "Die Projekte werden priorisiert, terminlich aufeinander abgestimmt und über gemeinsame "
        "Architektur-, Daten- und Sicherheitsstandards geführt. Das Programmbüro koordiniert "
        "Ressourcen, Abhängigkeiten und Berichterstattung."])
    fill_section(doc, "Strategiebezug und Umsetzung von Programmen", [
        "Das Programm setzt die Digitalisierungs- und Servicestrategie der Stadt Musterstadt um und "
        "unterstützt die ressortübergreifende Zusammenarbeit."])
    fill_section(doc, "Rechtliche Grundlagen", [
        "Massgebend sind die einschlägigen kommunalen und kantonalen Rechtsgrundlagen sowie die "
        "Datenschutzgesetzgebung; die konkreten Erlasse sind mit dem Rechtsdienst zu verifizieren."])
    fill_section(doc, "Ressourcen- und Hilfsmittelbedarf", [
        f"Der Programmaufwand beträgt rund {chf(aufwand)} Personentage. Benötigt werden ein Programmbüro, "
        "gemeinsame Infrastruktur sowie die fachliche Mitwirkung der beteiligten Ressorts."])
    fill_section(doc, "Kosten / Nutzen / Wirtschaftlichkeit", [
        f"Der genehmigte Programmrahmen beträgt {chf(budget)} CHF. Der Nutzen entsteht aus Synergien, "
        "einheitlichen Standards und beschleunigter Umsetzung der Einzelprojekte."])
    fill_section(doc, "Planung und Organisation", [
        f"Geplanter Start: {de(z.get('start', ''))}, geplantes Ende: {de(z.get('ende', ''))}. Die "
        "Programmdurchführung wird mit Zwischenevaluationen gesteuert; die Projekte liefern monatliche PSR."])

    # Metadaten (Tab0: Klassifizierung)
    meta = find_table(doc, "Klassifizierung")
    if meta:
        mm = {"Status": "Freigegeben", "Programmnummer": ref, "Programmleiter": "N. N. (Programmleitung)",
              "Version": "1.0", "Datum": datum, "Auftraggeber": "Stadtrat Musterstadt",
              "Autor/Autoren": PMO[0], "Verteiler": "Stadtrat, Programmausschuss, Ressortleitungen"}
        for row in meta.rows:
            k = cl(row.cells[0].text)
            if k in mm and len(row.cells) > 1:
                set_cell(row.cells[1], mm[k])

    fill_phase_table(find_table(doc, "Phase", "Geplant CHF"), phase_values(budget, PHASE_PROGRAMM, ".--"))
    fill_phase_table(find_table(doc, "Phase", "Arbeitstage"), phase_values(aufwand, PHASE_PROGRAMM))

    org = find_table(doc, "Rolle in der Programmorganisation")
    if org:
        rollen = {"Programmauftraggeber": ("Stadtrat Musterstadt", "str", "Stadtrat"),
                  "Programmausschuss": (AUSSCHUSS[0], AUSSCHUSS[1], "Programmausschuss (Ressortleitungen)"),
                  "Programmleiter": ("N. N.", "", f"Programmleitung, {PMO[2]}")}
        for row in org.rows[1:]:
            rolle = cl(row.cells[0].text)
            for key, (nm, ku, fu) in rollen.items():
                if rolle.startswith(key):
                    set_cell(row.cells[1], nm); set_cell(row.cells[2], ku); set_cell(row.cells[3], fu)
                    break

    # Ziele-Tabellen (Lösungsziele / Vorgehensziele): Nr|Kategorie|Beschreibung|Messgrösse|Priorität|Prognose
    ztabs = [t for t in doc.tables if "beschreibung" in " | ".join(cl(c.text) for c in t.rows[0].cells).lower()
             and "messgr" in " | ".join(cl(c.text) for c in t.rows[0].cells).lower()]
    if len(ztabs) >= 1:
        r = ztabs[0].rows[1] if len(ztabs[0].rows) > 1 else None
        if r is not None and len(r.cells) >= 6:
            for i, val in enumerate(["LZ-01", "Nutzen", f"Zielzustand im Themenfeld «{name}» erreichen",
                                     "Grad der Zielerreichung", "hoch", "on track"]):
                set_cell(r.cells[i], val)
    if len(ztabs) >= 2:
        r = ztabs[1].rows[1] if len(ztabs[1].rows) > 1 else None
        if r is not None and len(r.cells) >= 6:
            for i, val in enumerate(["VZ-01", "Vorgehen", "Programm nach HERMES 2022 steuern",
                                     "Phasenfreigaben eingehalten", "hoch", "on track"]):
                set_cell(r.cells[i], val)

    rb = find_table(doc, "Rahmenbedingung", "Beschreibung")
    if rb and len(rb.rows) > 1:
        set_cell(rb.rows[1].cells[0], "01")
        set_cell(rb.rows[1].cells[1], "Budgetrahmen")
        set_cell(rb.rows[1].cells[2], f"Genehmigter Programmrahmen {chf(budget)} CHF.")
    ab = find_table(doc, "Abgrenzung", "Beschreibung")
    if ab and len(ab.rows) > 1:
        set_cell(ab.rows[1].cells[0], "01")
        set_cell(ab.rows[1].cells[1], "Betrieb")
        set_cell(ab.rows[1].cells[2], "Der Dauerbetrieb der Lösungen ist nicht Teil des Programms.")

    ms = find_table(doc, "Meilensteine", "Geplant")
    if ms:
        md = {"Programmdurchführungsfreigabe": datum, "Zwischenevaluation 1": de(z.get("start", "")),
              "Programmabschluss": de(z.get("ende", ""))}
        for row in ms.rows[1:]:
            k = cl(row.cells[0].text)
            for key, val in md.items():
                if k.startswith(key):
                    set_cell(row.cells[1], val)
                    break

    fill_risiken(find_table(doc, "Risikobeschreibung"),
                 ["Abhängigkeiten zwischen den Projekten geraten in Verzug",
                  "Ressourcenkonkurrenz zwischen den Projekten"], "Programmleitung")
    fill_rows_col(find_table(doc, "Zeitpunkt", "Beschreibung"), [
        "Die Projekte des Programms können koordiniert umgesetzt werden.",
        "Verzögerung des Programmnutzens; Abhängigkeiten geraten in Verzug.",
        "Die Digitalisierungsziele des Programms werden nicht erreicht."])
    vt = find_table(doc, "Verbindlichkeit", "Verantwortlich")
    if vt and len(vt.rows) > 1:
        set_cell(vt.rows[1].cells[1], "Programmrahmen")
        set_cell(vt.rows[1].cells[2], f"Genehmigter Rahmen {chf(budget)} CHF und Termine einhalten.")
        set_cell(vt.rows[1].cells[3], "Programmleitung")

    remove_guidance(doc)
    remove_placeholder_rows(doc)
    doc.save(path)


def _stub(ref, v):
    a = v.get("auftrag", {})
    bereich = v.get("bereich", "")
    return {"name": v.get("titel") or ref, "nummer": ref, "pl": "Daniel Huber",
            "ag": "Ressortleitung " + (bereich.replace("Ressort ", "") or "–"),
            "ve": v.get("einheit", "–"), "gb": bereich or "–",
            "cost_plan": a.get("budget_soll", 0), "eff_plan": a.get("aufwand_soll", 0),
            "ziel": ("Nutzen", (v.get("titel") or "das Vorhaben") + " umsetzen"),
            "risks": ["Datenübernahme aus Altsystem", "Verfügbarkeit Fachressourcen"]}


def main():
    for tpl in (TPL_PROJEKT, TPL_PROGRAMM):
        if not os.path.exists(tpl):
            print("FEHLER: Vorlage fehlt:", tpl)
            return
    pf = yaml.safe_load(open(os.path.join(HERE, "portfolio-musterstadt.yaml"), encoding="utf-8"))
    soll = {v["ref"]: v for v in pf["vorhaben"]}
    zeit = pf.get("zeitplan", {})
    by_nr = {p["nummer"]: p for p in PROJECTS}

    kinder = {}
    for ref, v in soll.items():
        if v.get("art") == "projekt" and v.get("programm"):
            kinder.setdefault(v["programm"], []).append(
                {"nummer": ref, "name": v.get("titel") or ref,
                 "budget": v["auftrag"].get("budget_soll", 0),
                 "status": v["auftrag"].get("status", "")})

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    n_proj = n_prog = 0
    for ref, v in soll.items():
        if v.get("art") == "programm":
            name = v.get("titel") or ref
            path = os.path.join(OUT, "Programme", _safe(name), "Programmdurchfuehrungsauftrag.docx")
            build_programm_da(name, ref, v, zeit.get(ref), kinder.get(name, []), path)
            n_prog += 1
        else:
            p = by_nr.get(ref) or _stub(ref, v)
            prog = v.get("programm")
            folder = (os.path.join(OUT, "Programme", _safe(prog), _safe(p["name"])) if prog
                      else os.path.join(OUT, "Fachbereiche", _safe(p["gb"]), _safe(p["name"])))
            build_projekt_da(p, v, zeit.get(ref), os.path.join(folder, "Durchfuehrungsauftrag.docx"), pi=n_proj)
            n_proj += 1

    print(f"Durchführungsaufträge (vollständig, vorlagengetreu) in {OUT}")
    print(f"  {n_proj} Projekt-DA, {n_prog} Programm-DA")

    # Seed-DA-Store extrahieren (committet) – speist später das Portfolio-Soll
    from app.da import extract_da, is_da
    records = []
    for dp, _dirs, files in os.walk(OUT):
        for fn in sorted(files):
            if fn.lower().endswith(".docx") and not fn.startswith("~$"):
                fp = os.path.join(dp, fn)
                if is_da(fp):
                    records.append(extract_da(fp))
    records.sort(key=lambda r: (r.get("typ", ""), str(r.get("ref"))))
    out = os.path.join(HERE, "da-musterstadt.yaml")
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(records, f, allow_unicode=True, sort_keys=False)
    print(f"  Seed-DA-Store: {out} ({len(records)} DA)")


if __name__ == "__main__":
    main()
