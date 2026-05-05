from pydantic import ValidationError

from fastapi import HTTPException

from app.routes.facturas import (
    FacturaCreate,
    FacturaSimpleCreate,
    LineaFacturaCreate,
    _validate_nif_required,
)


def test_factura_create_rejects_empty_invoice_payload():
    payload = FacturaCreate(cliente_id=1, lineas=[], base_imponible=None)

    assert payload.lineas == []
    assert payload.base_imponible is None


def test_linea_rejects_negative_values():
    try:
        LineaFacturaCreate(descripcion="Servicio", cantidad=-1, precio_unitario=100)
    except ValidationError:
        return
    raise AssertionError("Debe rechazar cantidades negativas")


def test_factura_simple_validates_estado():
    try:
        FacturaSimpleCreate(
            cliente_nombre="Cliente",
            concepto="Servicio",
            base_imponible=100,
            estado="enviado",
        )
    except ValidationError:
        return
    raise AssertionError("Debe rechazar estados fuera del catálogo")


def test_rejects_invoice_over_400_with_vat_without_nif():
    try:
        _validate_nif_required(None, base=500, iva_pct=21)
    except HTTPException as exc:
        assert exc.status_code == 422
        assert "NIF" in exc.detail
        return
    raise AssertionError("Debe exigir NIF si el total con IVA supera 400€")


def test_allows_simplified_invoice_up_to_400_with_vat_without_nif():
    _validate_nif_required(None, base=100, iva_pct=21)
