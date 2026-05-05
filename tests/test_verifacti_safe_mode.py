import asyncio

from app.services import verifacti_wrapper


def test_verifacti_defaults_to_demo(monkeypatch):
    monkeypatch.setattr(verifacti_wrapper, "VERIFACTI_SEND_MODE", "demo")
    monkeypatch.setattr(verifacti_wrapper, "VERIFACTI_API_KEY", "configured-but-not-used")

    result = asyncio.run(verifacti_wrapper.enviar_factura_verifacti(object(), object()))

    assert result["success"] is True
    assert result["status"] == "demo"
