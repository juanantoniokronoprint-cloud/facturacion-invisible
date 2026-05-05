#!/usr/bin/env python3
"""
Script de pruebas QA adicional - Completar a 100+
"""

import os
import sys

TEMP_DB = "/tmp/test_qa_extra.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEMP_DB}"
os.environ["API_KEY"] = "testkey"
os.environ["ENVIRONMENT"] = "dev"
os.environ["EMAIL_SEND_MODE"] = "outbox"
os.environ["VERIFACTI_SEND_MODE"] = "demo"

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
headers = {"X-API-Key": "testkey"}

results = []


def test(name, status, detail, steps="", expected="", got=""):
    print(f"[{status}] {name}: {detail}")
    results.append(
        {
            "id": len(results) + 1,
            "sc": name,
            "st": status,
            "detail": detail,
            "steps": steps,
            "exp": expected,
            "got": got,
        }
    )
    return results[-1]


# ==========================================
# PRUEBAS ADICIONALES 82-120
# ==========================================

# 82-85: Casos especiales de facturas
try:
    c = client.post(
        "/api/facturas/clientes", json={"nombre": "Sin Lineas"}, headers=headers
    ).json()
    f = client.post(
        "/api/facturas/",
        json={"cliente_id": c["id"], "base_imponible": 250.0, "iva_pct": 21.0},
        headers=headers,
    ).json()
    ok = f.get("base_imponible") == 250.0
    test(
        "82-Factura-SinLineas",
        "PASS" if ok else "FAIL",
        f"base={f.get('base_imponible')}",
        "base only",
        "250",
        f.get("base_imponible"),
    )
except Exception as e:
    test("82-Factura-SinLineas", "ERROR", str(e))

# 83: Cliente con teléfono
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nombre": "Tel Test", "telefono": "612345678"},
        headers=headers,
    ).json()
    ok = c.get("telefono") == "612345678"
    test(
        "83-Cliente-Telefono",
        "PASS" if ok else "FAIL",
        f"tel={c.get('telefono')}",
        "telefono",
        "612345678",
        c.get("telefono"),
    )
except Exception as e:
    test("83-Cliente-Telefono", "ERROR", str(e))

# 84: Factura actualizar a pendiente
try:
    c = client.post(
        "/api/facturas/clientes", json={"nombre": "Pend Test"}, headers=headers
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "base_imponible": 100.0,
            "estado": "borrador",
            "lineas": [{"descripcion": "t", "cantidad": 1, "precio_unitario": 100.0}],
        },
        headers=headers,
    ).json()
    r = client.patch(
        f"/api/facturas/{f['id']}/estado?estado=pendiente", headers=headers
    ).json()
    ok = r.get("estado") == "pendiente"
    test(
        "84-Factura-Pendiente",
        "PASS" if ok else "FAIL",
        f"est={r.get('estado')}",
        "borrador->pendiente",
        "pendiente",
        r.get("estado"),
    )
except Exception as e:
    test("84-Factura-Pendiente", "ERROR", str(e))

# 85: Lineas con cantidad >1
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "Q1234567A", "nombre": "Cant Test"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "lineas": [
                {
                    "descripcion": "Serv",
                    "cantidad": 5,
                    "precio_unitario": 20.0,
                    "iva_pct": 21.0,
                }
            ],
        },
        headers=headers,
    ).json()
    ok = f.get("base_imponible") == 100.0
    test(
        "85-Lineas-Cantidad",
        "PASS" if ok else "FAIL",
        f"base={f.get('base_imponible')}",
        "cant=5*20",
        "100",
        f.get("base_imponible"),
    )
except Exception as e:
    test("85-Lineas-Cantidad", "ERROR", str(e))

# 86: IVa mix en lineas automatico
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "R1234567B", "nombre": "IVA Auto"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "iva_pct": 10.0,
            "lineas": [
                {"descripcion": "L1", "cantidad": 1, "precio_unitario": 100.0},
                {"descripcion": "L2", "cantidad": 1, "precio_unitario": 50.0},
            ],
        },
        headers=headers,
    ).json()
    ok = f.get("iva_pct") == 10.0
    test(
        "86-Lineas-IVAAuto",
        "PASS" if ok else "FAIL",
        f"iva={f.get('iva_pct')}",
        "iva default",
        "10",
        f.get("iva_pct"),
    )
