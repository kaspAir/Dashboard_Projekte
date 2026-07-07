"""Laden des Management-Informationsmodells (MIM)."""
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MIM = os.path.join(ROOT, "config", "mim", "mim.default.yaml")


def load_mim(path: str | None = None) -> dict:
    path = path or DEFAULT_MIM
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
