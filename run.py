"""WSGI-Einstiegspunkt.

Gunicorn startet die App via ``gunicorn run:app`` (siehe Jenkinsfile).
Lokal: ``python run.py``.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Nur fuer die lokale Entwicklung. In Prod laeuft Gunicorn.
    app.run(host="127.0.0.1", port=5000, debug=True)
