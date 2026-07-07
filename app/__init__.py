"""Applikations-Factory.

Bewusst minimal gehalten: nur so viel, dass die Deploy-Pipeline ein echtes,
laufendes Ziel mit Health-Check hat ("deploybares Skelett"). Die Fachlichkeit
(Connectoren, Extraktion, kanonisches Modell, Dashboard) kommt schrittweise
darauf.
"""
import os

from flask import Flask, jsonify


def create_app() -> Flask:
    # .env lokal laden (auf dem Server kommt die Umgebung aus der Shell/.env).
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    app = Flask(__name__)
    app.config["APP_ENV"] = os.environ.get("APP_ENV", "local")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-insecure")
    app.config["DATABASE_URL"] = os.environ.get(
        "DATABASE_URL", "sqlite:///data/app.db"
    )

    @app.get("/healthz")
    def healthz():
        """Liveness-Probe – von der Deploy-Pipeline per curl geprueft."""
        return jsonify(status="ok", env=app.config["APP_ENV"])

    @app.get("/")
    def index():
        env = app.config["APP_ENV"]
        return (
            "<!doctype html><meta charset='utf-8'>"
            "<title>Projekt-Dashboard</title>"
            "<h1>Projekt-Dashboard</h1>"
            f"<p>Umgebung: <strong>{env}</strong></p>"
            "<p>Status: laeuft. Fachlichkeit folgt.</p>"
        ), 200

    return app
