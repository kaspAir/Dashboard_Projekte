"""Misst die Extraktions-Genauigkeit gegen die Ground-Truth.

Läuft über alle generierten PSR (sample-data/psr/**/*.docx), extrahiert je Datei
und vergleicht die 8 Ampeln + Kosten mit dem bekannten Soll-Wert.
Aufruf (aus dem Repo-Root):  python sample-data/measure_extraction.py
"""
from __future__ import annotations

import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.extraction import extract_snapshot  # noqa: E402
from app.mim import load_mim  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PSR = os.path.join(HERE, "psr")

FIELD_TO_GT = {
    "status_overall": "gesamt", "status_schedule": "termine", "status_cost": "kosten",
    "status_effort": "personalaufwand", "status_results": "ergebnisse",
    "status_objectives": "projektziele", "status_risks": "projektrisiken",
    "status_governance": "governance",
}


def norm(x):
    return str(x).replace("'", "").strip()


def main():
    gt = yaml.safe_load(open(os.path.join(HERE, "ground_truth.yaml"), encoding="utf-8"))
    mim = load_mim()
    files = missing = 0
    s_ok = s_tot = 0        # Ampel-Felder
    k_ok = k_tot = 0        # Kosten-Werte
    mismatches = []

    for rec in gt:
        path = os.path.join(PSR, rec["datei"].replace("/", os.sep))
        if not os.path.exists(path):
            missing += 1
            continue
        files += 1
        prov = extract_snapshot(path, mim)["provenance"]
        for fid, gtkey in FIELD_TO_GT.items():
            s_tot += 1
            got = prov.get(fid, {}).get("value")
            exp = rec["status"][gtkey]
            if got == exp:
                s_ok += 1
            elif len(mismatches) < 8:
                mismatches.append(f"{rec['datei']} {fid}: erwartet {exp}, erhalten {got}")
        if "cost" in prov:
            c = prov["cost"]["value"]
            for key in ("plan", "ist", "prognose"):
                k_tot += 1
                if norm(c.get(key, "")) == norm(rec["kosten"][key]):
                    k_ok += 1

    print(f"Dateien geprüft: {files}  (fehlend: {missing})")
    print(f"Ampel-Felder:    {s_ok}/{s_tot}  = {100*s_ok/max(s_tot,1):.1f}%")
    print(f"Kosten-Werte:    {k_ok}/{k_tot}  = {100*k_ok/max(k_tot,1):.1f}%")
    if mismatches:
        print("\nBeispiel-Abweichungen:")
        for m in mismatches:
            print("  " + m)


if __name__ == "__main__":
    main()
