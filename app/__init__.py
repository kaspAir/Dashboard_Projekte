"""Applikations-Factory."""
import os
import tempfile

from flask import Flask, abort, jsonify, render_template, request
from werkzeug.utils import secure_filename

from .data import (all_projects, dashboard_data, load_snapshots, project_detail,
                   resolve_source)
from .mim import load_mim
from .sources.registry import load_active_source, save_active_source

LIFECYCLE_DE = {"active": "aktiv", "completed": "abgeschlossen", "aborted": "abgebrochen"}

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

    @app.get("/projekte")
    def projekte():
        bereich = request.args.get("bereich")
        einheit = request.args.get("einheit")
        projects = all_projects()
        if bereich:
            projects = [p for p in projects if p["business_area"] == bereich]
        if einheit:
            projects = [p for p in projects if p["org_unit"] == einheit]
        return render_template("projects.html", env=app.config["APP_ENV"],
                               projects=projects, bereich=bereich, einheit=einheit,
                               lifecycle_de=LIFECYCLE_DE)

    @app.get("/projekt/<key>")
    def projekt(key):
        detail = project_detail(key)
        if not detail:
            abort(404)
        return render_template("project_detail.html", env=app.config["APP_ENV"],
                               d=detail, lifecycle_de=LIFECYCLE_DE)

    @app.route("/quellen", methods=["GET", "POST"])
    def quellen():
        env = app.config["APP_ENV"]
        source = load_active_source()
        result = error = None
        if request.method == "POST":
            action = request.form.get("action")
            path = (request.form.get("path") or "").strip()
            if path:
                source = {"type": "folder", "path": path}
                save_active_source(source)
            if action == "ingest":
                try:
                    from .ingestion import run_ingestion, write_store  # lazy (docx)
                    res = run_ingestion(source)
                    if res["ingested"] > 0:      # leeres Ergebnis nie den Store überschreiben
                        write_store(res["records"])
                    result = res
                except Exception as exc:
                    error = f"Einlesen fehlgeschlagen: {exc}"
        snaps = load_snapshots()
        return render_template("quellen.html", env=env, source=source, result=result,
                               error=error, store_snapshots=len(snaps),
                               store_projects=len({r.get("projekt") for r in snaps}),
                               data_source=resolve_source()[1])

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
            from .extraction import extract_snapshot  # lazy: docx/lxml erst bei Bedarf laden
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
