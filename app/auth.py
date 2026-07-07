"""Benutzerverwaltung + Login (E-Mail + Passwort, gehasht).

Rollen:
  super_admin  – alle Rechte; legt Mandanten an.
  mandant_admin – im eigenen Mandanten: Organisationen und Benutzer anlegen.
  user          – Zugriff auf zugewiesene Organisationen; upload je nach Flag.

Standard-Benutzer aus config/users.default.yaml (committet, ohne Passwort-Hash),
Laufzeit-Benutzer aus data/users.yaml. Passwörter werden nur zur Laufzeit (data/)
gehasht gespeichert – der Super-Admin setzt sein Passwort beim ersten Login.
"""
from __future__ import annotations

import os

import yaml
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEF_USERS = os.path.join(ROOT, "config", "users.default.yaml")
RT_USERS = os.path.join(ROOT, "data", "users.yaml")


def _read(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or []
    return []


def load_users():
    by_email = {}
    for u in _read(DEF_USERS) + _read(RT_USERS):
        by_email[u["email"].lower()] = u
    return list(by_email.values())


def get_user(email):
    if not email:
        return None
    for u in load_users():
        if u["email"].lower() == email.lower():
            return u
    return None


def save_user(user):
    runtime = _read(RT_USERS)
    by_email = {u["email"].lower(): u for u in runtime}
    by_email[user["email"].lower()] = user
    os.makedirs(os.path.dirname(RT_USERS), exist_ok=True)
    with open(RT_USERS, "w", encoding="utf-8") as f:
        yaml.safe_dump(list(by_email.values()), f, allow_unicode=True, sort_keys=False)


def create_user(email, name, role, mandant_id=None, org_ids=None, can_upload=False, password=None):
    save_user({
        "email": email.strip(), "name": name.strip(), "role": role,
        "mandant_id": mandant_id, "org_ids": org_ids or [],
        "can_upload": bool(can_upload),
        "password_hash": generate_password_hash(password) if password else "",
    })


def verify_login(email, password):
    """Prüft Login. Hat der Benutzer noch kein Passwort, wird es beim ersten Login gesetzt."""
    user = get_user(email)
    if not user or not password:
        return None
    ph = user.get("password_hash")
    if not ph:                      # erstes Login -> Passwort setzen ("Konto beanspruchen")
        user = dict(user)
        user["password_hash"] = generate_password_hash(password)
        save_user(user)
        return user
    return user if check_password_hash(ph, password) else None


def is_super(user):
    return bool(user) and user.get("role") == "super_admin"


def is_mandant_admin(user):
    return bool(user) and user.get("role") == "mandant_admin"


def can_manage_users(user):
    return is_super(user) or is_mandant_admin(user)


def may_upload(user):
    return is_super(user) or bool(user and user.get("can_upload"))
