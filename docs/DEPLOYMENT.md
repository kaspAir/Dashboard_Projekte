# Projekt-Dashboard – Deployment & DevOps

Erprobtes Muster (analog HERMES PIA / ProS): **Jenkins → SSH → Infomaniak**,
kein Docker in Prod, Auslieferung über einen **PHP-Proxy** je Subdomain auf einen
lokalen **Gunicorn**-Port.

## Umgebungen & Promotion

| Branch | Umgebung | URL | Port | App-Verzeichnis | Workers |
|--------|----------|-----|------|-----------------|---------|
| `dev` | dev | dev.dashboard-projekte.ch | 8023 | `~/dashboard-dev` | 1 |
| `test` | test | test.dashboard-projekte.ch | 8021 | `~/dashboard-test` | 1 |
| `int` | int | int.dashboard-projekte.ch | 8022 | `~/dashboard-int` | 1 |
| `main` | prod | dashboard-projekte.ch | 8020 | `~/dashboard` | 2 |

**Promotion streng sequenziell: `dev → test → int → main`.** Nie Stufen
überspringen. Jeder Deploy wird bewusst durch das Ausführen des jeweiligen
Jenkins-Jobs ausgelöst.

Port-Block **8020–8023** ist frei gewählt und kollidiert nicht mit hermespia
(8000–8003) oder ProS (8010–8012) auf demselben Host.

## Hosting

- Infomaniak Managed Hosting, **gleicher Host** wie hermespia.ch / ProS.
- SSH: `u7031y_kaspar@83.228.238.194`, Basis `/home/clients/2a1849703150229016af3666c2f46b09`.
- Kein Docker in Prod (Docker nur für die Regressionstests auf dem Jenkins-Agent).
- TLS je Subdomain über Infomaniak.

## Serving: PHP-Proxy

Pro Subdomain in den **Web-Root der Subdomain** legen:

- `deploy/proxy.php` – `$BACKEND` auf den Port der Stufe setzen (s. Tabelle).
- `deploy/.htaccess` – leitet alle Requests an `proxy.php`.

Der Proxy reicht an `127.0.0.1:<port>` weiter, wo Gunicorn die App bedient.

## Secrets & Konfiguration

- Pro Umgebung eine eigene `.env` **im App-Verzeichnis** (nicht im Git; s. `.env.example`).
- Relevante Variablen: `APP_ENV`, `SECRET_KEY`, `DATABASE_URL` (SQLite je Stufe),
  `ANTHROPIC_API_KEY`, später Microsoft-Graph-Zugang.

## Isolation: venv pro Umgebung

Jedes App-Verzeichnis hat sein **eigenes `.venv`** (von der Pipeline angelegt).
So kann ein Dependency-Bump auf `dev` keine andere Stufe beeinträchtigen.

## Jenkins

- **Vier separate Pipeline-Jobs** (kein Multibranch), je einer pro Branch/Stufe:
  `Dashboard dev/test/int/main`, jeweils *Pipeline script from SCM* auf
  `https://github.com/kaspAir/Dashboard_Projekte` mit dem passenden Branch. Die
  `when{}`-Bedingungen im `Jenkinsfile` matchen den `JOB_NAME` und feuern die
  richtige Deploy-Stufe.
- Credential **`dashboard-deploy`** (privater SSH-Key für `u7031y_kaspar`, derselbe
  Key wie `hermespia-deploy`).
- Ablauf je Deploy: `git reset --hard origin/<branch>` → venv sicherstellen →
  `pip install` → alten Gunicorn per PID killen → neu per `nohup` starten →
  Health-Check `curl /healthz`.

## Erstinbetriebnahme (einmalig)

1. Vier Branches anlegen und pushen: `dev`, `test`, `int`, `main`.
2. Subdomains dev/test/int + Prod-Domain in Infomaniak einrichten (DNS + TLS).
3. In jeden Subdomain-Web-Root `proxy.php` (Port anpassen!) + `.htaccess` legen.
4. Jenkins-Credential `dashboard-deploy` hinterlegen; vier Pipeline-Jobs
   (`Dashboard dev/test/int/main`) auf Repo + jeweiligen Branch zeigen.
5. Ersten Build je Job laufen lassen – die Pipeline klont ins App-Verzeichnis.
6. In jedem App-Verzeichnis auf dem Server eine `.env` erstellen (aus `.env.example`).
7. Verifizieren: `https://dev.dashboard-projekte.ch/healthz` → `{"status":"ok","env":"dev"}`.

## Health-Check

`GET /healthz` → `{"status":"ok","env":"<umgebung>"}`. Wird von der Pipeline nach
jedem Deploy geprüft.