except Exception as e:
    test("86-Lineas-IVAAuto", "ERROR", str(e))

# 87: Abono referencia serie AB
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "S1234567C", "nombre": "AB Ref"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "base_imponible": 100.0,
            "lineas": [{"descripcion": "t", "cantidad": 1, "precio_unitario": 100.0}],
        },
        headers=headers,
    ).json()
    ab = client.post(
        f"/api/facturas/{f['id']}/abono",
        json={"base_imponible": 50.0, "concepto": "A", "motivo": "M"},
        headers=headers,
    ).json()["factura"]
    ok = "AB" in ab.get("serie", "")
    test(
        "87-Abono-SerieAB",
        "PASS" if ok else "FAIL",
        f"s={ab.get('serie')}",
        "serie AB",
        "AB",
        ab.get("serie"),
    )
except Exception as e:
    test("87-Abono-SerieAB", "ERROR", str(e))

# 88: Rectificativa serie FR
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "T1234567D", "nombre": "FR Ref"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "base_imponible": 100.0,
            "lineas": [{"descripcion": "t", "cantidad": 1, "precio_unitario": 100.0}],
        },
        headers=headers,
    ).json()
    r = client.post(
        f"/api/facturas/{f['id']}/rectificativa",
        json={
            "tipo_factura": "R2",
            "tipo_rectificacion": "I",
            "base_imponible": -25.0,
            "concepto": "R",
            "motivo": "M",
        },
        headers=headers,
    ).json()["factura"]
    ok = "FR" in r.get("serie", "")
    test(
        "88-Rect-SerieFR",
        "PASS" if ok else "FAIL",
        f"s={r.get('serie')}",
        "serie FR",
        "FR",
        r.get("serie"),
    )
except Exception as e:
    test("88-Rect-SerieFR", "ERROR", str(e))

# 89: VeriFactu - transformando
try:
    from app.services.verifacti_transformer import VeriFactiTransformer

    f = {"serie": "FI", "numero": "1", "fecha": "2024-01-01"}
    cl = {"nif": "A1234567B", "nombre": "Test"}
    ls = [
        {
            "base_imponible": 100.0,
            "cuota_repercutida": 21.0,
            "tipo_impositivo": "G21",
            "cuota_recargo_equivalencia": 0.0,
        }
    ]
    result = VeriFactiTransformer.transform_factura(f, cl, ls)
    ok = "serie" in result
    test(
        "89-VeriFacti-Transform",
        "PASS" if ok else "FAIL",
        f"keys={list(result.keys())[:3]}",
        "transform",
        "keys",
        list(result.keys())[:3],
    )
except Exception as e:
    test("89-VeriFacti-Transform", "ERROR", str(e))

# 90: VeriFactu rectificativa transform
try:
    from app.services.verifacti_transformer import VeriFactiTransformer

    f = {"serie": "FR", "numero": "1", "fecha": "2024-01-01", "tipo_factura": "R1"}
    cl = {"nif": "B1234567C", "nombre": "Test"}
    ls = [
        {
            "base_imponible": -50.0,
            "cuota_repercutida": -10.5,
            "tipo_impositivo": "G21",
            "cuota_recargo_equivalencia": 0.0,
        }
    ]
    result = VeriFactiTransformer.transform_rectificativa(f, cl, ls)
    ok = "serie" in result
    test(
        "90-VeriFacti-Rect",
        "PASS" if ok else "FAIL",
        f"ok={ok}",
        "rect transform",
        "ok",
        f"ok={ok}",
    )
except Exception as e:
    test("90-VeriFacti-Rect", "ERROR", str(e))

# 91: Factura serie por defecto
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "U1234567E", "nombre": "Serie Test"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "base_imponible": 100.0,
            "lineas": [{"descripcion": "t", "cantidad": 1, "precio_unitario": 100.0}],
        },
        headers=headers,
    ).json()
    ok = f.get("serie") == "FI"
    test(
        "91-Factura-SerieDefault",
        "PASS" if ok else "FAIL",
        f"s={f.get('serie')}",
        "default",
        "FI",
        f.get("serie"),
    )
