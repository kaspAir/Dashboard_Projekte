"""Ordner-Connector: findet Dokumente rekursiv unter einem Wurzelverzeichnis.

Bewusst rekursiv und ohne Annahme über die Ordnerstruktur: PSR dürfen beliebig
tief und verstreut liegen (ein Projektverzeichnis pro Projekt, PSR irgendwo darin)
– genau wie später beim SharePoint-„Verzeichnis aller Projekte". Ob eine gefundene
.docx tatsächlich ein PSR ist, entscheidet erst die Ingestion inhaltsbasiert.
"""
from __future__ import annotations

import os

from .base import Artifact


class FolderConnector:
    type = "folder"

    def __init__(self, root: str):
        self.root = root

    def discover(self):
        artifacts = []
        for dirpath, _dirs, files in os.walk(self.root):
            for name in files:
                if name.lower().endswith(".docx") and not name.startswith("~$"):
                    path = os.path.join(dirpath, name)
                    artifacts.append(Artifact(identifier=path, local_path=path))
        return artifacts
