"""Erzeugt zusätzliche Test-Datensätze (kaspAIr, Stadt Musterstadt) analog zur LLV.

Wiederverwendet die Generator-Funktionen aus generate_psr.py. Erzeugt je Set einen
Ordner mit Projektunterordnern (monatliche PSR) + eine ground_truth-Datei.

Aufruf (Repo-Root):  python sample-data/generate_extra.py
"""
import os
import shutil
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_psr import HERE, build_doc, snapshots_for  # noqa: E402


def generate(projects, out_name, gt_name):
    out_dir = os.path.join(HERE, out_name)
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    manifest, total = [], 0
    for idx, p in enumerate(projects, start=1):
        folder = os.path.join(out_dir, f"{idx:02d}_{p['short']}")
        os.makedirs(folder, exist_ok=True)
        for s in snapshots_for(p):
            build_doc(s, os.path.join(folder, f"{s['periode']}_PSR.docx"))
            total += 1
            manifest.append(dict(
                projekt=p["short"], name=p["name"], nummer=p["nummer"],
                datei=f"{idx:02d}_{p['short']}/{s['periode']}_PSR.docx", periode=s["periode"],
                verwaltungseinheit=p["ve"], geschaeftsbereich=p["gb"],
                lifecycle=p["lifecycle"], phase=s["phase"], status=s["status"],
                kosten={"plan": s["k_plan"], "ist": s["k_ist"], "prognose": s["k_prog"]}))
    with open(os.path.join(HERE, gt_name), "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, allow_unicode=True, sort_keys=False)
    print(f"{out_name}: {len(projects)} Projekte, {total} Snapshots")


if __name__ == "__main__":
    from psr_data_demo import PROJECTS as DEMO
    from psr_data_kaspair import PROJECTS as KASPAIR
    generate(KASPAIR, "psr-kaspair", "ground_truth_kaspair.yaml")
    generate(DEMO, "psr-demo", "ground_truth_demo.yaml")