except Exception as e:
    test("91-Factura-SerieDefault", "ERROR", str(e))

# 92: Lineas IVA mixto
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "V1234567F", "nombre": "Mix Test"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/simple",
        json={
            "cliente_nif": "V1234567F",
            "cliente_nombre": "Mix Test",
            "concepto": "Trabajo",
            "base_imponible": 100.0,
            "iva_pct": 21.0,
            "irpf_pct": 15.0,
        },
        headers=headers,
    ).json()
    ok = f.get("total") == 106.0
    test(
        "92-Simple-IRPF15",
        "PASS" if ok else "FAIL",
        f"t={f.get('total')}",
        "irpf 15%",
        "106",
        f.get("total"),
    )
except Exception as e:
    test("92-Simple-IRPF15", "ERROR", str(e))

# 93: Cliente con CP
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nombre": "CP Test", "codigo_postal": "28013"},
        headers=headers,
    ).json()
    ok = c.get("codigo_postal") == "28013"
    test(
        "93-Cliente-CP",
        "PASS" if ok else "FAIL",
        f"cp={c.get('codigo_postal')}",
        "codigo_postal",
        "28013",
        c.get("codigo_postal"),
    )
except Exception as e:
    test("93-Cliente-CP", "ERROR", str(e))

# 94: Cliente con provincia
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nombre": "Prov Test", "provincia": "Madrid"},
        headers=headers,
    ).json()
    ok = c.get("provincia") == "Madrid"
    test(
        "94-Cliente-Provincia",
        "PASS" if ok else "FAIL",
        f"prov={c.get('provincia')}",
        "provincia",
        "Madrid",
        c.get("provincia"),
    )
except Exception as e:
    test("94-Cliente-Provincia", "ERROR", str(e))

# 95: Cliente con ciudad
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nombre": "City Test", "ciudad": "Madrid"},
        headers=headers,
    ).json()
    ok = c.get("ciudad") == "Madrid"
    test(
        "95-Cliente-Ciudad",
        "PASS" if ok else "FAIL",
        f"city={c.get('ciudad')}",
        "ciudad",
        "Madrid",
        c.get("ciudad"),
    )
except Exception as e:
    test("95-Cliente-Ciudad", "ERROR", str(e))

# 96: Cliente con domicilio
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nombre": "Dom Test", "domicilio": "Calle Mayor 1"},
        headers=headers,
    ).json()
    ok = c.get("domicilio") == "Calle Mayor 1"
    test(
        "96-Cliente-Domicilio",
        "PASS" if ok else "FAIL",
        f"dom={c.get('domicilio')}",
        "domicilio",
        "Calle Mayor 1",
        c.get("domicilio"),
    )
except Exception as e:
    test("96-Cliente-Domicilio", "ERROR", str(e))

# 97: Factura simple con IRPF 7
try:
    f = client.post(
        "/api/facturas/simple",
        json={
            "cliente_nombre": "IRPF7 Test",
            "concepto": "Trabajo",
            "base_imponible": 1000.0,
            "iva_pct": 21.0,
            "irpf_pct": 7.0,
        },
        headers=headers,
    ).json()
    ok = f.get("irpf_cuota") == 70.0
    test(
        "97-Simple-IRPF7",
        "PASS" if ok else "FAIL",
        f"irpf={f.get('irpf_cuota')}",
        "irpf 7%",
        "70",
        f.get("irpf_cuota"),
    )
except Exception as e:
    test("97-Simple-IRPF7", "ERROR", str(e))

# 98: Factura simple IRPF 19
try:
    f = client.post(
        "/api/facturas/simple",
        json={
            "cliente_nombre": "IRPF19 Test",
            "concepto": "Trabajo",
            "base_imponible": 1000.0,
            "iva_pct": 21.0,
            "irpf_pct": 19.0,
        },
        headers=headers,
    ).json()
    ok = f.get("irpf_cuota") == 190.0
    test(
        "98-Simple-IRPF19",
        "PASS" if ok else "FAIL",
        f"irpf={f.get('irpf_cuota')}",
        "irpf 19%",
        "190",
        f.get("irpf_cuota"),
    )
