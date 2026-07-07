"""Connector-Auswahl (ohne Netzwerkzugriff)."""
import pytest

from app.sources.config import build_connector


def test_folder_connector():
    c = build_connector({"type": "folder", "path": "/tmp"})
    assert c.type == "folder"


def test_sharepoint_connector_builds_without_network():
    c = build_connector({"type": "sharepoint", "tenant_id": "t", "client_id": "c",
                         "client_secret": "s", "site": "host:/sites/X", "root": "PSR"})
    assert c.type == "sharepoint"       # Konstruktor macht keinen Netzwerkaufruf


def test_unknown_type_raises():
    with pytest.raises(ValueError):
        build_connector({"type": "dropbox"})
