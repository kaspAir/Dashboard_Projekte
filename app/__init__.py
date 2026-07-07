"""Applikations-Factory."""
import os
import tempfile

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from .data import dashboard_data
from .extraction import extract_snapshot
from .mim import load_mim

META_IDS = ["project_name", "project_number", "report_date", "project_lead",
            "sponsor", "org_unit", "business_area", "phase", "lifecycle_state"]
RAG_IDS = ["status_overall", "status_schedule", "status_cost", "status_effort",
           "status_results", "status_objectives", "status_risks", "status_governance"]
METRIC_IDS = ["cost", "effort"]


def _result_view(mim, snapshot, filename):
    labels = {f["id"]: f.get("label", f["id"]) for f in mim["fields"]}
    prov = snapshot["provenance"]

    def rows(ids):
        out = []
        for fid in ids:
            if fid in prov:
                p = prov[fid]
                out.append({"label": labels.get(fid, fid), "value": p["value"],
                            "source": p["source"], "confidence": p["confidence"]})
        return out

    return {"filename": filename, "count": len(prov),
            "meta": rows(META_IDS), "rag": rows(RAG_IDS), "metrics": rows(METRIC_IDS)}


def create_app() -> Flask:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    app = Flask(__name__)
    app.config["APP_ENV"] = os.environ.get("APP_ENV", "local")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-insecure")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB Upload-Limit

    @app.get("/healthz")
    def healthz():
        """Liveness-Probe – von der Deploy-Pipeline per curl geprüft."""
        return jsonify(status="ok", env=app.config["APP_ENV"])

    @app.get("/")
    @app.get("/dashboard")
    def dashboard():
        return render_template(
            "dashboard.html", env=app.config["APP_ENV"], mim=load_mim(), d=dashboard_data()
        )

    @app.route("/upload", methods=["GET", "POST"])
    def upload():
        env = app.config["APP_ENV"]
        if request.method == "GET":
            return render_template("upload.html", env=env, result=None, error=None)

        f = request.files.get("file")
        if not f or not f.filename:
            return render_template("upload.html", env=env, result=None,
                                   error="Bitte eine Datei auswählen.")
        if not f.filename.lower().endswith(".docx"):
            return render_template("upload.html", env=env, result=None,
                                   error="Nur .docx-Dateien werden unterstützt.")

        tmp = os.path.join(tempfile.gettempdir(), secure_filename(f.filename))
        f.save(tmp)
        try:
            result = _result_view(load_mim(), extract_snapshot(tmp, load_mim()), f.filename)
        except Exception as exc:  # Extraktion darf die Seite nicht crashen
            return render_template("upload.html", env=env, result=None,
                                   error=f"Extraktion fehlgeschlagen: {exc}")
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        return render_template("upload.html", env=env, result=result, error=None)

    return app
