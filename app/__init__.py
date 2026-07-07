"""Applikations-Factory: Login, Rollen (super_admin/mandant_admin/user),
Mandant → Organisation → Projekt, gescopte Sicht."""
import os
import tempfile

from flask import (Flask, abort, jsonify, make_response, redirect,
                   render_template, request, session)
from werkzeug.utils import secure_filename

from .auth import (can_manage_users, create_user, get_user, is_mandant_admin,
                   is_super, load_users, may_upload, verify_login)
from .data import (all_projects, dashboard_data, load_snapshots, project_detail,
                   resolve_source)
from .mim import load_mim
from .orgs import (get_mandant, in_scope, load_mandanten, load_orgs,
                   save_mandant, save_org, slug)
from .sources.registry import load_active_source, save_active_source

LIFECYCLE_DE = {"active": "aktiv", "completed": "abgeschlossen", "aborted": "abgebrochen"}
META_IDS = ["project_name", "project_number", "report_date", "project_lead",
            "sponsor", "org_unit", "business_area", "phase", "lifecycle_state"]
RAG_IDS = ["status_overall", "status_schedule", "status_cost", "status_effort",
           "status_results", "status_objectives", "status_risks", "status_governance"]
METRIC_IDS = ["cost", "effort"]


def current_user():
    return get_user(session.get("user"))


def active_mandant(user):
    if is_super(user):
        mid = request.cookies.get("mandant")
        m = get_mandant(mid) if mid else None
        mand = load_mandanten()
        return m or (mand[0] if mand else None)
    return get_mandant(user.get("mandant_id")) if user else None


def visible_orgs(user):
    if is_super(user):
        m = active_mandant(user)
        return load_orgs(m["id"]) if m else []
    if is_mandant_admin(user):
        return load_orgs(user.get("mandant_id"))
    ids = set((user or {}).get("org_ids") or [])
    return [o for o in load_orgs((user or {}).get("mandant_id")) if o["id"] in ids]


def active_org(user):
    vis = visible_orgs(user)
    if not vis:
        return None
    oid = request.cookies.get("org")
    for o in vis:
        if o["id"] == oid:
            return o
    return vis[0]


def _ctx(user):
    return dict(user=user, org=active_org(user), mandant=active_mandant(user),
                may_upload=may_upload(user), is_super=is_super(user),
                can_manage=can_manage_users(user))


