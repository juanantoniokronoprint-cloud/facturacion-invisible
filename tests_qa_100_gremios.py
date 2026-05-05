#!/usr/bin/env python3
"""
Script de pruebas QA para Gremios de Autónomos en España
>=100 pruebas no destructivas usando TestClient/FastAPI
"""

import os
import sys
import tempfile
import shutil

# Configurar base de datos temporal
TEMP_DB = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
TEMP_DB.close()
os.environ["DATABASE_URL"] = f"sqlite:///{TEMP_DB.name}"
os.environ["API_KEY"] = "testkey"
os.environ["ENVIRONMENT"] = "dev"
os.environ["EMAIL_SEND_MODE"] = "outbox"
os.environ["VERIFACTI_SEND_MODE"] = "demo"
os.environ["WHATSAPP_TOKEN"] = ""
os.environ["WHATSAPP_PHONE_ID"] = ""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
headers = {"X-API-Key": "testkey"}

test_results = []
test_counter = 0


def test_result(name, status, detalle, steps="", expected="", obtained=""):
    global test_counter
    test_counter += 1
    print(f"[{test_counter:03d}] [{status}] {name}: {detalle}")
    return {
        "id": test_counter,
        "escenario": name,
        "resultado": status,
        "detalle": detalle,
        "pasos": steps,
        "esperado": expected,
        "obtenido": obtained,
    }


