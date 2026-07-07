"""Applikations-Factory."""
import os

from flask import Flask, jsonify, render_template

from .data import dashboard_data
from .mim import load_mim


def create_app() -> Flask:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    app = Flask(__name__)
    app.config["APP_ENV"] = os.environ.get("APP_ENV", "local")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-insecure")

    @app.get("/healthz")
    def healthz():
        """Liveness-Probe – von der Deploy-Pipeline per curl geprüft."""
        return jsonify(status="ok", env=app.config["APP_ENV"])

    @app.get("/")
    @app.get("/dashboard")
    def dashboard():
        mim = load_mim()
        return render_template(
            "dashboard.html", env=app.config["APP_ENV"], mim=mim, d=dashboard_data()
        )

    return app
