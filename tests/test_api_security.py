from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.routes import webhooks
from app.services import auth, email_service


def test_config_endpoint_requires_api_key(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "secret")
    monkeypatch.setattr(auth, "ENVIRONMENT", "production")
    client = TestClient(app)

    assert client.get("/api/config").status_code == 401
    assert client.get("/api/config", headers={"X-API-Key": "wrong"}).status_code == 403
    assert client.get("/api/config", headers={"X-API-Key": "secret"}).status_code == 200


def test_security_headers_present():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_whatsapp_webhook_secret(monkeypatch):
    monkeypatch.setattr(webhooks, "WHATSAPP_WEBHOOK_SECRET", "hook-secret")
    client = TestClient(app)

    response = client.post("/webhook/whatsapp", json={"from": "1", "text": "ayuda"})

    assert response.status_code == 401


def test_email_defaults_to_outbox(monkeypatch, tmp_path):
    monkeypatch.setattr(email_service, "EMAIL_SEND_MODE", "outbox")
    monkeypatch.setattr(email_service, "GOG_ACCOUNT", "configured-but-not-used")
    monkeypatch.setattr(email_service, "OUTBOX_DIR", tmp_path)

    result = email_service.send_email(
        to_emails=["cliente@example.com"],
        subject="Prueba",
        body="Contenido",
    )

    assert result["success"] is True
    assert result["mode"] == "outbox"
    assert Path(result["outbox_path"]).exists()