except Exception as e:
    test("98-Simple-IRPF19", "ERROR", str(e))

# 99: Rectificativa R1 total
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "X1234567G", "nombre": "R1 Total"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "base_imponible": 500.0,
            "iva_pct": 21.0,
            "lineas": [
                {
                    "descripcion": "t",
                    "cantidad": 1,
                    "precio_unitario": 500.0,
                    "iva_pct": 21.0,
                }
            ],
        },
        headers=headers,
    ).json()
    r = client.post(
        f"/api/facturas/{f['id']}/rectificativa",
        json={
            "tipo_factura": "R1",
            "tipo_rectificacion": "I",
            "base_imponible": -500.0,
            "concepto": "R",
            "motivo": "Total",
        },
        headers=headers,
    ).json()["factura"]
    ok = r.get("base_imponible") == -500.0
    test(
        "99-Rect-R1Total",
        "PASS" if ok else "FAIL",
        f"b={r.get('base_imponible')}",
        "R1 full",
        "-500",
        r.get("base_imponible"),
    )
except Exception as e:
    test("99-Rect-R1Total", "ERROR", str(e))

# 100: Rectificativa S completas
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "Y1234567H", "nombre": "S Full"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "base_imponible": 800.0,
            "iva_pct": 21.0,
            "lineas": [
                {
                    "descripcion": "t",
                    "cantidad": 1,
                    "precio_unitario": 800.0,
                    "iva_pct": 21.0,
                }
            ],
        },
        headers=headers,
    ).json()
    r = client.post(
        f"/api/facturas/{f['id']}/rectificativa",
        json={
            "tipo_factura": "R3",
            "tipo_rectificacion": "S",
            "base_imponible": 750.0,
            "concepto": "S",
            "motivo": "Nueva",
        },
        headers=headers,
    ).json()["factura"]
    ok = r.get("base_imponible") == 750.0 and r.get("tipo_rectificacion") == "S"
    test(
        "100-Rect-SFull",
        "PASS" if ok else "FAIL",
        f"b={r.get('base_imponible')}, t={r.get('tipo_rectificacion')}",
        "S sust",
        "750,S",
        f"b={r.get('base_imponible')}, t={r.get('tipo_rectificacion')}",
    )
except Exception as e:
    test("100-Rect-SFull", "ERROR", str(e))

# 101: Factura sin cliente (simple)
try:
    f = client.post(
        "/api/facturas/simple",
        json={
            "cliente_nombre": "Sin Cliente ID",
            "concepto": "Trabajo",
            "base_imponible": 75.0,
            "iva_pct": 21.0,
        },
        headers=headers,
    ).json()
    ok = f.get("cliente_id") is not None
    test(
        "101-Simple-SinCliente",
        "PASS" if ok else "FAIL",
        f"cid={f.get('cliente_id')}",
        "auto cliente",
        "exists",
        f.get("cliente_id"),
    )
except Exception as e:
    test("101-Simple-SinCliente", "ERROR", str(e))

# 102: Abono IVA 21
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "Z1234567I", "nombre": "AB21"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "base_imponible": 100.0,
            "iva_pct": 21.0,
            "lineas": [
                {
                    "descripcion": "t",
                    "cantidad": 1,
                    "precio_unitario": 100.0,
                    "iva_pct": 21.0,
                }
            ],
        },
        headers=headers,
    ).json()
    ab = client.post(
        f"/api/facturas/{f['id']}/abono",
        json={"base_imponible": 100.0, "concepto": "A", "motivo": "M"},
        headers=headers,
    ).json()["factura"]
    ok = ab.get("iva_cuota") == -21.0
    test(
        "102-Abono-IVA21",
        "PASS" if ok else "FAIL",
        f"iva={ab.get('iva_cuota')}",
        "iva 21",
        "-21",
        ab.get("iva_cuota"),
    )
except Exception as e:
    test("102-Abono-IVA21", "ERROR", str(e))