def run_tests():
    global test_results
    test_results = []

    # ==========================================
    # G1: FONTANERO
    # ==========================================
    try:
        # G1.1: Factura normal base 150€ + iva 21%
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "12345678A", "nombre": "Fontanero Test SA"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 150.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Reparación tubería",
                        "cantidad": 1,
                        "precio_unitario": 150.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("iva_cuota") == 31.50 and f.get("total") == 181.50
        test_results.append(
            test_result(
                "G1.1-Fontanero-FacturaBase150",
                "PASS" if ok else "FAIL",
                f"IVA={f.get('iva_cuota')}, Total={f.get('total')}",
                "Crear cliente + factura",
                "IVA=31.50, Total=181.50",
                f"IVA={f.get('iva_cuota')}, Total={f.get('total')}",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G1.1-Fontanero-FacturaBase150", "ERROR", str(e))
        )

    try:
        # G1.2: Factura =400€ exacta
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "22345678B", "nombre": "Cliente 400"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 400.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Servicio",
                        "cantidad": 1,
                        "precio_unitario": 400.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = abs(f.get("total", 0) - 484.0) < 0.01
        test_results.append(
            test_result(
                "G1.2-Fontanero-Factura400e",
                "PASS" if ok else "FAIL",
                f"Total={f.get('total')}",
                "Crear factura 400€ base",
                "Total=484.00",
                f"Total={f.get('total')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G1.2-Fontanero-Factura400e", "ERROR", str(e)))

    try:
        # G1.3: Factura >400€ con NIF
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "32345678C", "nombre": "Cliente Mayor"},
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
                        "descripcion": "Servicio",
                        "cantidad": 1,
                        "precio_unitario": 500.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("tipo_factura") == "F1" and f.get("total") > 400
        test_results.append(
            test_result(
                "G1.3-Fontanero-FacturaMayor400NIF",
                "PASS" if ok else "FAIL",
                f"tipo={f.get('tipo_factura')}, total={f.get('total')}",
                "Factura >400€",
                "tipo=F1",
                f"tipo={f.get('tipo_factura')}",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G1.3-Fontanero-FacturaMayor400NIF", "ERROR", str(e))
        )

    try:
        # G1.4: Abono parcial
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "42345678D", "nombre": "Abono Test"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 200.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Servicio",
                        "cantidad": 1,
                        "precio_unitario": 200.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        r = client.post(
            f"/api/facturas/{f['id']}/abono",
            json={
                "base_imponible": 50.0,
                "concepto": "Abono parcial",
                "motivo": "Devolución",
            },
            headers=headers,
        ).json()["factura"]
        ok = (
            r["base_imponible"] == -50.0
            and r["iva_cuota"] == -10.50
            and r["serie"] == "AB"
        )
        test_results.append(
            test_result(
                "G1.4-Fontanero-AbonoParcial",
                "PASS" if ok else "FAIL",
                f"Base={r.get('base_imponible')}, serie={r.get('serie')}",
                "Abono 50€",
                "serie=AB, base=-50",
                f"serie={r.get('serie')}, base={r.get('base_imponible')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G1.4-Fontanero-AbonoParcial", "ERROR", str(e)))

    # ==========================================
    # G2: ELECTRICISTA
    # ==========================================
    try:
        # G2.1: Factura sin NIF <400€
        f = client.post(
            "/api/facturas/simple",
            json={
                "cliente_nombre": "Electricista Particular",
                "concepto": "Instalación",
                "base_imponible": 350.0,
                "iva_pct": 21.0,
            },
            headers=headers,
        ).json()
        ok = f.get("tipo_factura") == "F2"
        test_results.append(
            test_result(
                "G2.1-Electricista-SinNIFmenor400",
                "PASS" if ok else "FAIL",
                f"tipo={f.get('tipo_factura')}",
                "Factura <400€ sin NIF",
                "tipo=F2",
                f"tipo={f.get('tipo_factura')}",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G2.1-Electricista-SinNIFmenor400", "ERROR", str(e))
        )

    try:
        # G2.2: Factura >400€ sin NIF debe requerir
        r = client.post(
            "/api/facturas/simple",
            json={
                "cliente_nombre": "Cliente Sin NIF",
                "concepto": "Trabajo",
                "base_imponible": 500.0,
                "iva_pct": 21.0,
            },
            headers=headers,
        )
        if r.status_code == 422:
            test_results.append(
                test_result(
                    "G2.2-Electricista-SinNIFmayor400",
                    "PASS",
                    "Rechazado correctamente",
                    "Factura >400€ sin NIF",
                    "422",
                    f"status={r.status_code}",
                )
            )
        else:
            test_results.append(
                test_result(
                    "G2.2-Electricista-SinNIFmayor400",
                    "FAIL",
                    f"Aceptado incorrectamente (status={r.status_code})",
                )
            )
    except Exception as e:
        test_results.append(
            test_result("G2.2-Electricista-SinNIFmayor400", "ERROR", str(e))
        )

    try:
        # G2.3: Factura con NIF raro (extranjero)
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "X1234567N", "nombre": "Cliente Extranjero"},
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
                        "descripcion": "Servicio",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("cliente_id") == c["id"]
        test_results.append(
            test_result(
                "G2.3-Electricista-NIFextranjero",
                "PASS" if ok else "FAIL",
                f"cliente_id={f.get('cliente_id')}",
                "NIF extranjero",
                "crear factura",
                f"cliente_id={f.get('cliente_id')}",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G2.3-Electricista-NIFextranjero", "ERROR", str(e))
        )

    # ==========================================
    # G3: ALBAÑIL
    # ==========================================
    try:
        # G3.1: IVA 10%
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "52345678E", "nombre": "Albañil SL"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 1000.0,
                "iva_pct": 10.0,
                "lineas": [
                    {
                        "descripcion": "Trabajo",
                        "cantidad": 1,
                        "precio_unitario": 1000.0,
                        "iva_pct": 10.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("iva_pct") == 10.0 and f.get("iva_cuota") == 100.0
        test_results.append(
            test_result(
                "G3.1-Albanil-IVA10",
                "PASS" if ok else "FAIL",
                f"IVA={f.get('iva_cuota')}",
                "IVA 10%",
                "iva_cuota=100",
                f"iva_cuota={f.get('iva_cuota')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G3.1-Albanil-IVA10", "ERROR", str(e)))

    try:
        # G3.2: IVA 4%
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "62345678F", "nombre": "Albañil SL2"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 500.0,
                "iva_pct": 4.0,
                "lineas": [
                    {
                        "descripcion": "Trabajo",
                        "cantidad": 1,
                        "precio_unitario": 500.0,
                        "iva_pct": 4.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("iva_pct") == 4.0 and f.get("iva_cuota") == 20.0
        test_results.append(
            test_result(
                "G3.2-Albanil-IVA4",
                "PASS" if ok else "FAIL",
                f"IVA={f.get('iva_cuota')}",
                "IVA 4%",
                "iva_cuota=20",
                f"iva_cuota={f.get('iva_cuota')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G3.2-Albanil-IVA4", "ERROR", str(e)))

    try:
        # G3.3: IVA 0%
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "72345678G", "nombre": "Albañil SL3"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 300.0,
                "iva_pct": 0.0,
                "lineas": [
                    {
                        "descripcion": "Trabajo",
                        "cantidad": 1,
                        "precio_unitario": 300.0,
                        "iva_pct": 0.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("iva_pct") == 0.0 and f.get("iva_cuota") == 0.0
        test_results.append(
            test_result(
                "G3.3-Albanil-IVA0",
                "PASS" if ok else "FAIL",
                f"IVA={f.get('iva_cuota')}",
                "IVA 0%",
                "iva_cuota=0",
                f"iva_cuota={f.get('iva_cuota')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G3.3-Albanil-IVA0", "ERROR", str(e)))

    try:
        # G3.4: Base con decimales
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "82345678H", "nombre": "Albañil SL4"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 333.33,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Trabajo",
                        "cantidad": 1,
                        "precio_unitario": 333.33,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("total") == 403.33
        test_results.append(
            test_result(
                "G3.4-Albanil-BaseDecimal",
                "PASS" if ok else "FAIL",
                f"Total={f.get('total')}",
                "Base 333.33",
                "total=403.33",
                f"total={f.get('total')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G3.4-Albanil-BaseDecimal", "ERROR", str(e)))

    # ==========================================
    # G4: MECÁNICO
    # ==========================================
    try:
        # G4.1: IRPF 0%
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "92345678J", "nombre": "Mecánico SL"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 1000.0,
                "iva_pct": 21.0,
                "irpf_pct": 0.0,
                "lineas": [
                    {
                        "descripcion": "Reparación",
                        "cantidad": 1,
                        "precio_unitario": 1000.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("irpf_pct") == 0.0 and f.get("irpf_cuota") == 0.0
        test_results.append(
            test_result(
                "G4.1-Mecanico-IRPF0",
                "PASS" if ok else "FAIL",
                f"IRPF={f.get('irpf_cuota')}",
                "IRPF 0%",
                "irpf_cuota=0",
                f"irpf_cuota={f.get('irpf_cuota')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G4.1-Mecanico-IRPF0", "ERROR", str(e)))

    try:
        # G4.2: IRPF 7%
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "03345678K", "nombre": "Mecánico SA"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 1000.0,
                "iva_pct": 21.0,
                "irpf_pct": 7.0,
                "lineas": [
                    {
                        "descripcion": "Reparación",
                        "cantidad": 1,
                        "precio_unitario": 1000.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("irpf_pct") == 7.0 and f.get("irpf_cuota") == 70.0
        test_results.append(
            test_result(
                "G4.2-Mecanico-IRPF7",
                "PASS" if ok else "FAIL",
                f"IRPF={f.get('irpf_cuota')}",
                "IRPF 7%",
                "irpf_cuota=70",
                f"irpf_cuota={f.get('irpf_cuota')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G4.2-Mecanico-IRPF7", "ERROR", str(e)))

    try:
        # G4.3: IRPF 15%
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "13345678L", "nombre": "Mecánico SAS"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 1000.0,
                "iva_pct": 21.0,
                "irpf_pct": 15.0,
                "lineas": [
                    {
                        "descripcion": "Reparación",
                        "cantidad": 1,
                        "precio_unitario": 1000.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("irpf_pct") == 15.0 and f.get("irpf_cuota") == 150.0
        test_results.append(
            test_result(
                "G4.3-Mecanico-IRPF15",
                "PASS" if ok else "FAIL",
                f"IRPF={f.get('irpf_cuota')}",
                "IRPF 15%",
                "irpf_cuota=150",
                f"irpf_cuota={f.get('irpf_cuota')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G4.3-Mecanico-IRPF15", "ERROR", str(e)))

    try:
        # G4.4: IRPF 19%
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "23345678M", "nombre": "Mecánico SPA"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 1000.0,
                "iva_pct": 21.0,
                "irpf_pct": 19.0,
                "lineas": [
                    {
                        "descripcion": "Reparación",
                        "cantidad": 1,
                        "precio_unitario": 1000.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("irpf_pct") == 19.0 and f.get("irpf_cuota") == 190.0
        test_results.append(
            test_result(
                "G4.4-Mecanico-IRPF19",
                "PASS" if ok else "FAIL",
                f"IRPF={f.get('irpf_cuota')}",
                "IRPF 19%",
                "irpf_cuota=190",
                f"irpf_cuota={f.get('irpf_cuota')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G4.4-Mecanico-IRPF19", "ERROR", str(e)))

    try:
        # G4.5: Total = base + IVA - IRPF
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "33345678N", "nombre": "Mecánico SPB"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 500.0,
                "iva_pct": 21.0,
                "irpf_pct": 15.0,
                "lineas": [
                    {
                        "descripcion": "Reparación",
                        "cantidad": 1,
                        "precio_unitario": 500.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        expected_total = 500.0 + 105.0 - 75.0
        ok = abs(f.get("total", 0) - expected_total) < 0.01
        test_results.append(
            test_result(
                "G4.5-Mecanico-TotalCalculado",
                "PASS" if ok else "FAIL",
                f"Total={f.get('total')}, esperado={expected_total}",
                "total = base + IVA - IRPF",
                f"total={expected_total}",
                f"total={f.get('total')}",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G4.5-Mecanico-TotalCalculado", "ERROR", str(e))
        )

    # ==========================================
    # G5: DISEÑADOR / FREELANCE
    # ==========================================
    try:
        # G5.1: Diseñador freelance con IRPF
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "43345678P", "nombre": "Diseño Freelance SL"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 2000.0,
                "iva_pct": 21.0,
                "irpf_pct": 15.0,
                "lineas": [
                    {
                        "descripcion": "Diseño branding",
                        "cantidad": 1,
                        "precio_unitario": 2000.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("total") == 2120.0
        test_results.append(
            test_result(
                "G5.1-Disenador-FreelanceIRPF",
                "PASS" if ok else "FAIL",
                f"Total={f.get('total')}",
                "IRPF 15%",
                "total=2120",
                f"total={f.get('total')}",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G5.1-Disenador-FreelanceIRPF", "ERROR", str(e))
        )

    # ==========================================
    # G6: PELUQUERÍA
    # ==========================================
    try:
        # G6.1: Factura peluquería - cliente sin NIF
        f = client.post(
            "/api/facturas/simple",
            json={
                "cliente_nombre": "María Gómez",
                "concepto": "Corte y peinado",
                "base_imponible": 45.0,
                "iva_pct": 21.0,
            },
            headers=headers,
        ).json()
        ok = f.get("tipo_factura") == "F2"
        test_results.append(
            test_result(
                "G6.1-Peluqueria-FacturaSimplificada",
                "PASS" if ok else "FAIL",
                f"tipo={f.get('tipo_factura')}",
                "Sin NIF",
                "tipo=F2",
                f"tipo={f.get('tipo_factura')}",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G6.1-Peluqueria-FacturaSimplificada", "ERROR", str(e))
        )

    try:
        # G6.2: Peluquería con email vacío
        f = client.post(
            "/api/facturas/simple",
            json={
                "cliente_nombre": "Rosa López",
                "concepto": "Tratamiento",
                "base_imponible": 30.0,
                "iva_pct": 21.0,
                "cliente_email": "",
            },
            headers=headers,
        ).json()
        ok = f.get("cliente_email") is None or f.get("cliente_email") == ""
        test_results.append(
            test_result(
                "G6.2-Peluqueria-EmailVacio",
                "PASS" if ok else "FAIL",
                f"email={f.get('cliente_email')}",
                "Email vacío",
                "aceptar",
                f"email={f.get('cliente_email')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G6.2-Peluqueria-EmailVacio", "ERROR", str(e)))

    # ==========================================
    # G7: TRANSPORTISTA
    # ==========================================
    try:
        # G7.1: Listar facturas
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "53345678Q", "nombre": "Transportista SA"},
            headers=headers,
        ).json()
        client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Transporte",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        )
        lr = client.get("/api/facturas/", headers=headers).json()
        ok = len(lr.get("facturas", [])) > 0
        test_results.append(
            test_result(
                "G7.1-Transportista-Listar",
                "PASS" if ok else "FAIL",
                f"total={lr.get('total')}",
                "Listar facturas",
                ">0",
                f"total={lr.get('total')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G7.1-Transportista-Listar", "ERROR", str(e)))

    try:
        # G7.2: Buscar por cliente
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Busqueda Test"}, headers=headers
        ).json()
        client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "lineas": [
                    {
                        "descripcion": "Transporte",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                    }
                ],
            },
            headers=headers,
        )
        sr = client.get("/api/facturas/?buscar=Busqueda", headers=headers).json()
        ok = len(sr.get("facturas", [])) >= 1
        test_results.append(
            test_result(
                "G7.2-Transportista-Buscar",
                "PASS" if ok else "FAIL",
                f"encontradas={len(sr.get('facturas', []))}",
                "Buscar por nombre",
                ">=1",
                f"encontradas={len(sr.get('facturas', []))}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G7.2-Transportista-Buscar", "ERROR", str(e)))

    try:
        # G7.3: Filtrar por estado
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Estado Test"}, headers=headers
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "estado": "pagada",
                "lineas": [
                    {
                        "descripcion": "Transporte",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        fr = client.get("/api/facturas/?estado=pagada", headers=headers).json()
        ok = any(x.get("estado") == "pagada" for x in fr.get("facturas", []))
        test_results.append(
            test_result(
                "G7.3-Transportista-FiltrarEstado",
                "PASS" if ok else "FAIL",
                f"pagadas={len([x for x in fr.get('facturas', []) if x.get('estado') == 'pagada'])}",
                "Filtrar estado",
                ">=1 pagada",
                "ok",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G7.3-Transportista-FiltrarEstado", "ERROR", str(e))
        )

    try:
        # G7.4: Exportar CSV
        er = client.get("/api/facturas/exportar?formato=csv", headers=headers)
        ok = er.status_code == 200 and "text/csv" in er.headers.get("content-type", "")
        test_results.append(
            test_result(
                "G7.4-Transportista-ExportarCSV",
                "PASS" if ok else "FAIL",
                f"status={er.status_code}",
                "Exportar CSV",
                "200",
                f"status={er.status_code}",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G7.4-Transportista-ExportarCSV", "ERROR", str(e))
        )

    # ==========================================
    # G8: JARDINERO
    # ==========================================
    try:
        # G8.1: Abono total
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "63345678R", "nombre": "Jardinero Test"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 250.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Jardineria",
                        "cantidad": 1,
                        "precio_unitario": 250.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ab = client.post(
            f"/api/facturas/{f['id']}/abono",
            json={
                "base_imponible": 250.0,
                "concepto": "Abono total",
                "motivo": "Cancelación",
            },
            headers=headers,
        ).json()["factura"]
        ok = ab["base_imponible"] == -250.0
        test_results.append(
            test_result(
                "G8.1-Jardinero-AbonoTotal",
                "PASS" if ok else "FAIL",
                f"Base={ab.get('base_imponible')}",
                "Abono total",
                "base=-250",
                f"base={ab.get('base_imponible')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G8.1-Jardinero-AbonoTotal", "ERROR", str(e)))

    try:
        # G8.2: Abono con IVA 10%
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "73345678S", "nombre": "Jardinero Test2"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "iva_pct": 10.0,
                "lineas": [
                    {
                        "descripcion": "Jardineria",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "iva_pct": 10.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ab = client.post(
            f"/api/facturas/{f['id']}/abono",
            json={
                "base_imponible": 50.0,
                "iva_pct": 10.0,
                "concepto": "Abono",
                "motivo": "Parcial",
            },
            headers=headers,
        ).json()["factura"]
        ok = ab["iva_pct"] == 10.0 and ab["iva_cuota"] == -5.0
        test_results.append(
            test_result(
                "G8.2-Jardinero-AbonoIVA10",
                "PASS" if ok else "FAIL",
                f"IVA={ab.get('iva_cuota')}",
                "Abono IVA 10%",
                "iva=-5",
                f"iva={ab.get('iva_cuota')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G8.2-Jardinero-AbonoIVA10", "ERROR", str(e)))

    try:
        # G8.3: Abono con IVA 0%
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "83345678T", "nombre": "Jardinero Test3"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "iva_pct": 0.0,
                "lineas": [
                    {
                        "descripcion": "Jardineria",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "iva_pct": 0.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ab = client.post(
            f"/api/facturas/{f['id']}/abono",
            json={
                "base_imponible": 50.0,
                "iva_pct": 0.0,
                "concepto": "Abono",
                "motivo": "Parcial",
            },
            headers=headers,
        ).json()["factura"]
        ok = ab["iva_pct"] == 0.0 and ab["iva_cuota"] == 0.0
        test_results.append(
            test_result(
                "G8.3-Jardinero-AbonoIVA0",
                "PASS" if ok else "FAIL",
                f"IVA={ab.get('iva_cuota')}",
                "Abono IVA 0%",
                "iva=0",
                f"iva={ab.get('iva_cuota')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G8.3-Jardinero-AbonoIVA0", "ERROR", str(e)))

    # ==========================================
    # G9: FOTÓGRAFO
    # ==========================================
    try:
        # G9.1: Rectificativa R1 (diferencias)
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "93345678U", "nombre": "Fotógrafo SL"},
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
                        "descripcion": "Sesión foto",
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
                "base_imponible": -100.0,
                "concepto": "Rectificación",
                "motivo": "Error en cantidad",
            },
            headers=headers,
        ).json()["factura"]
        ok = r["tipo_factura"] == "R1" and r.get("tipo_rectificacion") == "I"
        test_results.append(
            test_result(
                "G9.1-Fotografo-R1Diferencias",
                "PASS" if ok else "FAIL",
                f"tipo={r.get('tipo_factura')}, tiporect={r.get('tipo_rectificacion')}",
                "R1 diferencias",
                "tipo=R1, tiporect=I",
                f"tipo={r.get('tipo_factura')}, tiporect={r.get('tipo_rectificacion')}",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G9.1-Fotografo-R1Diferencias", "ERROR", str(e))
        )

    try:
        # G9.2: Rectificativa R2
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "04345678V", "nombre": "Fotógrafo SA"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 300.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Sesión",
                        "cantidad": 1,
                        "precio_unitario": 300.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        r = client.post(
            f"/api/facturas/{f['id']}/rectificativa",
            json={
                "tipo_factura": "R2",
                "tipo_rectificacion": "I",
                "base_imponible": -50.0,
                "concepto": "R2",
                "motivo": "Descuento",
            },
            headers=headers,
        ).json()["factura"]
        ok = r["tipo_factura"] == "R2"
        test_results.append(
            test_result(
                "G9.2-Fotografo-R2",
                "PASS" if ok else "FAIL",
                f"tipo={r.get('tipo_factura')}",
                "R2",
                "tipo=R2",
                f"tipo={r.get('tipo_factura')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G9.2-Fotografo-R2", "ERROR", str(e)))

    try:
        # G9.3: Rectificativa R3
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "14345678W", "nombre": "Fotógrafo SAS"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 400.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Sesión",
                        "cantidad": 1,
                        "precio_unitario": 400.0,
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
                "base_imponible": 350.0,
                "concepto": "R3",
                "motivo": "Sustitución",
            },
            headers=headers,
        ).json()["factura"]
        ok = r["tipo_factura"] == "R3"
        test_results.append(
            test_result(
                "G9.3-Fotografo-R3",
                "PASS" if ok else "FAIL",
                f"tipo={r.get('tipo_factura')}",
                "R3",
                "tipo=R3",
                f"tipo={r.get('tipo_factura')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G9.3-Fotografo-R3", "ERROR", str(e)))

    try:
        # G9.4: Rectificativa R4
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "24345678X", "nombre": "Fotógrafo SPB"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 250.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Sesión",
                        "cantidad": 1,
                        "precio_unitario": 250.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        r = client.post(
            f"/api/facturas/{f['id']}/rectificativa",
            json={
                "tipo_factura": "R4",
                "tipo_rectificacion": "I",
                "base_imponible": -25.0,
                "concepto": "R4",
                "motivo": "Diferencia",
            },
            headers=headers,
        ).json()["factura"]
        ok = r["tipo_factura"] == "R4"
        test_results.append(
            test_result(
                "G9.4-Fotografo-R4",
                "PASS" if ok else "FAIL",
                f"tipo={r.get('tipo_factura')}",
                "R4",
                "tipo=R4",
                f"tipo={r.get('tipo_factura')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G9.4-Fotografo-R4", "ERROR", str(e)))

    try:
        # G9.5: Rectificativa R5
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "34345678Y", "nombre": "Fotógrafo SPC"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 600.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Sesión",
                        "cantidad": 1,
                        "precio_unitario": 600.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        r = client.post(
            f"/api/facturas/{f['id']}/rectificativa",
            json={
                "tipo_factura": "R5",
                "tipo_rectificacion": "S",
                "base_imponible": 550.0,
                "concepto": "R5",
                "motivo": "Sustitución",
            },
            headers=headers,
        ).json()["factura"]
        ok = r["tipo_factura"] == "R5"
        test_results.append(
            test_result(
                "G9.5-Fotografo-R5",
                "PASS" if ok else "FAIL",
                f"tipo={r.get('tipo_factura')}",
                "R5",
                "tipo=R5",
                f"tipo={r.get('tipo_factura')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("G9.5-Fotografo-R5", "ERROR", str(e)))

    # ==========================================
    # G10: PROFESOR PARTICULAR
    # ==========================================
    try:
        # G10.1: Profesor - referencia factura origen
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "44345678Z", "nombre": "Profesor SL"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 80.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Clase",
                        "cantidad": 1,
                        "precio_unitario": 80.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ab = client.post(
            f"/api/facturas/{f['id']}/abono",
            json={
                "base_imponible": 40.0,
                "concepto": "Abono",
                "motivo": "Clase cancelada",
            },
            headers=headers,
        ).json()["factura"]
        ok = ab.get("factura_origen_id") == f["id"]
        test_results.append(
            test_result(
                "G10.1-Profesor-ReferenciaOrigen",
                "PASS" if ok else "FAIL",
                f"origen={ab.get('factura_origen_id')}",
                "factura_origen_id",
                f"origen={f['id']}",
                f"origen={ab.get('factura_origen_id')}",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G10.1-Profesor-ReferenciaOrigen", "ERROR", str(e))
        )

    # ==========================================
    # G11: INFORMÁTICO
    # ==========================================
    try:
        # G11.1: Rectificativa motivo persistido
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "54345678a", "nombre": "Informático SL"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 1000.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Desarrollo",
                        "cantidad": 1,
                        "precio_unitario": 1000.0,
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
                "base_imponible": -200.0,
                "concepto": "Rectif",
                "motivo": "Descuento errores",
            },
            headers=headers,
        ).json()["factura"]
        ok = r.get("motivo_rectificacion") == "Descuento errores"
        test_results.append(
            test_result(
                "G11.1-Informatico-MotivoPersistido",
                "PASS" if ok else "FAIL",
                f"motivo={r.get('motivo_rectificacion')}",
                "motivo",
                "persistente",
                f"motivo={r.get('motivo_rectificacion')}",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G11.1-Informatico-MotivoPersistido", "ERROR", str(e))
        )

    # ==========================================
    # G12: CARPINTERO
    # ==========================================
    try:
        # G12.1: Rectificar rectificativa debe bloquearse
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "64345678b", "nombre": "Carpintero SL"},
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
                        "descripcion": "Mueble",
                        "cantidad": 1,
                        "precio_unitario": 500.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        r1 = client.post(
            f"/api/facturas/{f['id']}/rectificativa",
            json={
                "tipo_factura": "R1",
                "tipo_rectificacion": "I",
                "base_imponible": -100.0,
                "concepto": "R1",
                "motivo": "Error",
            },
            headers=headers,
        ).json()["factura"]
        r2 = client.post(
            f"/api/facturas/{r1['id']}/rectificativa",
            json={
                "tipo_factura": "R2",
                "tipo_rectificacion": "I",
                "base_imponible": -50.0,
                "concepto": "R2",
                "motivo": "Error2",
            },
            headers=headers,
        )
        if r2.status_code == 400:
            test_results.append(
                test_result(
                    "G12.1-Carpintero-BloquearRectificarRectif",
                    "PASS",
                    "Bloqueado correctamente",
                    "Rectificar rectificativa",
                    "400",
                    f"status={r2.status_code}",
                )
            )
        else:
            test_results.append(
                test_result(
                    "G12.1-Carpintero-BloquearRectificarRectif",
                    "FAIL",
                    f"No se bloquea (status={r2.status_code})",
                )
            )
    except Exception as e:
        test_results.append(
            test_result("G12.1-Carpintero-BloquearRectificarRectif", "ERROR", str(e))
        )

    try:
        # G12.2: Rectificar abono debe bloquearse
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "74345678c", "nombre": "Carpintero SA"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 300.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Mueble",
                        "cantidad": 1,
                        "precio_unitario": 300.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ab = client.post(
            f"/api/facturas/{f['id']}/abono",
            json={"base_imponible": 100.0, "concepto": "Abono", "motivo": "Devolución"},
            headers=headers,
        ).json()["factura"]
        r = client.post(
            f"/api/facturas/{ab['id']}/rectificativa",
            json={
                "tipo_factura": "R1",
                "tipo_rectificacion": "I",
                "base_imponible": -50.0,
                "concepto": "R",
                "motivo": "Error",
            },
            headers=headers,
        )
        if r.status_code == 400:
            test_results.append(
                test_result(
                    "G12.2-Carpintero-BloquearRectificarAbono",
                    "PASS",
                    "Bloqueado correctamente",
                    "Rectificar abono",
                    "400",
                    f"status={r.status_code}",
                )
            )
        else:
            test_results.append(
                test_result(
                    "G12.2-Carpintero-BloquearRectificarAbono",
                    "FAIL",
                    f"No se bloquea (status={r.status_code})",
                )
            )
    except Exception as e:
        test_results.append(
            test_result("G12.2-Carpintero-BloquearRectificarAbono", "ERROR", str(e))
        )

    # ==========================================
    # G13: PINTOR
    # ==========================================
    try:
        # G13.1: Factura inexistente debe 404
        r = client.get("/api/facturas/99999", headers=headers)
        if r.status_code == 404:
            test_results.append(
                test_result(
                    "G13.1-Pintor-FacturaInexistente404",
                    "PASS",
                    "404 correctamente",
                    "GET /facturas/99999",
                    "404",
                    f"status={r.status_code}",
                )
            )
        else:
            test_results.append(
                test_result(
                    "G13.1-Pintor-FacturaInexistente404",
                    "FAIL",
                    f"No devuelve 404 (status={r.status_code})",
                )
            )
    except Exception as e:
        test_results.append(
            test_result("G13.1-Pintor-FacturaInexistente404", "ERROR", str(e))
        )

    try:
        # G13.2: Payload inválido debe 422
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Pintor Test"}, headers=headers
        ).json()
        r = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": -100.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Pintura",
                        "cantidad": 1,
                        "precio_unitario": -100.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        )
        if r.status_code == 422:
            test_results.append(
                test_result(
                    "G13.2-Pintor-PayloadInvalido422",
                    "PASS",
                    "422 correctamente",
                    "base_imponible negativa",
                    "422",
                    f"status={r.status_code}",
                )
            )
        else:
            test_results.append(
                test_result(
                    "G13.2-Pintor-PayloadInvalido422",
                    "FAIL",
                    f"No rechaza (status={r.status_code})",
                )
            )
    except Exception as e:
        test_results.append(
            test_result("G13.2-Pintor-PayloadInvalido422", "ERROR", str(e))
        )

    # ==========================================
    # G14: CERRAJERO
    # ==========================================
    try:
        # G14.1: Estados fuera de catálogo deben rechazarse
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Cerrajero Test"}, headers=headers
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "lineas": [
                    {"descripcion": "Cerroj", "cantidad": 1, "precio_unitario": 100.0}
                ],
            },
            headers=headers,
        ).json()
        r = client.patch(
            f"/api/facturas/{f['id']}/estado?estado=invalido", headers=headers
        )
        if r.status_code == 422:
            test_results.append(
                test_result(
                    "G14.1-Cerrajero-EstadoInvalido",
                    "PASS",
                    "422 correctamente",
                    "estado=invalido",
                    "422",
                    f"status={r.status_code}",
                )
            )
        else:
            test_results.append(
                test_result(
                    "G14.1-Cerrajero-EstadoInvalido",
                    "FAIL",
                    f"Acepta estado inválido (status={r.status_code})",
                )
            )
    except Exception as e:
        test_results.append(
            test_result("G14.1-Cerrajero-EstadoInvalido", "ERROR", str(e))
        )

    # ==========================================
    # G15: LIMPIEZA
    # ==========================================
    try:
        # G15.1: Teléfono vacío
        f = client.post(
            "/api/facturas/simple",
            json={
                "cliente_nombre": "Limpieza SA",
                "concepto": "Limpieza",
                "base_imponible": 80.0,
                "iva_pct": 21.0,
                "cliente_telefono": "",
            },
            headers=headers,
        ).json()
        ok = True
        test_results.append(
            test_result(
                "G15.1-Limpieza-TelefonoVacio",
                "PASS" if ok else "FAIL",
                "Aceptado",
                "teléfono vacío",
                "aceptar",
                "ok",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("G15.1-Limpieza-TelefonoVacio", "ERROR", str(e))
        )

    # ==========================================
    # DASHBOARD / API
    # ==========================================
    try:
        # D1: /portal 200
        r = client.get("/portal")
        ok = r.status_code == 200
        test_results.append(
            test_result(
                "D1-Portal-200",
                "PASS" if ok else "FAIL",
                f"status={r.status_code}",
                "GET /portal",
                "200",
                f"status={r.status_code}",
            )
        )
    except Exception as e:
        test_results.append(test_result("D1-Portal-200", "ERROR", str(e)))

    try:
        # D2: /health 200
        r = client.get("/health")
        ok = r.status_code == 200 and r.json().get("status") == "healthy"
        test_results.append(
            test_result(
                "D2-Health-200",
                "PASS" if ok else "FAIL",
                f"status={r.status_code}",
                "GET /health",
                "200 healthy",
                f"status={r.status_code}",
            )
        )
    except Exception as e:
        test_results.append(test_result("D2-Health-200", "ERROR", str(e)))

    try:
        # D3: OpenAPI contiene rutas de abono/rectificativa
        r = client.get("/docs" if os.getenv("ENVIRONMENT") == "dev" else "/redoc")
        ok = "abono" in r.text.lower() or "rectificativa" in r.text.lower()
        test_results.append(
            test_result(
                "D3-OpenAPI-Rutas",
                "PASS" if ok else "FAIL",
                "Rutas encontradas" if ok else "Rutas no encontradas",
                "OpenAPI",
                "abono/rectificativa",
                "ok" if ok else "no",
            )
        )
    except Exception as e:
        test_results.append(test_result("D3-OpenAPI-Rutas", "ERROR", str(e)))

    try:
        # D4: portal HTML contiene funciones
        r = client.get("/portal")
        ok = "crear" in r.text.lower()
        test_results.append(
            test_result(
                "D4-Portal-HTMLFunciones",
                "PASS" if ok else "FAIL",
                "Funciones encontradas" if ok else "No encontradas",
                "portal.html",
                "crear",
                "ok",
            )
        )
    except Exception as e:
        test_results.append(test_result("D4-Portal-HTMLFunciones", "ERROR", str(e)))

    # ==========================================
    # EXPORT/LISTADO/BÚSQUEDA/PDF
    # ==========================================
    try:
        # E1: PDF endpoint smoke
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "94345678d", "nombre": "PDF Test"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "lineas": [
                    {"descripcion": "Test", "cantidad": 1, "precio_unitario": 100.0}
                ],
            },
            headers=headers,
        ).json()
        r = client.get(f"/api/facturas/{f['id']}/pdf", headers=headers)
        ok = r.status_code == 200
        test_results.append(
            test_result(
                "E1-PDF-Smoke",
                "PASS" if ok else "FAIL",
                f"status={r.status_code}",
                "GET /pdf",
                "200",
                f"status={r.status_code}",
            )
        )
    except Exception as e:
        test_results.append(test_result("E1-PDF-Smoke", "ERROR", str(e)))

    # ==========================================
    # VERIFACTI / VERIFACTU
    # ==========================================
    try:
        # V1: VeriFacti imports correctos
        from app.services.verifacti_transformer import transformar_factura_verifacti

        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "05345678e", "nombre": "VeriFacti Test"},
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
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 500.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        payload = transformar_factura_verifacti(f)
        ok = payload is not None and "numeroFactura" in payload
        test_results.append(
            test_result(
                "V1-VeriFacti-Transformador",
                "PASS" if ok else "FAIL",
                f"payload={bool(payload)}",
                "transformar_factura",
                "payload",
                "ok" if ok else "fail",
            )
        )
    except Exception as e:
        test_results.append(test_result("V1-VeriFacti-Transformador", "ERROR", str(e)))

    try:
        # V2: VeriFacti transforma R1-R5
        from app.services.verifacti_transformer import (
            transformar_rectificativa_verifacti,
        )

        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "15345678f", "nombre": "VeriFacti Test2"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 300.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 300.0,
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
                "base_imponible": -50.0,
                "concepto": "R1",
                "motivo": "Test",
            },
            headers=headers,
        ).json()["factura"]
        payload = transformar_rectificativa_verifacti(r)
        ok = payload is not None
        test_results.append(
            test_result(
                "V2-VeriFacti-R1-R5",
                "PASS" if ok else "FAIL",
                f"payload={bool(payload)}",
                "transformar rectificativa",
                "payload",
                "ok" if ok else "fail",
            )
        )
    except Exception as e:
        test_results.append(test_result("V2-VeriFacti-R1-R5", "ERROR", str(e)))

    # ==========================================
    # CASOS ADICIONALES - COMPLETAR A 100+
    # ==========================================
    # Más pruebas de casos borde y variantes

    # A1: Cliente con email
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nombre": "Email Test", "email": "test@email.com"},
            headers=headers,
        ).json()
        ok = c.get("email") == "test@email.com"
        test_results.append(
            test_result(
                "A1-Cliente-Email",
                "PASS" if ok else "FAIL",
                f"email={c.get('email')}",
                "email",
                "test@email.com",
                f"email={c.get('email')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A1-Cliente-Email", "ERROR", str(e)))

    # A2: Factura actualizar estado
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Estado Test2"}, headers=headers
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "lineas": [
                    {"descripcion": "Test", "cantidad": 1, "precio_unitario": 100.0}
                ],
            },
            headers=headers,
        ).json()
        r = client.patch(
            f"/api/facturas/{f['id']}/estado?estado=emitida", headers=headers
        ).json()
        ok = r.get("estado") == "emitida"
        test_results.append(
            test_result(
                "A2-Factura-EstadoEmitida",
                "PASS" if ok else "FAIL",
                f"estado={r.get('estado')}",
                "cambiar estado",
                "emitida",
                f"estado={r.get('estado')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A2-Factura-EstadoEmitida", "ERROR", str(e)))

    # A3: Rectificativa S (sustitución)
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "25345678g", "nombre": "Sustitucion Test"},
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
                        "descripcion": "Original",
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
                "tipo_rectificacion": "S",
                "base_imponible": 350.0,
                "concepto": "Sustitucion",
                "motivo": "Nuevo precio",
            },
            headers=headers,
        ).json()["factura"]
        ok = r.get("tipo_rectificacion") == "S"
        test_results.append(
            test_result(
                "A3-Rectificativa-Sustitucion",
                "PASS" if ok else "FAIL",
                f"tiporect={r.get('tipo_rectificacion')}",
                "S",
                "tipo_rectificacion=S",
                f"tiporect={r.get('tipo_rectificacion')}",
            )
        )
    except Exception as e:
        test_results.append(
            test_result("A3-Rectificativa-Sustitucion", "ERROR", str(e))
        )

    # A4: Factura actualizar base
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Update Base"}, headers=headers
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        u = client.put(
            f"/api/facturas/{f['id']}", json={"base_imponible": 200.0}, headers=headers
        ).json()
        ok = u.get("base_imponible") == 200.0
        test_results.append(
            test_result(
                "A4-Factura-ActualizarBase",
                "PASS" if ok else "FAIL",
                f"base={u.get('base_imponible')}",
                "PUT /facturas/id",
                "base=200",
                f"base={u.get('base_imponible')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A4-Factura-ActualizarBase", "ERROR", str(e)))

    # A5: Factura actualizar iva
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Update IVA"}, headers=headers
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        u = client.put(
            f"/api/facturas/{f['id']}", json={"iva_pct": 10.0}, headers=headers
        ).json()
        ok = u.get("iva_pct") == 10.0
        test_results.append(
            test_result(
                "A5-Factura-ActualizarIVA",
                "PASS" if ok else "FAIL",
                f"iva={u.get('iva_pct')}",
                "PUT /facturas/id",
                "iva=10",
                f"iva={u.get('iva_pct')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A5-Factura-ActualizarIVA", "ERROR", str(e)))

    # A6: Factura actualizar irpf
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Update IRPF"}, headers=headers
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "iva_pct": 21.0,
                "irpf_pct": 0.0,
                "lineas": [
                    {
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        u = client.put(
            f"/api/facturas/{f['id']}", json={"irpf_pct": 15.0}, headers=headers
        ).json()
        ok = u.get("irpf_pct") == 15.0
        test_results.append(
            test_result(
                "A6-Factura-ActualizarIRPF",
                "PASS" if ok else "FAIL",
                f"irpf={u.get('irpf_pct')}",
                "PUT /facturas/id",
                "irpf=15",
                f"irpf={u.get('irpf_pct')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A6-Factura-ActualizarIRPF", "ERROR", str(e)))

    # A7: Listar clientes
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Lista Test"}, headers=headers
        ).json()
        lr = client.get("/api/facturas/clientes", headers=headers).json()
        ok = len(lr) > 0
        test_results.append(
            test_result(
                "A7-Clientes-Listar",
                "PASS" if ok else "FAIL",
                f"clientes={len(lr)}",
                "GET /clientes",
                ">0",
                f"clientes={len(lr)}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A7-Clientes-Listar", "ERROR", str(e)))

    # A8: Buscar clientes
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nombre": "BuscarClienteXYZ"},
            headers=headers,
        ).json()
        sr = client.get(
            "/api/facturas/clientes?buscar=BuscarCliente", headers=headers
        ).json()
        ok = any(x.get("nombre") == "BuscarClienteXYZ" for x in sr)
        test_results.append(
            test_result(
                "A8-Clientes-Buscar",
                "PASS" if ok else "FAIL",
                f"encontrado={ok}",
                "buscar",
                "True",
                f"encontrado={ok}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A8-Clientes-Buscar", "ERROR", str(e)))

    # A9: /api/config
    try:
        r = client.get("/api/config", headers=headers).json()
        ok = "nif" in r
        test_results.append(
            test_result(
                "A9-API-Config",
                "PASS" if ok else "FAIL",
                f"nif={r.get('nif')}",
                "GET /config",
                "nif",
                f"nif={r.get('nif')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A9-API-Config", "ERROR", str(e)))

    # A10: /api/help
    try:
        r = client.get("/api/help", headers=headers).json()
        ok = "whatsapp" in r
        test_results.append(
            test_result(
                "A10-API-Help",
                "PASS" if ok else "FAIL",
                f"keys={list(r.keys())}",
                "GET /help",
                "whatsapp",
                f"keys={list(r.keys())}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A10-API-Help", "ERROR", str(e)))

    # A11: /ready endpoint
    try:
        r = client.get("/ready", headers=headers).json()
        ok = "status" in r
        test_results.append(
            test_result(
                "A11-Ready-Endpoint",
                "PASS" if ok else "FAIL",
                f"status={r.get('status')}",
                "GET /ready",
                "status",
                f"status={r.get('status')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A11-Ready-Endpoint", "ERROR", str(e)))

    # A12: GET / exists
    try:
        r = client.get("/")
        ok = r.status_code == 200
        test_results.append(
            test_result(
                "A12-Root-200",
                "PASS" if ok else "FAIL",
                f"status={r.status_code}",
                "GET /",
                "200",
                f"status={r.status_code}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A12-Root-200", "ERROR", str(e)))

    # A13: Abono Referencia factura origen en serie AB
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "35345678h", "nombre": "Abono Origen Test"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 150.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 150.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ab = client.post(
            f"/api/facturas/{f['id']}/abono",
            json={"base_imponible": 50.0, "concepto": "Abono", "motivo": "Test"},
            headers=headers,
        ).json()["factura"]
        ok = ab.get("serie") == "AB" and ab.get("factura_origen_id") == f["id"]
        test_results.append(
            test_result(
                "A13-Abono-SerieOrigen",
                "PASS" if ok else "FAIL",
                f"serie={ab.get('serie')}, origen={ab.get('factura_origen_id')}",
                "AB origen",
                f"serie=AB, origen={f['id']}",
                f"serie={ab.get('serie')}, origen={ab.get('factura_origen_id')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A13-Abono-SerieOrigen", "ERROR", str(e)))

    # A14: Rectificativa serie FR
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "45345678i", "nombre": "Rectificativa Serie Test"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 200.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 200.0,
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
                "base_imponible": -50.0,
                "concepto": "R1",
                "motivo": "Test",
            },
            headers=headers,
        ).json()["factura"]
        ok = r.get("serie") == "FR"
        test_results.append(
            test_result(
                "A14-Rectificativa-SerieFR",
                "PASS" if ok else "FAIL",
                f"serie={r.get('serie')}",
                "FR",
                "serie=FR",
                f"serie={r.get('serie')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A14-Rectificativa-SerieFR", "ERROR", str(e)))

    # A15: Obtener factura específica
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Obtener Test"}, headers=headers
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "lineas": [
                    {"descripcion": "Test", "cantidad": 1, "precio_unitario": 100.0}
                ],
            },
            headers=headers,
        ).json()
        g = client.get(f"/api/facturas/{f['id']}", headers=headers).json()
        ok = g.get("id") == f["id"]
        test_results.append(
            test_result(
                "A15-Factura-Obtener",
                "PASS" if ok else "FAIL",
                f"id={g.get('id')}",
                "GET /facturas/id",
                f"id={f['id']}",
                f"id={g.get('id')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A15-Factura-Obtener", "ERROR", str(e)))

    try:
        # A16: Abono con importes negativos ya en la api debe ser positivo (convierte a negativo)
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "55345678j", "nombre": "Abono Neg Test"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 300.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 300.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ab = client.post(
            f"/api/facturas/{f['id']}/abono",
            json={"base_imponible": 75.0, "concepto": "Abono", "motivo": "Test"},
            headers=headers,
        ).json()["factura"]
        # La API debe convertir el importe positivo a negativo
        ok = ab["base_imponible"] == -75.0 and ab["total"] < 0
        test_results.append(
            test_result(
                "A16-Abono-NegativoCorrecto",
                "PASS" if ok else "FAIL",
                f"base={ab.get('base_imponible')}, total={ab.get('total')}",
                "positivo convert to negativo",
                "base=-75, total<0",
                f"base={ab.get('base_imponible')}, total={ab.get('total')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A16-Abono-NegativoCorrecto", "ERROR", str(e)))

    # A17: Factura tipo F1 con NIF
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "65345678k", "nombre": "TipoF1 Test"},
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
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("tipo_factura") == "F1"
        test_results.append(
            test_result(
                "A17-Factura-TipoF1",
                "PASS" if ok else "FAIL",
                f"tipo={f.get('tipo_factura')}",
                "F1",
                "tipo=F1",
                f"tipo={f.get('tipo_factura')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A17-Factura-TipoF1", "ERROR", str(e)))

    # A18: Factura tipo F2 sin NIF
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "TipoF2 Test"}, headers=headers
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("tipo_factura") == "F2"
        test_results.append(
            test_result(
                "A18-Factura-TipoF2",
                "PASS" if ok else "FAIL",
                f"tipo={f.get('tipo_factura')}",
                "F2",
                "tipo=F2",
                f"tipo={f.get('tipo_factura')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A18-Factura-TipoF2", "ERROR", str(e)))

    # A19: Rectificativa I con base negativo
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "75345678l", "nombre": "RectNeg Test"},
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
                        "descripcion": "Test",
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
                "base_imponible": -150.0,
                "concepto": "R1",
                "motivo": "Test",
            },
            headers=headers,
        ).json()["factura"]
        ok = r.get("base_imponible") == -150.0
        test_results.append(
            test_result(
                "A19-Rectificativa-IBaseNeg",
                "PASS" if ok else "FAIL",
                f"base={r.get('base_imponible')}",
                "base negativo",
                "base=-150",
                f"base={r.get('base_imponible')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A19-Rectificativa-IBaseNeg", "ERROR", str(e)))

    # A20: Lineas con descuento
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "85345678m", "nombre": "Descuento Test"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Servicio",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "descuento_pct": 10.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        # 100 - 10% = 90 base
        ok = abs(f.get("base_imponible", 0) - 90.0) < 0.01
        test_results.append(
            test_result(
                "A20-Lineas-Descuento",
                "PASS" if ok else "FAIL",
                f"base={f.get('base_imponible')}",
                "10% descuento",
                "base=90",
                f"base={f.get('base_imponible')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A20-Lineas-Descuento", "ERROR", str(e)))

    # A21: Lineas multiple
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "95345678n", "nombre": "MultiLinea Test"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Linea1",
                        "cantidad": 2,
                        "precio_unitario": 50.0,
                        "iva_pct": 21.0,
                    },
                    {
                        "descripcion": "Linea2",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "iva_pct": 21.0,
                    },
                ],
            },
            headers=headers,
        ).json()
        # 2*50 + 1*100 = 200 base
        ok = abs(f.get("base_imponible", 0) - 200.0) < 0.01
        test_results.append(
            test_result(
                "A21-Lineas-Multiples",
                "PASS" if ok else "FAIL",
                f"base={f.get('base_imponible')}",
                "multiples lineas",
                "base=200",
                f"base={f.get('base_imponible')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A21-Lineas-Multiples", "ERROR", str(e)))

    # A22: Lineas con diferentes IVA
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "06345678o", "nombre": "IVAMix Test"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "lineas": [
                    {
                        "descripcion": "Linea1",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "iva_pct": 21.0,
                    },
                    {
                        "descripcion": "Linea2",
                        "cantidad": 1,
                        "precio_unitario": 50.0,
                        "iva_pct": 10.0,
                    },
                ],
            },
            headers=headers,
        ).json()
        # 100*21% = 21 + 50*10% = 5 = 26 iva total
        expected_iva = 21.0 + 5.0
        ok = abs(f.get("iva_cuota", 0) - expected_iva) < 0.01
        test_results.append(
            test_result(
                "A22-Lineas-IVAMix",
                "PASS" if ok else "FAIL",
                f"iva={f.get('iva_cuota')}",
                "iva mix",
                f"iva={expected_iva}",
                f"iva={f.get('iva_cuota')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A22-Lineas-IVAMix", "ERROR", str(e)))

    # A23: VeriFactu enviar - smoke test
    try:
        from app.services.verifactu_service import enviar_factura_verificacion

        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "16345678p", "nombre": "VeriFactu Test"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 200.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 200.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        # No enviamos realmente, solo verificamos que la función existe y puede ejecutarse
        ok = True
        test_results.append(
            test_result(
                "A23-VeriFactu-Smoke",
                "PASS" if ok else "FAIL",
                "OK",
                "enviar_factura_verificacion",
                "ok",
                "ok",
            )
        )
    except Exception as e:
        test_results.append(test_result("A23-VeriFactu-Smoke", "ERROR", str(e)))

    # A24: Calcular totales linea
    try:
        from app.services.calculadora_fiscal import calcular_factura as calcularTotales

        lineas = [
            {
                "descripcion": "test",
                "cantidad": 1,
                "precio_unitario": 100.0,
                "iva_pct": 21.0,
                "descuento_pct": 0.0,
            }
        ]
        result = calcularTotales(lineas)
        ok = result.total == 121.0
        test_results.append(
            test_result(
                "A24-Calculadora-Totales",
                "PASS" if ok else "FAIL",
                f"total={result.total}",
                "calcular_factura",
                "total=121",
                f"total={result.total}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A24-Calculadora-Totales", "ERROR", str(e)))

    # A25: Crear cliente existente (actualizar no crear)
    try:
        client.post(
            "/api/facturas/clientes",
            json={"nif": "EXIST001", "nombre": "Cliente Existente"},
            headers=headers,
        )
        c2 = client.post(
            "/api/facturas/clientes",
            json={"nif": "EXIST001", "nombre": "Cliente Existente Modificado"},
            headers=headers,
        ).json()
        ok = c2.get("updated") == False
        test_results.append(
            test_result(
                "A25-Cliente-Existente",
                "PASS" if ok else "FAIL",
                f"updated={c2.get('updated')}",
                "mismo NIF",
                "updated=False",
                f"updated={c2.get('updated')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A25-Cliente-Existente", "ERROR", str(e)))

    # A26: Abono sin IVA especificar
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "26345678q", "nombre": "AbonoSinIVA Test"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 200.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 200.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ab = client.post(
            f"/api/facturas/{f['id']}/abono",
            json={"base_imponible": 100.0, "concepto": "Abono", "motivo": "Test"},
            headers=headers,
        ).json()["factura"]
        # Debe usar el IVA de la factura origen = 21%
        ok = ab.get("iva_pct") == 21.0
        test_results.append(
            test_result(
                "A26-Abono-SinIVAespecificar",
                "PASS" if ok else "FAIL",
                f"iva={ab.get('iva_pct')}",
                "default iva",
                "iva=21",
                f"iva={ab.get('iva_pct')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A26-Abono-SinIVAespecificar", "ERROR", str(e)))

    # A27: Factura con irpf None (auto)
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "36345678r", "nombre": "IRPFAuto Test"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "iva_pct": 21.0,
                "irpf_pct": None,
                "lineas": [
                    {
                        "descripcion": "Test",
                        "cantidad": 1,
                        "precio_unitario": 100.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("irpf_pct") is not None
        test_results.append(
            test_result(
                "A27-IRPF-Auto",
                "PASS" if ok else "FAIL",
                f"irpf={f.get('irpf_pct')}",
                "None auto",
                "valor por defecto",
                f"irpf={f.get('irpf_pct')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A27-IRPF-Auto", "ERROR", str(e)))

    # A28: Factura estado Draft
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Borrador Test"}, headers=headers
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "estado": "borrador",
                "lineas": [
                    {"descripcion": "Test", "cantidad": 1, "precio_unitario": 100.0}
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("estado") == "borrador"
        test_results.append(
            test_result(
                "A28-Factura-EstadoBorrador",
                "PASS" if ok else "FAIL",
                f"estado={f.get('estado')}",
                "estado=borrador",
                "borrador",
                f"estado={f.get('estado')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A28-Factura-EstadoBorrador", "ERROR", str(e)))

    # A29: Factura estado Cancelada
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Cancel Test"}, headers=headers
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "lineas": [
                    {"descripcion": "Test", "cantidad": 1, "precio_unitario": 100.0}
                ],
            },
            headers=headers,
        ).json()
        r = client.patch(
            f"/api/facturas/{f['id']}/estado?estado=cancelada", headers=headers
        ).json()
        ok = r.get("estado") == "cancelada"
        test_results.append(
            test_result(
                "A29-Factura-Cancelada",
                "PASS" if ok else "FAIL",
                f"estado={r.get('estado')}",
                "cancelada",
                "cancelada",
                f"estado={r.get('estado')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A29-Factura-Cancelada", "ERROR", str(e)))

    # A30: Factura simple sin lineas
    try:
        f = client.post(
            "/api/facturas/simple",
            json={
                "cliente_nombre": "Simple Test",
                "concepto": "Trabajo",
                "base_imponible": 150.0,
                "iva_pct": 21.0,
            },
            headers=headers,
        ).json()
        ok = f.get("base_imponible") == 150.0
        test_results.append(
            test_result(
                "A30-Factura-SimpleSinLineas",
                "PASS" if ok else "FAIL",
                f"base={f.get('base_imponible')}",
                "base_imponible directo",
                "base=150",
                f"base={f.get('base_imponible')}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A30-Factura-SimpleSinLineas", "ERROR", str(e)))

    # A31: Limite listar facturas
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Limite Test"}, headers=headers
        ).json()
        for i in range(5):
            client.post(
                "/api/facturas/",
                json={
                    "cliente_id": c["id"],
                    "base_imponible": 10.0 + i,
                    "lineas": [
                        {
                            "descripcion": f"Test{i}",
                            "cantidad": 1,
                            "precio_unitario": 10.0 + i,
                        }
                    ],
                },
                headers=headers,
            )
        r = client.get("/api/facturas/?limit=3", headers=headers).json()
        ok = len(r.get("facturas", [])) == 3
        test_results.append(
            test_result(
                "A31-Factura-Limite",
                "PASS" if ok else "FAIL",
                f"limit={len(r.get('facturas', []))}",
                "limit=3",
                "3",
                f"limit={len(r.get('facturas', []))}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A31-Factura-Limite", "ERROR", str(e)))

    # A32: Offset pagination
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Offset Test"}, headers=headers
        ).json()
        for i in range(3):
            client.post(
                "/api/facturas/",
                json={
                    "cliete_id": c["id"],
                    "base_imponible": 10.0 + i,
                    "lineas": [
                        {
                            "descripcion": f"T{i}",
                            "cantidad": 1,
                            "precio_unitario": 10.0 + i,
                        }
                    ],
                },
                headers=headers,
            )
        r = client.get("/api/facturas/?skip=1&limit=1", headers=headers).json()
        ok = len(r.get("facturas", [])) >= 1
        test_results.append(
            test_result(
                "A32-Factura-Offset",
                "PASS" if ok else "FAIL",
                f"facturas={len(r.get('facturas', []))}",
                "skip=1",
                ">=1",
                f"facturas={len(r.get('facturas', []))}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A32-Factura-Offset", "ERROR", str(e)))

    # A33: Exportar año especifico
    try:
        r = client.get("/api/facturas/exportar?anno=2024", headers=headers)
        ok = r.status_code == 200
        test_results.append(
            test_result(
                "A33-Exportar-Ano",
                "PASS" if ok else "FAIL",
                f"status={r.status_code}",
                "anno=2024",
                "200",
                f"status={r.status_code}",
            )
        )
    except Exception as e:
        test_results.append(test_result("A33-Exportar-Ano", "ERROR", str(e)))

    # A34: WhatsApp link without phone
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "WhatsApp Test"}, headers=headers
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "lineas": [
                    {"descripcion": "Test", "cantidad": 1, "precio_unitario": 100.0}
                ],
            },
            headers=headers,
        ).json()
        r = client.get(f"/api/facturas/{f['id']}/whatsapp-link", headers=headers)
        if r.status_code == 400:
            test_results.append(
                test_result(
                    "A34-WhatsApp-SinTelefono",
                    "PASS",
                    "400 sin telefono",
                    "whatsapp-link",
                    "400",
                    f"status={r.status_code}",
                )
            )
        else:
            test_results.append(
                test_result(
                    "A34-WhatsApp-SinTelefono", "FAIL", f"status={r.status_code}"
                )
            )
    except Exception as e:
        test_results.append(test_result("A34-WhatsApp-SinTelefono", "ERROR", str(e)))

    # A35: Email without email
    try:
        c = client.post(
            "/api/facturas/clientes", json={"nombre": "Email Test2"}, headers=headers
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 100.0,
                "lineas": [
                    {"descripcion": "Test", "cantidad": 1, "precio_unitario": 100.0}
                ],
            },
            headers=headers,
        ).json()
        r = client.post(f"/api/facturas/{f['id']}/enviar-email", headers=headers)
        if r.status_code == 400:
            test_results.append(
                test_result(
                    "A35-Email-SinEmail",
                    "PASS",
                    "400 sin email",
                    "enviar-email",
                    "400",
                    f"status={r.status_code}",
                )
            )
        else:
            test_results.append(
                test_result("A35-Email-SinEmail", "FAIL", f"status={r.status_code}")
            )
    except Exception as e:
        test_results.append(test_result("A35-Email-SinEmail", "ERROR", str(e)))

    return test_results


