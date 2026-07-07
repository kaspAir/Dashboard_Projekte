"""Gemeinsame Test-Fixtures: authentifizierter Client (Super-Admin) und anonymer Client."""
import pytest

from app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    """Als Super-Admin angemeldet (Session direkt gesetzt, ohne Passwort-Flow)."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["user"] = "k.broennimann@gmail.com"
    return c


@pytest.fixture
def anon(app):
    return app.test_client()
