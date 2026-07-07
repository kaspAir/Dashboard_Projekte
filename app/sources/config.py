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
    if kind == "sharepoint":
        from .sharepoint import SharePointConnector   # lazy: requests erst bei Bedarf
        return SharePointConnector(config)
    raise ValueError(f"Unbekannter Quell-Typ: {kind!r}")
