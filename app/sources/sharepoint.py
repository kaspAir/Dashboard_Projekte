"""SharePoint/OneDrive-Connector über Microsoft Graph (App-only, client_credentials).

Hinter derselben discover()-Schnittstelle wie der Ordner-Connector: liefert Artefakte
mit lokal lesbarem Pfad (die .docx wird nach /tmp heruntergeladen). Durchsucht ein
Verzeichnis rekursiv – die PSR dürfen beliebig tief liegen.

Config (siehe config/sources/example-sharepoint.yaml):
  tenant_id, client_id, client_secret, site, drive (optional), root (optional).
"""
from __future__ import annotations

import os
import tempfile

import requests

GRAPH = "https://graph.microsoft.com/v1.0"


class SharePointConnector:
    type = "sharepoint"

    def __init__(self, config: dict):
        self.tenant = config["tenant_id"]
        self.client_id = config["client_id"]
        self.client_secret = config["client_secret"]
        self.site = config.get("site")          # "host:/sites/Name" ODER eine site-id
        self.drive_name = config.get("drive")   # optional; sonst Standard-Dokumentbibliothek
        self.root = (config.get("root") or "").strip("/")   # Ordner in der Bibliothek
        self._token = None

    # -- Auth / HTTP --------------------------------------------------------
    def _headers(self):
        if not self._token:
            r = requests.post(
                f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/token",
                data={"client_id": self.client_id, "client_secret": self.client_secret,
                      "scope": "https://graph.microsoft.com/.default",
                      "grant_type": "client_credentials"}, timeout=30)
            r.raise_for_status()
            self._token = r.json()["access_token"]
        return {"Authorization": f"Bearer {self._token}"}

    def _get(self, url):
        r = requests.get(url, headers=self._headers(), timeout=60)
        r.raise_for_status()
        return r.json()

    # -- Auflösung Site / Drive --------------------------------------------
    def _site_id(self):
        if self.site and "," in self.site:     # sieht schon nach einer site-id aus
            return self.site
        return self._get(f"{GRAPH}/sites/{self.site}")["id"]

    def _drive_id(self, site_id):
        drives = self._get(f"{GRAPH}/sites/{site_id}/drives")["value"]
        if self.drive_name:
            for d in drives:
                if d["name"].lower() == self.drive_name.lower():
                    return d["id"]
        return drives[0]["id"]

    # -- Rekursiv sammeln + herunterladen ----------------------------------
    def _walk(self, drive_id, item_id):
        found = []
        url = f"{GRAPH}/drives/{drive_id}/items/{item_id}/children"
        while url:
            data = self._get(url)
            for it in data.get("value", []):
                if it.get("folder"):
                    found += self._walk(drive_id, it["id"])
                elif it["name"].lower().endswith(".docx") and not it["name"].startswith("~$"):
                    found.append(it)
            url = data.get("@odata.nextLink")
        return found

    def _download(self, drive_id, item):
        r = requests.get(f"{GRAPH}/drives/{drive_id}/items/{item['id']}/content",
                         headers=self._headers(), timeout=120)
        r.raise_for_status()
        fd, path = tempfile.mkstemp(suffix=".docx", prefix="psr_")
        with os.fdopen(fd, "wb") as f:
            f.write(r.content)
        return path

    def discover(self):
        # lokale Importe vermeiden Zyklen; Artifact leicht gehalten
        from .base import Artifact
        site_id = self._site_id()
        drive_id = self._drive_id(site_id)
        if self.root:
            root_item = self._get(f"{GRAPH}/drives/{drive_id}/root:/{self.root}")
        else:
            root_item = self._get(f"{GRAPH}/drives/{drive_id}/root")
        artifacts = []
        for it in self._walk(drive_id, root_item["id"]):
            artifacts.append(Artifact(identifier=it.get("webUrl", it["id"]),
                                      local_path=self._download(drive_id, it)))
        return artifacts