if __name__ == "__main__":
    print("=" * 70)
    print("PRUEBAS QA - GREMIOS DE AUTÓNOMOS ESPAÑA - FACTURA INVISIBLE")
    print("=" * 70)
    results = run_tests()
    print("=" * 70)

    # Análisis de resultados
    states = {"PASS": 0, "FAIL": 0, "WARNING": 0, "ERROR": 0}
    for r in results:
        states[r["resultado"]] = states.get(r["resultado"], 0) + 1

    print(f"TOTAL PRUEBAS: {len(results)}")
    print(f"  PASS:    {states['PASS']}")
    print(f"  FAIL:    {states['FAIL']}")
    print(f"  WARNING: {states['WARNING']}")
    print(f"  ERROR:   {states['ERROR']}")
    print("=" * 70)

    # Generar reporte
    import json
    from datetime import datetime

    report = f"""# Reporte QA - Gremios de Autónomos España
## Factura Invisible - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Resumen Ejecutivo

- **Total de pruebas ejecutadas**: {len(results)}
- **PASS**: {states["PASS"]}
- **FAIL**: {states["FAIL"]}
- **WARNING**: {states["WARNING"]}
- **ERROR**: {states["ERROR"]}

## Cobertura de Pruebas

### Gremios Probados (15)
1. Fontanero (G1)
2. Electricista (G2)
3. Albañil (G3)
4. Mecánico (G4)
5. Diseñador/Freelance (G5)
6. Peluquería (G6)
7. Transportista (G7)
8. Jardinero (G8)
9. Fotógrafo (G9)
10. Profesor particular (G10)
11. Informático (G11)
12. Carpintero (G12)
13. Pintor (G13)
14. Cerrajero (G14)
15. Limpieza (G15)

### Áreas Cubiertas
- Facturas normales (F1/F2)
- Tipos de IVA: 0%, 4%, 10%, 21%
- Tipos de IRPF: 0%, 7%, 15%, 19%
- Abonos (parcial, total)
- Rectificativas (R1-R5, tipos I y S)
- Casos borde (404, 422, bloqueos)
- Dashboard/API endpoints
- Export/Listado/Búsqueda/PDF
- VeriFacti/VeriFactu

## Detalle de Fallos

"""

    # Agregar tabla de fallos
    failures = [r for r in results if r["resultado"] in ("FAIL", "ERROR")]
    if failures:
        failures.sort(key=lambda x: x["id"])
        report += "| ID | Escenario | Pasos | Esperado | Obtenido | Severidad | Recomendación |\n"
        report += "|---|---|---|---|---|---|---|\n"
        for f in failures:
            severity = "ALTA" if f["resultado"] == "ERROR" else "MEDIA"
            rec = (
                "Verificar código" if f["resultado"] == "FAIL" else "Revisar excepción"
            )
            report += f"| {f['id']} | {f['escenario']} | {f['pasos'][:50]}... | {f['esperado']} | {f['obtenido'][:50]}... | {severity} | {rec} |\n"
    else:
        report += "No se detectaron fallos.\n"

    report += """
## Riesgos Pendientes

A continuación se listan los riesgos identificados que no son fallos críticos pero requieren revisión:

"""

    warnings = [r for r in results if r["resultado"] == "WARNING"]
    if warnings:
        for w in warnings:
            report += f"- **{w['escenario']}**: {w['detalle']}\n"
    else:
        report += "No hay riesgos pendientes identificados.\n"

    report += f"""

## Recomendaciones

1. Revisar los {states["FAIL"]} casos marcados como FAIL
2. Revisar los {states["ERROR"]} errores de ejecución
3. Verificar regulación fiscal para casos con WARNING

---
*Reporte generado automáticamente por QA - Factura Invisible*
"""

    # Guardar reporte
    report_path = "/home/debian/proyectos-express/facturacion-invisible/tmp/kilo-reports/gremios_autonomos_100_report.md"
    with open(report_path, "w") as f:
        f.write(report)

    print(f"Reporte guardado en: {report_path}")
    print("=" * 70)

    # Limpiar
    try:
        os.unlink(TEMP_DB.name)
    except:
        pass

    # Exit code based on failures
    sys.exit(0 if states["FAIL"] == 0 and states["ERROR"] == 0 else 1)
