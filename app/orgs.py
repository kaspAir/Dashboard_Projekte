"""Mandanten (oberste Ebene) und Organisationen (darunter) + Scoping.

Mandant → Organisation → Projekt. Standard aus config/*.default.yaml (committet),
Laufzeit aus data/ (nicht im Git, überlebt Deploys). Analog org_id-Scoping in HERMES PIA.
"""
from __future__ import annotations

import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEF_MANDANTEN = os.path.join(ROOT, "config", "mandanten.default.yaml")
DEF_ORGS = os.path.join(ROOT, "config", "orgs.default.yaml")
RT_MANDANTEN = os.path.join(ROOT, "data", "mandanten.yaml")
RT_ORGS = os.path.join(ROOT, "data", "orgs.yaml")


def _read(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or []
    return []


def _write(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(items, f, allow_unicode=True, sort_keys=False)


def _merge(default_path, runtime_path):
    by_id = {}
    for item in _read(default_path) + _read(runtime_path):
        by_id[item["id"]] = item
    return list(by_id.values())


# -- Mandanten --------------------------------------------------------------
def load_mandanten():
    return _merge(DEF_MANDANTEN, RT_MANDANTEN)


def get_mandant(mandant_id):
    for m in load_mandanten():
        if m["id"] == mandant_id:
            return m
    return None


def save_mandant(mandant):
    runtime = _read(RT_MANDANTEN)
    by_id = {m["id"]: m for m in runtime}
    by_id[mandant["id"]] = mandant
    _write(RT_MANDANTEN, list(by_id.values()))


# -- Organisationen ---------------------------------------------------------
def load_orgs(mandant_id=None):
    orgs = _merge(DEF_ORGS, RT_ORGS)
    if mandant_id:
        orgs = [o for o in orgs if o.get("mandant_id") == mandant_id]
    return orgs


def get_org(org_id):
    for o in load_orgs():
        if o["id"] == org_id:
            return o
    return None


def save_org(org):
    runtime = _read(RT_ORGS)
    by_id = {o["id"]: o for o in runtime}
    by_id[org["id"]] = org
    _write(RT_ORGS, list(by_id.values()))


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "eintrag"


def in_scope(record: dict, org: dict | None) -> bool:
    scope = (org or {}).get("scope") or {}
    areas = scope.get("business_areas") or []
    units = scope.get("org_units") or []
    if not areas and not units:
        return True
    if areas and record.get("geschaeftsbereich") in areas:
        return True
    if units and record.get("verwaltungseinheit") in units:
        return True
    return False
