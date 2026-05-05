from datetime import datetime
from types import SimpleNamespace

from app.routes.facturas import AbonoCreate, RectificativaCreate
from app.services.verifacti_transformer import transformar_factura_verifactu
from app.services.verifactu_service import crear_factura_abono, crear_rectificativa_por_diferencias


def test_abono_schema_accepts_positive_base():
    payload = AbonoCreate(base_imponible=50, concepto="Devolución", motivo="Devolución parcial")
    assert payload.base_imponible == 50


def test_rectificativa_schema_accepts_r1_diferencias():
    payload = RectificativaCreate(tipo_factura="R1", tipo_rectificacion="I", base_imponible=-50, motivo="Error importe")
    assert payload.tipo_factura == "R1"
    assert payload.tipo_rectificacion == "I"


def test_verifactu_abono_payload_is_negative_and_referenced():
    data = crear_factura_abono(
        serie="AB",
        numero="1",
        fecha_expedicion="04-05-2026",
        nif_cliente="B12345678",
        nombre_cliente="Cliente Test",
        base_imponible=50,
        tipo_impositivo=21,
        cuota_iva=10.5,
        descripcion="Devolución parcial",
        serie_factura_original="FI",
        numero_factura_original="1",
        fecha_factura_original="04-05-2026",
    )
    assert data["importe_total"] == "-60.5"
    assert data["lineas"][0]["base_imponible"] == "-50"
    assert data["tipo_rectificativa"] == "I"
    assert data["facturas_rectificadas"][0]["serie"] == "FI"


def test_verifactu_rectificativa_payload_has_r1_and_reference():
    data = crear_rectificativa_por_diferencias(
        serie="FR",
        numero="1",
        fecha_expedicion="04-05-2026",
        nif_cliente="B12345678",
        nombre_cliente="Cliente Test",
        diferencia_base=-50,
        diferencia_cuota=-10.5,
        tipo_iva=21,
        descripcion="Corrección importe",
        serie_original="FI",
        numero_original="1",
        fecha_original="04-05-2026",
    )
    assert data["tipo_factura"] == "R1"
    assert data["tipo_rectificativa"] == "I"
    assert data["facturas_rectificadas"][0]["numero"] == "1"


def test_transformar_factura_verifactu_supports_orm_rectificativa():
    origen = SimpleNamespace(
        serie="FI",
        numero="1",
        fecha_emision=datetime(2026, 5, 4),
        lineas=[SimpleNamespace(base_imponible=100, iva_cuota=21)],
    )
    factura = SimpleNamespace(
        serie="FR",
        numero="1",
        fecha_emision=datetime(2026, 5, 4),
        fecha_operacion=datetime(2026, 5, 4),
        tipo_factura="R1",
        tipo_rectificacion="I",
        motivo_rectificacion="Corrección importe",
        base_imponible=-50,
        iva_pct=21,
        factura_origen=origen,
        lineas=[SimpleNamespace(descripcion="Corrección", cantidad=1, precio_unitario=-50, descuento_pct=0, iva_pct=21)],
    )
    cliente = SimpleNamespace(nif="B12345678", nombre="Cliente Test")
    data = transformar_factura_verifactu(factura, cliente, "R1")
    assert data["tipo_factura"] == "R1"
    assert data["tipo_rectificativa"] == "I"
    assert data["facturas_rectificadas"][0]["serie"] == "FI"
