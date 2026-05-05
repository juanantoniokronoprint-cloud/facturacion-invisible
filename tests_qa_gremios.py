#!/usr/bin/env python3
"""
Script de pruebas QA para Gremios de Autónomos en España
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_gremios.db"
os.environ["API_KEY"] = "testkey"
os.environ["ENVIRONMENT"] = "dev"

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
headers = {"X-API-Key": "testkey"}


def test_result(name, status, detalle):
    print(f"[{status}] {name}: {detalle}")
    return {"escenario": name, "resultado": status, "detalle": detalle}


def run_tests():
    results = []

    # G1: Fontanero - Factura normal
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "12345678A", "nombre": "Cliente Test"},
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
                        "descripcion": "Reparación",
                        "cantidad": 1,
                        "precio_unitario": 150.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f.get("iva_cuota") == 31.50 and f.get("total") == 181.50
        results.append(
            test_result(
                "G1-Fontanero-FacturaNormal",
                "PASS" if ok else "FAIL",
                f"IVA={f.get('iva_cuota')}, Total={f.get('total')}",
            )
        )
    except Exception as e:
        results.append(test_result("G1-Fontanero-FacturaNormal", "ERROR", str(e)))

    # G1: Fontanero - Abono parcial
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "12345678A", "nombre": "Cliente Test"},
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
                        "descripcion": "Reparación",
                        "cantidad": 1,
                        "precio_unitario": 150.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        r = client.post(
            f"/api/facturas/{f['id']}/abono",
            json={"base_imponible": 50.0, "concepto": "Abono", "motivo": "Devolución"},
            headers=headers,
        ).json()["factura"]
        ok = (
            r["base_imponible"] == -50.0
            and r["iva_cuota"] == -10.50
            and r["serie"] == "AB"
        )
        results.append(
            test_result(
                "G1-Fontanero-AbonoParcial",
                "PASS" if ok else "FAIL",
                f"Base={r.get('base_imponible')}, serie={r.get('serie')}",
            )
        )
    except Exception as e:
        results.append(test_result("G1-Fontanero-AbonoParcial", "ERROR", str(e)))

    # G1: Fontanero - Rectificativa
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "12345678A", "nombre": "Cliente Test"},
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
            f"/api/facturas/{f['id']}/rectificativa",
            json={
                "tipo_factura": "R1",
                "tipo_rectificacion": "I",
                "base_imponible": -50.0,
                "concepto": "Rectif",
                "motivo": "Error",
            },
            headers=headers,
        ).json()["factura"]
        ok = r["tipo_factura"] == "R1" and r.get("factura_origen_id") == f["id"]
        results.append(
            test_result(
                "G1-Fontanero-Rectificativa",
                "PASS" if ok else "FAIL",
                f"tipo={r.get('tipo_factura')}",
            )
        )
    except Exception as e:
        results.append(test_result("G1-Fontanero-Rectificativa", "ERROR", str(e)))

    # G2: Electricista - Factura >400€ sin NIF
    try:
        f = client.post(
            "/api/facturas/simple",
            json={
                "cliente_nombre": "Cliente Sin NIF",
                "concepto": "Instalación",
                "base_imponible": 500.0,
                "iva_pct": 21.0,
                "cliente_nif": None,
            },
            headers=headers,
        ).json()
        total = f.get("total", 0)
        tipo = f.get("tipo_factura", "")
        # Según AEAT: factura simplificada (F2) solo si <=400€ CON IVA O sin NIF pero en la práctica se debe exigir NIF para >400€
        if total > 400 and tipo == "F2":
            results.append(
                test_result(
                    "G2-Electricista-SinNIF",
                    "FAIL",
                    f"Total={total}, tipo={tipo} - debe requerir NIF para >400€",
                )
            )
        else:
            results.append(
                test_result(
                    "G2-Electricista-SinNIF",
                    "WARNING",
                    f"Total={total}, tipo={tipo} - verificar regulación",
                )
            )
    except Exception as e:
        results.append(test_result("G2-Electricista-SinNIF", "ERROR", str(e)))

    # G3: Albañil - Cliente empresa con NIF
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "B12345678", "nombre": "Construcciones García SL"},
            headers=headers,
        ).json()
        f = client.post(
            "/api/facturas/",
            json={
                "cliente_id": c["id"],
                "base_imponible": 2500.0,
                "iva_pct": 21.0,
                "lineas": [
                    {
                        "descripcion": "Trabajos",
                        "cantidad": 1,
                        "precio_unitario": 2500.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = f["tipo_factura"] == "F1" and f["iva_pct"] == 21.0
        # Actualizar estado
        client.patch(f"/api/facturas/{f['id']}/estado?estado=pagada", headers=headers)
        f2 = client.get(f"/api/facturas/{f['id']}", headers=headers).json()
        ok2 = f2["estado"] == "pagada"
        results.append(
            test_result(
                "G3-Albanil-EmpresaNIF",
                "PASS" if (ok and ok2) else "FAIL",
                f"tipo={f.get('tipo_factura')}, estado={f2.get('estado')}",
            )
        )
    except Exception as e:
        results.append(test_result("G3-Albanil-EmpresaNIF", "ERROR", str(e)))

    # G4: Mecánico - Abono total
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "12345678A", "nombre": "Cliente Test"},
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
                        "descripcion": "Reparación",
                        "cantidad": 1,
                        "precio_unitario": 300.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        r = client.post(
            f"/api/facturas/{f['id']}/abono",
            json={
                "base_imponible": 300.0,
                "concepto": "Abono",
                "motivo": "Abono total",
            },
            headers=headers,
        ).json()["factura"]
        ok = (
            r["base_imponible"] == -300.0
            and r["iva_cuota"] == -63.0
            and r["serie"] == "AB"
        )
        results.append(
            test_result(
                "G4-Mecanico-AbonoTotal",
                "PASS" if ok else "FAIL",
                f"Base={r.get('base_imponible')}, iva={r.get('iva_cuota')}",
            )
        )
    except Exception as e:
        results.append(test_result("G4-Mecanico-AbonoTotal", "ERROR", str(e)))

    # G5: Diseñador - IRPF 15%
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "B87654321", "nombre": "Empresa Diseño SL"},
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
                        "descripcion": "Diseño",
                        "cantidad": 1,
                        "precio_unitario": 1000.0,
                        "iva_pct": 21.0,
                    }
                ],
            },
            headers=headers,
        ).json()
        ok = (
            f.get("irpf_pct") == 15.0
            and f.get("irpf_cuota") == 150.0
            and f.get("total") == 1060.0
        )
        results.append(
            test_result(
                "G5-Diseñador-IRPF15",
                "PASS" if ok else "FAIL",
                f"IRPF={f.get('irpf_cuota')}, total={f.get('total')}",
            )
        )
    except Exception as e:
        results.append(test_result("G5-Diseñador-IRPF15", "ERROR", str(e)))

    # G5: Diseñador - Rectificativa
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "B87654321", "nombre": "Empresa Diseño SL"},
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
                        "descripcion": "Diseño",
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
                "motivo": "Descuento",
            },
            headers=headers,
        ).json()["factura"]
        ok = r["tipo_factura"] == "R1" and r.get("factura_origen_id") == f["id"]
        results.append(
            test_result(
                "G5-Diseñador-Rectificativa",
                "PASS" if ok else "FAIL",
                f"tipo={r.get('tipo_factura')}",
            )
        )
    except Exception as e:
        results.append(test_result("G5-Diseñador-Rectificativa", "ERROR", str(e)))

    # G6: Peluquería - Factura simplificada
    try:
        f = client.post(
            "/api/facturas/simple",
            json={
                "cliente_nombre": "María López",
                "concepto": "Corte pelo",
                "base_imponible": 25.0,
                "iva_pct": 21.0,
            },
            headers=headers,
        ).json()
        ok = f.get("tipo_factura") == "F2" and f.get("total") == 30.25
        results.append(
            test_result(
                "G6-Peluqueria-Simplificada",
                "PASS" if ok else "FAIL",
                f"tipo={f.get('tipo_factura')}, total={f.get('total')}",
            )
        )
    except Exception as e:
        results.append(test_result("G6-Peluqueria-Simplificada", "ERROR", str(e)))

    # G7: Transportista - Búsqueda y exportación
    try:
        c1 = client.post(
            "/api/facturas/clientes", json={"nombre": "Cliente1"}, headers=headers
        ).json()
        c2 = client.post(
            "/api/facturas/clientes", json={"nombre": "Cliente2"}, headers=headers
        ).json()
        client.post(
            "/api/facturas/",
            json={
                "cliente_id": c1["id"],
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
        client.post(
            "/api/facturas/",
            json={
                "cliente_id": c2["id"],
                "base_imponible": 200.0,
                "lineas": [
                    {
                        "descripcion": "Transporte",
                        "cantidad": 1,
                        "precio_unitario": 200.0,
                    }
                ],
            },
            headers=headers,
        )
        # Search
        sr = client.get("/api/facturas/?buscar=Cliente1", headers=headers).json()
        # Export
        er = client.get("/api/facturas/exportar?formato=csv", headers=headers)
        ok = len(sr.get("facturas", [])) == 1 and er.status_code == 200
        results.append(
            test_result(
                "G7-Transportista-Exportar",
                "PASS" if ok else "FAIL",
                f"busqueda={len(sr.get('facturas', []))}, csv={er.status_code}",
            )
        )
    except Exception as e:
        results.append(test_result("G7-Transportista-Exportar", "ERROR", str(e)))

    # G8: Caso borde - Rectificar rectificativa (debe fallar)
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "12345678A", "nombre": "Cliente Test"},
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
        r1 = client.post(
            f"/api/facturas/{f['id']}/rectificativa",
            json={
                "tipo_factura": "R1",
                "tipo_rectificacion": "I",
                "base_imponible": -20.0,
                "concepto": "R1",
                "motivo": "Error1",
            },
            headers=headers,
        ).json()["factura"]
        r2 = client.post(
            f"/api/facturas/{r1['id']}/rectificativa",
            json={
                "tipo_factura": "R1",
                "tipo_rectificacion": "I",
                "base_imponible": -10.0,
                "concepto": "R2",
                "motivo": "Error2",
            },
            headers=headers,
        )
        if r2.status_code == 400:
            results.append(
                test_result(
                    "G8-Borde-RectificarRectif", "PASS", "Bloqueado correctamente"
                )
            )
        else:
            results.append(
                test_result(
                    "G8-Borde-RectificarRectif",
                    "FAIL",
                    f"No se bloquea (status={r2.status_code})",
                )
            )
    except Exception as e:
        results.append(test_result("G8-Borde-RectificarRectif", "ERROR", str(e)))

    # G8: Caso borde - Rectificar abono (debe fallar)
    try:
        c = client.post(
            "/api/facturas/clientes",
            json={"nif": "12345678A", "nombre": "Cliente Test"},
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
        ab = client.post(
            f"/api/facturas/{f['id']}/abono",
            json={"base_imponible": 50.0, "concepto": "Abono", "motivo": "Abono"},
            headers=headers,
        ).json()["factura"]
        r = client.post(
            f"/api/facturas/{ab['id']}/rectificativa",
            json={
                "tipo_factura": "R1",
                "tipo_rectificacion": "I",
                "base_imponible": -10.0,
                "concepto": "R",
                "motivo": "Error",
            },
            headers=headers,
        )
        if r.status_code == 400:
            results.append(
                test_result(
                    "G8-Borde-RectificarAbono", "PASS", "Bloqueado correctamente"
                )
            )
        else:
            results.append(
                test_result(
                    "G8-Borde-RectificarAbono",
                    "FAIL",
                    f"No se bloquea (status={r.status_code})",
                )
            )
    except Exception as e:
        results.append(test_result("G8-Borde-RectificarAbono", "ERROR", str(e)))

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("PRUEBAS QA - GREMIOS DE AUTÓNOMOS ESPAÑA")
    print("=" * 60)
    results = run_tests()
    print("=" * 60)
    estados = {}
    for r in results:
        estados[r["resultado"]] = estados.get(r["resultado"], 0) + 1
    print(f"Total: {len(results)} pruebas - {estados}")
    print("=" * 60)
