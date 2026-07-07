"""Quell-Konfiguration je Mandant – laufzeit-editierbar, persistiert unter
data/sources/<mandant_id>.yaml (nicht im Git, überlebt Deploys)."""
from __future__ import annotations

import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCES_DIR = os.path.join(ROOT, "data", "sources")


def source_file(mandant_id: str) -> str:
    return os.path.join(SOURCES_DIR, f"{mandant_id}.yaml")


def default_source(mandant_id: str) -> dict:
    # LLV bekommt lokal den Demo-Ordner als Default; andere Mandanten leer.
    if mandant_id == "llv":
        return {"type": "folder", "path": os.path.join(ROOT, "sample-data", "psr")}
    return {"type": "folder", "path": ""}


def load_active_source(mandant_id: str) -> dict:
    path = source_file(mandant_id)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or default_source(mandant_id)
    return default_source(mandant_id)


def save_active_source(mandant_id: str, config: dict) -> None:
    os.makedirs(SOURCES_DIR, exist_ok=True)
    with open(source_file(mandant_id), "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True)
