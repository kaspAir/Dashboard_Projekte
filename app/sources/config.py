"""Quell-Konfiguration laden und den passenden Connector bauen."""
from __future__ import annotations

import yaml

from .folder import FolderConnector


def load_source_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_connector(config: dict):
    kind = config.get("type")
    if kind == "folder":
        return FolderConnector(config["path"])
    # Erweiterungspunkt (später):
    #   if kind == "sharepoint":
    #       return SharePointConnector(config)   # Graph, rekursiv, lädt Dateien herunter
    raise ValueError(f"Unbekannter Quell-Typ: {kind!r}")
