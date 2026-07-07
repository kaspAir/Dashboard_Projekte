"""Mandanten (Organisationen): Verwaltung + Scoping.

Jeder Mandant sieht nur die für ihn relevanten Projekte. Standard-Mandanten kommen
aus config/orgs.default.yaml (committet); zur Laufzeit angelegte aus data/orgs.yaml
(nicht im Git, überlebt Deploys). Analog zum org_id-Scoping in HERMES PIA.
"""
from __future__ import annotations

import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ORGS = os.path.join(ROOT, "config", "orgs.default.yaml")
RUNTIME_ORGS = os.path.join(ROOT, "data", "orgs.yaml")


def _read(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or []
    return []


def load_orgs():
    by_id = {}
    for org in _read(DEFAULT_ORGS) + _read(RUNTIME_ORGS):
        by_id[org["id"]] = org
    return list(by_id.values())


def get_org(org_id):
    orgs = load_orgs()
    for org in orgs:
        if org["id"] == org_id:
            return org
    return orgs[0] if orgs else None


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "mandant"


def save_org(org: dict) -> None:
    runtime = _read(RUNTIME_ORGS)
    by_id = {o["id"]: o for o in runtime}
    by_id[org["id"]] = org
    os.makedirs(os.path.dirname(RUNTIME_ORGS), exist_ok=True)
    with open(RUNTIME_ORGS, "w", encoding="utf-8") as f:
        yaml.safe_dump(list(by_id.values()), f, allow_unicode=True, sort_keys=False)


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
