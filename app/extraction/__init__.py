"""Extraktion: PSR-Dokument -> kanonisches Status-Modell (mit Provenienz).

Strategien (hinter derselben Schnittstelle extract_snapshot):
  - deterministisch (table_parser): liest die bekannte HERMES-Tabellenstruktur.
  - LLM-gestützt (später): findet MIM-Felder in beliebigem Format.
"""
from .extractor import extract_snapshot

__all__ = ["extract_snapshot"]
