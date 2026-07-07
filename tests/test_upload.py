"""Testet den Upload-Connector (Formular + Extraktion mit Provenienz)."""
import os

from app import create_app

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "psr_sample.docx")


def test_upload_form_ok():
    client = create_app().test_client()
    assert client.get("/upload").status_code == 200


def test_upload_extracts_with_provenance():
    client = create_app().test_client()
    with open(FIXTURE, "rb") as fh:
        resp = client.post(
            "/upload",
            data={"file": (fh, "psr_sample.docx")},
            content_type="multipart/form-data",
        )
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Fundstelle" in body
    assert "Gesamtstatus" in body           # MIM-Label eines Ampelfeldes
    assert "Konfidenz" in body


def test_upload_rejects_non_docx():
    client = create_app().test_client()
    resp = client.post(
        "/upload",
        data={"file": (open(__file__, "rb"), "notes.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert "Nur .docx" in resp.get_data(as_text=True)
