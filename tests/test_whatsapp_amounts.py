from app.services.whatsapp_handler import normalizar_importe_extraido


def test_normalizes_vat_included_amount_to_tax_base():
    datos = {
        "importe": 242,
        "iva": 21,
        "importe_incluye_iva": True,
    }

    normalizado = normalizar_importe_extraido(datos)

    assert normalizado["importe"] == 200.0
    assert normalizado["total_iva_incluido_original"] == 242.0


def test_keeps_tax_base_amount_when_vat_not_included():
    datos = {
        "importe": 242,
        "iva": 21,
        "importe_incluye_iva": False,
    }

    normalizado = normalizar_importe_extraido(datos)

    assert normalizado["importe"] == 242
    assert "total_iva_incluido_original" not in normalizado
