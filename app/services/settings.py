from __future__ import annotations

from app import config


PLACEHOLDER_EMISOR_VALUES = {"", "00000000T", "Facturación Invisible"}


def production_readiness() -> dict:
    """Devuelve comprobaciones no destructivas para saber si la app puede operar en producción."""
    checks = {
        "environment_production": config.ENVIRONMENT == "production",
        "api_key_configured": bool(config.API_KEY),
        "cors_restricted": bool(config.ALLOWED_ORIGINS) and "*" not in config.ALLOWED_ORIGINS,
        "public_base_url_configured": bool(config.PUBLIC_BASE_URL) and not config.PUBLIC_BASE_URL.startswith("http://127.0.0.1"),
        "telegram_webhook_secret_configured": bool(config.TELEGRAM_WEBHOOK_SECRET),
        "whatsapp_webhook_secret_configured": bool(config.WHATSAPP_WEBHOOK_SECRET),
        "email_safe_mode": config.EMAIL_SEND_MODE in {"outbox", "live"},
        "verifacti_safe_mode": config.VERIFACTI_SEND_MODE in {"demo", "live"},
        "emisor_nif_real": config.EMISOR_NIF not in PLACEHOLDER_EMISOR_VALUES,
        "emisor_nombre_real": config.EMISOR_NOMBRE not in PLACEHOLDER_EMISOR_VALUES,
        "emisor_domicilio_configured": bool(config.EMISOR_DOMICILIO),
    }
    missing = [name for name, ok in checks.items() if not ok]
    return {
        "ready": not missing,
        "checks": checks,
        "missing": missing,
    }
