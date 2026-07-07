"""Version + Build-Info (aus VERSION-Datei + Git-SHA)."""
from __future__ import annotations

import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_version() -> str:
    try:
        with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "0.0.0"


def _git_short():
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, timeout=3, text=True)
        return out.stdout.strip() or None
    except Exception:
        return None


__version__ = _read_version()
GIT_SHA = _git_short()
