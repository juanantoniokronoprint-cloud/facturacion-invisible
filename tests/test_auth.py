from fastapi import HTTPException

from app.services import auth


def test_auth_dev_mode_without_api_key(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "")
    monkeypatch.setattr(auth, "ENVIRONMENT", "development")

    assert auth.get_api_key(None) == "dev-mode"


def test_auth_production_fails_closed_without_api_key(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "")
    monkeypatch.setattr(auth, "ENVIRONMENT", "production")

    try:
        auth.get_api_key(None)
    except HTTPException as exc:
        assert exc.status_code == 503
    else:
        raise AssertionError("Debe fallar cerrado en producción sin API_KEY")


def test_auth_requires_valid_api_key(monkeypatch):
    monkeypatch.setattr(auth, "API_KEY", "secret")
    monkeypatch.setattr(auth, "ENVIRONMENT", "production")

    assert auth.get_api_key("secret") == "secret"

    try:
        auth.get_api_key("wrong")
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Debe rechazar API_KEY incorrecta")