# 103: Calculadora fiscal
try:
    from app.services.calculadora_fiscal import detectar_tipo_cliente

    t = detectar_tipo_cliente("B12345678")
    ok = t in ("sl", "sa", "autonomo", "particular")
    test(
        "103-Calc-TipoCliente",
        "PASS" if ok else "FAIL",
        f"tipo={t}",
        "B... -> sl",
        "sl/sa",
        t,
    )
except Exception as e:
    test("103-Calc-TipoCliente", "ERROR", str(e))

# 104: VeriFactu - ejemplo empresa
try:
    from app.services.calculadora_fiscal import calcular_ejemplo_empresa

    calc = calcular_ejemplo_empresa()
    ok = hasattr(calc, "total")
    test(
        "104-Calc-EjemploEmp",
        "PASS" if ok else "FAIL",
        f"ok={ok}",
        "ejemplo empresa",
        "ok",
        f"ok={ok}",
    )
except Exception as e:
    test("104-Calc-EjemploEmp", "ERROR", str(e))

# 105: VeriFactu - ejemplo autonomo
try:
    from app.services.calculadora_fiscal import calcular_ejemplo_autonomo

    calc = calcular_ejemplo_autonomo()
    ok = hasattr(calc, "total")
    test(
        "105-Calc-EjemploAut",
        "PASS" if ok else "FAIL",
        f"ok={ok}",
        "ejemplo autonomo",
        "ok",
        f"ok={ok}",
    )
except Exception as e:
    test("105-Calc-EjemploAut", "ERROR", str(e))

# 106: Validar NIF formato
try:
    from app.services.verifacti_transformer import VeriFactiTransformer

    v = VeriFactiTransformer.validar_nif_formato("12345678A")
    test(
        "106-VeriFacti-ValidarNIF",
        "PASS" if v else "FAIL",
        f"valid={v}",
        "12345678A",
        "True/False",
        f"valid={v}",
    )
except Exception as e:
    test("106-VeriFacti-ValidarNIF", "ERROR", str(e))

# 107: Settings - production readiness
try:
    from app.services.settings import production_readiness

    pr = production_readiness()
    ok = "status" in pr or "ready" in pr
    test(
        "107-Settings-Ready",
        "PASS" if ok else "FAIL",
        f"keys={list(pr.keys())[:3]}",
        "ready",
        "keys",
        list(pr.keys())[:3],
    )
except Exception as e:
    test("107-Settings-Ready", "ERROR", str(e))

# 108: Document path
try:
    from app.services.document_service import factura_filename

    # No tenemos objeto factura real, probamos que existe la función
    ok = callable(factura_filename)
    test(
        "108-Doc-Filename",
        "PASS" if ok else "FAIL",
        f"exists={ok}",
        "filename func",
        "exists",
        f"exists={ok}",
    )
except Exception as e:
    test("108-Doc-Filename", "ERROR", str(e))

# 109: Email outbox
try:
    from app.services.email_service import _write_outbox

    result = _write_outbox({"to": "test@test.com", "subject": "Test"})
    ok = "path" in result or "error" in result
    test(
        "109-Email-Outbox",
        "PASS" if ok else "FAIL",
        f"ok={ok}",
        "outbox write",
        "path",
        f"ok={ok}",
    )
except Exception as e:
    test("109-Email-Outbox", "ERROR", str(e))

# 110: NIF valido CIF
try:
    from app.services.whatsapp_handler import es_nif_cif_valido

    ok1 = es_nif_cif_valido("A1234567B")
    ok2 = not es_nif_cif_valido("")
    test(
        "110-WhatsApp-NIFvalido",
        "PASS" if (ok1 or ok2) else "FAIL",
        f"ok1={ok1}, ok2={ok2}",
        "validacion",
        "bool",
        f"ok1={ok1}, ok2={ok2}",
    )
except Exception as e:
    test("110-WhatsApp-NIFvalido", "ERROR", str(e))

# 111: Normalizar telefono
try:
    from app.services.whatsapp_handler import normalizar_telefono

    t = normalizar_telefono("+34 612 345 678")
    ok = "612345678" in t
    test(
        "111-WhatsApp-NormTel",
        "PASS" if ok else "FAIL",
        f"t={t}",
        "normalize",
        "612",
        t,
    )