def _result_view(mim, snapshot, filename):
    labels = {f["id"]: f.get("label", f["id"]) for f in mim["fields"]}
    prov = snapshot["provenance"]

    def rows(ids):
        return [{"label": labels.get(fid, fid), "value": prov[fid]["value"],
                 "source": prov[fid]["source"], "confidence": prov[fid]["confidence"]}
                for fid in ids if fid in prov]

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
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok", env=app.config["APP_ENV"])

    @app.before_request
    def _gate():
        if request.path.startswith(("/login", "/healthz", "/static")):
            return None
        if not current_user():
            return redirect("/login")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            user = verify_login(request.form.get("email", ""), request.form.get("password", ""))
            if user:
                session["user"] = user["email"]
                return redirect("/dashboard")
            error = "E-Mail oder Passwort falsch."
        return render_template("login.html", env=app.config["APP_ENV"], error=error)

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect("/login")

    @app.get("/")
    @app.get("/dashboard")
    def dashboard():
        user = current_user()
        mid = (active_mandant(user) or {}).get("id")
        return render_template("dashboard.html", env=app.config["APP_ENV"], mim=load_mim(),
                               d=dashboard_data(active_org(user), mid), **_ctx(user))

    @app.get("/projekte")
    def projekte():
        user = current_user()
        bereich = request.args.get("bereich")
        einheit = request.args.get("einheit")
        projects = all_projects(active_org(user), (active_mandant(user) or {}).get("id"))
        if bereich:
            projects = [p for p in projects if p["business_area"] == bereich]
        if einheit:
            projects = [p for p in projects if p["org_unit"] == einheit]
        return render_template("projects.html", env=app.config["APP_ENV"], projects=projects,
                               bereich=bereich, einheit=einheit, lifecycle_de=LIFECYCLE_DE, **_ctx(user))

    @app.get("/projekt/<key>")
    def projekt(key):
        user = current_user()
        detail = project_detail(key, active_org(user), (active_mandant(user) or {}).get("id"))
        if not detail:
            abort(404)
        return render_template("project_detail.html", env=app.config["APP_ENV"],
                               d=detail, lifecycle_de=LIFECYCLE_DE, **_ctx(user))

    @app.get("/orgs/wechsel/<oid>")
    def orgs_switch(oid):
        resp = make_response(redirect("/dashboard"))
        resp.set_cookie("org", oid, max_age=31536000)
        return resp

    @app.route("/orgs", methods=["GET", "POST"])
    def orgs_page():
        user = current_user()
        mand = active_mandant(user)
        if request.method == "POST":
            if not can_manage_users(user):
                abort(403)
            name = (request.form.get("name") or "").strip()
            if name and mand:
                areas = request.form.getlist("business_areas")
                save_org({"id": slug(mand["id"] + "-" + name), "mandant_id": mand["id"],
                          "name": name, "scope": {"business_areas": areas} if areas else {}})
            return redirect("/orgs")
        snaps = load_snapshots((mand or {}).get("id"))
        rows = [{**o, "n_projects": len({r.get("projekt") for r in snaps if in_scope(r, o)})}
                for o in visible_orgs(user)]
        ministries = sorted({r.get("geschaeftsbereich") for r in snaps if r.get("geschaeftsbereich")})
        return render_template("orgs.html", env=app.config["APP_ENV"], orgs=rows,
                               ministries=ministries, can_create=can_manage_users(user), **_ctx(user))

    @app.route("/mandanten", methods=["GET", "POST"])
    def mandanten_page():
        user = current_user()
        if not is_super(user):
            abort(403)
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            if name:
                save_mandant({"id": slug(name), "name": name})
            return redirect("/mandanten")
        return render_template("mandanten.html", env=app.config["APP_ENV"],
                               mandanten=load_mandanten(), **_ctx(user))

    @app.get("/mandanten/wechsel/<mid>")
    def mandant_switch(mid):
        if not is_super(current_user()):
            abort(403)
        resp = make_response(redirect("/dashboard"))
        resp.set_cookie("mandant", mid, max_age=31536000)
        resp.set_cookie("org", "", expires=0)
        return resp

    @app.route("/users", methods=["GET", "POST"])
    def users_page():
        user = current_user()
        if not can_manage_users(user):
            abort(403)
        mand = active_mandant(user)
        if request.method == "POST":
            email = (request.form.get("email") or "").strip()
            name = (request.form.get("name") or "").strip()
            role = request.form.get("role") or "user"
            if not is_super(user):        # Mandant-Admin: keine super_admins, nur eigener Mandant
                role = "mandant_admin" if role == "mandant_admin" else "user"
            if email and name:
                create_user(email, name, role, mand["id"] if mand else None,
                            request.form.getlist("org_ids"),
                            bool(request.form.get("can_upload")),
                            request.form.get("password") or "")
            return redirect("/users")
        users = load_users() if is_super(user) else [
            u for u in load_users() if u.get("mandant_id") == (mand["id"] if mand else None)]
        return render_template("users.html", env=app.config["APP_ENV"], users=users,
                               orgs=(load_orgs(mand["id"]) if mand else []), **_ctx(user))

    @app.route("/quellen", methods=["GET", "POST"])
    def quellen():
        user = current_user()
        if not can_manage_users(user):
            abort(403)
        mid = (active_mandant(user) or {}).get("id")
        source = load_active_source(mid)
        result = error = None
        if request.method == "POST":
            action = request.form.get("action")
            path = (request.form.get("path") or "").strip()
            if path:
                source = {"type": "folder", "path": path}
                save_active_source(mid, source)
            if action == "ingest":
                try:
                    from .ingestion import run_ingestion, write_store
                    res = run_ingestion(source)
                    if res["ingested"] > 0:
                        write_store(res["records"], mid)
                    result = res
                except Exception as exc:
                    error = f"Einlesen fehlgeschlagen: {exc}"
        snaps = load_snapshots(mid)
        return render_template("quellen.html", env=app.config["APP_ENV"], source=source,
                               result=result, error=error, store_snapshots=len(snaps),
                               store_projects=len({r.get("projekt") for r in snaps}),
                               data_source=resolve_source(mid)[1], **_ctx(user))

    @app.route("/upload", methods=["GET", "POST"])
    def upload():
        user = current_user()
        if not may_upload(user):
            abort(403)
        env = app.config["APP_ENV"]
        ctx = _ctx(user)
        if request.method == "GET":
            return render_template("upload.html", env=env, result=None, error=None, **ctx)
        f = request.files.get("file")
        if not f or not f.filename:
            return render_template("upload.html", env=env, result=None,
                                   error="Bitte eine Datei auswählen.", **ctx)
        if not f.filename.lower().endswith(".docx"):
            return render_template("upload.html", env=env, result=None,
                                   error="Nur .docx-Dateien werden unterstützt.", **ctx)
        tmp = os.path.join(tempfile.gettempdir(), secure_filename(f.filename))
        f.save(tmp)
        try:
            from .extraction import extract_snapshot
            result = _result_view(load_mim(), extract_snapshot(tmp, load_mim()), f.filename)
        except Exception as exc:
            return render_template("upload.html", env=env, result=None,
                                   error=f"Extraktion fehlgeschlagen: {exc}", **ctx)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        return render_template("upload.html", env=env, result=result, error=None, **ctx)

    return app
