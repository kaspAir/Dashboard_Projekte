"""Führt die Ordner-Ingestion aus und schreibt den kanonischen Store.

Aufruf (Repo-Root):  python sample-data/run_ingestion.py [wurzelordner]
Default-Ordner: sample-data/psr  ->  schreibt sample-data/canonical_store.yaml
"""
from __future__ import annotations

import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.ingestion import run_ingestion  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "psr")
    result = run_ingestion({"type": "folder", "path": root})
    out = os.path.join(HERE, "canonical_store.yaml")
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(result["records"], f, allow_unicode=True, sort_keys=False)
    print(f"Gescannt: {result['scanned']}  ingested: {result['ingested']}  "
          f"übersprungen: {result['skipped']}")
    print(f"Store: {out}  ({len(result['records'])} Snapshots)")


if __name__ == "__main__":
    main()