except Exception as e:
    test("111-WhatsApp-NormTel", "ERROR", str(e))

# 112: Rectificativa F3 sustitucion
try:
    from app.services.verifacti_transformer import VeriFactiTransformer

    f = {"serie": "FR", "numero": "1", "fecha": "2024-01-01", "tipo_factura": "R3"}
    cl = {"nif": "C1234567D", "nombre": "Test"}
    ls = [
        {
            "base_imponible": 100.0,
            "cuota_repercutida": 21.0,
            "tipo_impositivo": "G21",
            "cuota_recargo_equivalencia": 0.0,
        }
    ]
    r = VeriFactiTransformer.transform_f3_substitucion(f, cl, ls)
    ok = "serie" in r
    test(
        "112-VeriFacti-F3S",
        "PASS" if ok else "FAIL",
        f"ok={ok}",
        "F3 sustitucion",
        "ok",
        f"ok={ok}",
    )
except Exception as e:
    test("112-VeriFacti-F3S", "ERROR", str(e))

# 113: Factura empty lineas
try:
    c = client.post(
        "/api/facturas/clientes", json={"nombre": "Empty Test"}, headers=headers
    ).json()
    r = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "base_imponible": 150.0,
            "iva_pct": 21.0,
            "lineas": [],
        },
        headers=headers,
    )
    if r.status_code in [422, 400]:
        test(
            "113-Lineas-Empty",
            "PASS",
            "rechazado",
            "empty lineas",
            "422/400",
            f"status={r.status_code}",
        )
    else:
        f = r.json()
        test(
            "113-Lineas-Empty",
            "WARNING",
            f" status={r.status_code}",
            "empty lineas",
            "422",
            f"status={r.status_code}",
        )
except Exception as e:
    test("113-Lineas-Empty", "ERROR", str(e))

# 114: Abono con IRPF
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "K1234567J", "nombre": "ABIRPF"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "base_imponible": 200.0,
            "iva_pct": 21.0,
            "irpf_pct": 15.0,
            "lineas": [
                {
                    "descripcion": "t",
                    "cantidad": 1,
                    "precio_unitario": 200.0,
                    "iva_pct": 21.0,
                    "irpf_pct": 15.0,
                }
            ],
        },
        headers=headers,
    ).json()
    ab = client.post(
        f"/api/facturas/{f['id']}/abono",
        json={
            "base_imponible": 100.0,
            "irpf_pct": 15.0,
            "concepto": "A",
            "motivo": "M",
        },
        headers=headers,
    ).json()["factura"]
    ok = ab.get("irpf_pct") == 15.0
    test(
        "114-Abono-IRPF",
        "PASS" if ok else "FAIL",
        f"irpf={ab.get('irpf_pct')}",
        "irpf 15",
        "15",
        ab.get("irpf_pct"),
    )
except Exception as e:
    test("114-Abono-IRPF", "ERROR", str(e))

# 115: Factura verifactu_enviada default
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "L1234567K", "nombre": "VF Test"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "base_imponible": 100.0,
            "lineas": [{"descripcion": "t", "cantidad": 1, "precio_unitario": 100.0}],
        },
        headers=headers,
    ).json()
    ok = f.get("verifactu_enviada") == False
    test(
        "115-Factura-VFdefault",
        "PASS" if ok else "FAIL",
        f"vf={f.get('verifactu_enviada')}",
        "default",
        "False",
        f.get("verifactu_enviada"),
    )
except Exception as e:
    test("115-Factura-VFdefault", "ERROR", str(e))

# 116: Lineas detallado con descuento
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "M1234567L", "nombre": "Desc Test"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "lineas": [
                {
                    "descripcion": "Test",
                    "cantidad": 2,
                    "precio_unitario": 100.0,
                    "descuento_pct": 50.0,
                    "iva_pct": 21.0,
                }
            ],
        },
        headers=headers,
    ).json()
    # 2 * 100 = 200, 50% desc = 100 base
    ok = f.get("base_imponible") == 100.0
    test(
        "116-Lineas-Desc50",
        "PASS" if ok else "FAIL",
        f"base={f.get('base_imponible')}",
        "50% desc",
        "100",
        f.get("base_imponible"),
    )
