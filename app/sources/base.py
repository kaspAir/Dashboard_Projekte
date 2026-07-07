"""Connector-Basis: einheitliche Schnittstelle für Quellen.

Ein Connector liefert per discover() eine Liste von Artefakten. Jedes Artefakt
stellt über local_path eine lokal lesbare .docx bereit (ein SharePoint-Connector
würde die Datei zuvor herunterladen und local_path auf die Temp-Datei setzen).
Alles danach – PSR-Erkennung, Extraktion, Gruppierung – ist quell-agnostisch.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Artifact:
    identifier: str   # stabile Kennung (Pfad; später z. B. SharePoint-Item-ID)
    local_path: str   # lokal lesbarer Pfad zur .docx
