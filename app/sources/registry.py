"""Aktive Quell-Konfiguration – laufzeit-editierbar, persistiert unter data/
(nicht im Git; überlebt Deploys, da git reset data/ nicht anfasst)."""
from __future__ import annotations

import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACTIVE_SOURCE_FILE = os.path.join(ROOT, "data", "active_source.yaml")
DEFAULT_SOURCE = {"type": "folder", "path": os.path.join(ROOT, "sample-data", "psr")}


def load_active_source() -> dict:
    if os.path.exists(ACTIVE_SOURCE_FILE):
        with open(ACTIVE_SOURCE_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f) or dict(DEFAULT_SOURCE)
    return dict(DEFAULT_SOURCE)


def save_active_source(config: dict) -> None:
    os.makedirs(os.path.dirname(ACTIVE_SOURCE_FILE), exist_ok=True)
    with open(ACTIVE_SOURCE_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True)
