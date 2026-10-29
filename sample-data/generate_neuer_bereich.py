# -*- coding: utf-8 -*-
"""Erzeugt ein NEUES Ressort «Kultur & Sport» mit zwei Projekten (agil + klassisch),
je PSR-Zeitreihe + Durchführungsauftrag – zum Live-Hochladen auf den SharePoint und
Einlesen ins Dashboard (demonstriert: ein neuer Bereich erscheint live).

Ablage spiegelt die bestehende Struktur (Fachbereiche/<Ressort>/<Projekt>/...), damit
der Upload in PSR_Tests/Musterstadt nahtlos dazukommt.

Aufruf (Repo-Root):  python sample-data/generate_neuer_bereich.py
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from generate_psr import build_doc, snapshots_for         # noqa: E402
from generate_demo_drive import sprints_for, AGILE_PHASE  # noqa: E402
from generate_da import build_projekt_da, _safe           # noqa: E402

OUT = os.path.join(HERE, "neuer-bereich")
BEREICH = "Ressort Kultur & Sport"

NEU = [
    dict(short="Bibliotheksportal", name="Stadtbibliothek-Portal", nummer="M-2026-020",
         pl="Lena Moser", ag="Katrin Suter", ve="Kulturamt", gb=BEREICH,
         start=(2025, 1), dur=15, lifecycle="active", arch="volatil", weak=["termine"],
         cost_plan=420000, eff_plan=320,
         ziel=("Service", "Digitale Ausleihe und Veranstaltungsbuchung"),
         risks=["Anbindung an den Verbundkatalog", "Akzeptanz der Nutzenden"], method="agil"),
    dict(short="Sportbuchung", name="Sportanlagen-Buchung", nummer="M-2026-021",
         pl="Marco Keller", ag="Katrin Suter", ve="Sportamt", gb=BEREICH,
         start=(2025, 3), dur=18, lifecycle="active", arch="verschlechterung", weak=["kosten", "termine"],
         cost_plan=360000, eff_plan=280,
         ziel=("Effizienz", "Hallen und Plätze online buchen und bezahlen"),
         risks=["Zahlungsschnittstelle", "Vielzahl der Anlagen und Tarife"], method="klassisch"),
]


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    for pi, p in enumerate(NEU):
        folder = os.path.join(OUT, "Fachbereiche", _safe(p["gb"]), _safe(p["name"]))
        psr_dir = os.path.join(folder, "Statusberichte")
        os.makedirs(psr_dir, exist_ok=True)

        snaps = snapshots_for(p)
        for i, s in enumerate(snaps):
            s["method"] = p["method"]
            s["programm"] = ""
            if p["method"] == "agil":
                s["phase"] = AGILE_PHASE.get(s["phase"], s["phase"])
                done, nxt = sprints_for(p, s["periode"], s["status"]["gesamt"], i == len(snaps) - 1)
                s["sp_erreicht"], s["sp_geplant"] = done, nxt
            build_doc(s, os.path.join(psr_dir, f"{s['periode']}_PSR.docx"))

        soll = {"auftrag": {"status": "laufend", "datum": f"{p['start'][0]}-{p['start'][1]:02d}-15",
                            "budget_soll": p["cost_plan"], "aufwand_soll": p["eff_plan"]},
                "programm": "", "einheit": p["ve"], "bereich": p["gb"]}
        y, m = p["start"]
        end_y = y + (m - 1 + p["dur"]) // 12
        end_m = (m - 1 + p["dur"]) % 12 + 1
        zeit = {"start": f"{y}-{m:02d}-01", "ende": f"{end_y}-{end_m:02d}-01", "method": p["method"]}
        build_projekt_da(p, soll, zeit, os.path.join(folder, "Durchfuehrungsauftrag.docx"), pi=pi)

    print(f"Neuer Bereich «{BEREICH}» erzeugt in {OUT}")
    for p in NEU:
        n = len(snapshots_for(p))
        print(f"  {p['name']} ({p['nummer']}, {p['method']}): {n} PSR + 1 DA")


if __name__ == "__main__":
    main()