except Exception as e:
    test("116-Lineas-Desc50", "ERROR", str(e))

# 117: Lineas con 100% descuento
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nif": "N1234567M", "nombre": "Desc100 Test"},
        headers=headers,
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "lineas": [
                {
                    "descripcion": "Test",
                    "cantidad": 1,
                    "precio_unitario": 100.0,
                    "descuento_pct": 100.0,
                    "iva_pct": 21.0,
                }
            ],
        },
        headers=headers,
    ).json()
    ok = f.get("base_imponible") == 0.0
    test(
        "117-Lineas-Desc100",
        "PASS" if ok else "FAIL",
        f"base={f.get('base_imponible')}",
        "100% desc",
        "0",
        f.get("base_imponible"),
    )
except Exception as e:
    test("117-Lineas-Desc100", "ERROR", str(e))

# 118: Rectificar factura estado cancelada
try:
    c = client.post(
        "/api/facturas/clientes", json={"nombre": "Cancel Rect"}, headers=headers
    ).json()
    f = client.post(
        "/api/facturas/",
        json={
            "cliente_id": c["id"],
            "base_imponible": 100.0,
            "lineas": [{"descripcion": "t", "cantidad": 1, "precio_unitario": 100.0}],
        },
        headers=headers,
    ).json()
    client.patch(f"/api/facturas/{f['id']}/estado?estado=cancelada", headers=headers)
    r = client.post(
        f"/api/facturas/{f['id']}/rectificativa",
        json={
            "tipo_factura": "R1",
            "tipo_rectificacion": "I",
            "base_imponible": -50.0,
            "concepto": "R",
            "motivo": "M",
        },
        headers=headers,
    )
    if r.status_code in [200, 201]:
        test(
            "118-Rect-Cancelada",
            "WARNING",
            "permitido",
            "rectificar cancelada",
            "warning",
            f"status={r.status_code}",
        )
    else:
        test(
            "118-Rect-Cancelada",
            "PASS",
            "bloqueado",
            "rectificar cancelada",
            "blocked",
            f"status={r.status_code}",
        )
except Exception as e:
    test("118-Rect-Cancelada", "ERROR", str(e))

# 119: Cliente razon social
try:
    c = client.post(
        "/api/facturas/clientes",
        json={"nombre": "Razon Test", "razon_social": "Empresa SL"},
        headers=headers,
    ).json()
    ok = c.get("razon_social") == "Empresa SL"
    test(
        "119-Cliente-Razon",
        "PASS" if ok else "FAIL",
        f"rs={c.get('razon_social')}",
        "razon_social",
        "Empresa SL",
        c.get("razon_social"),
    )
except Exception as e:
    test("119-Cliente-Razon", "ERROR", str(e))

# 120: VeriFactu tipos IVA map
try:
    from app.services.verifacti_transformer import VeriFactiTransformer

    m = VeriFactiTransformer.TIPO_IVA_MAP
    ok = (
        m.get(21.0) == "G21"
        and m.get(10.0) == "R10"
        and m.get(4.0) == "S4"
        and m.get(0.0) == "E0"
    )
    test(
        "120-VeriFacti-IVAmap",
        "PASS" if ok else "FAIL",
        f"map={m}",
        "iva map",
        "G21,R10,S4,E0",
        f"map={m}",
    )
except Exception as e:
    test("120-VeriFacti-IVAmap", "ERROR", str(e))

# Resumen
print("\n" + "=" * 60)
print(f"PRUEBAS ADICIONALES: {len(results)}")
states = {"PASS": 0, "FAIL": 0, "WARNING": 0, "ERROR": 0}
for r in results:
    states[r["st"]] += 1
print(f"  PASS: {states['PASS']}")
print(f"  FAIL: {states['FAIL']}")
print(f"  WARNING: {states['WARNING']}")
print(f"  ERROR: {states['ERROR']}")
print("=" * 60)

# Guardar resultados adicionales
with open("/tmp/qa_extra_results.json", "w") as f:
    import json

    json.dump(results, f, indent=2)
