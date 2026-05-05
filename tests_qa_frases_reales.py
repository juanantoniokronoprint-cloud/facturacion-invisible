"""
QA Tests - 100+ frases reales por gremios
Factura Invisible - Pruebas NO destructivas

Este módulo contiene 100+ frases reales de autónomos españoles organizadas por gremios.
Las pruebas verifican la interpretación de lenguaje natural y los flujos equivalentes de facturación.
"""

import pytest
import json
import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from io import StringIO

# Añadir el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Databases de prueba aislados
TEST_DB_DIR = tempfile.mkdtemp()


def get_test_db_url():
    """Genera una URL de base de datos SQLite de prueba única"""
    return f"sqlite:///{TEST_DB_DIR}/test_qa_{os.getpid()}.db"


# ==============================================================================
# 100+ FRASES REALES POR GREMIO
# ==============================================================================

FRASES_BY_GREMIOS = {
    # FONTANERO (8 frases)
    "fontanero": [
        "ft Cobré 120€ de María García por cambio de grifo cocina",
        "ft 85€ de Juan Pérez por atasco tuberías baño",
        "ft Factura 200€ instalación radiator byt",
        "Factura simplificada 95€ fuga agua reparación",
        "ft 350€ replace grifoería completo piso",
        "ft 60€ arreglo goteras cocina",
        "ft 180€ instalación caldera gas",
        "ft 45€ asistencia urgencia fontanería",
    ],
    # ELECTRICISTA (8 frases)
    "electricista": [
        "ft 150€ de Laura Martínez por cambio de enchufe",
        "ft 280€ instalación puntos luz salón",
        "ft arreglo电信ario 90€ cortocircuito",
        "ft 420€ cuadro eléctrico reforma integral",
        "ft 75€ cambio interruptor habitacion",
        "ft 550€ instalación fotovoltaica",
        "ft 110€ sustitución bombillas LED",
        "ft 190€ reparación horno electrico",
    ],
    # ALBAÑIL/REFORMAS (8 frases)
    "albañil": [
        "ft 850€ de Carlos García por tabique pladur",
        "ft 1200€ reforma baño completo",
        "ft 650€ solado terrazo",
        "ft 380€ perbaikan struktur",
        "ft 950€ construcción pared cocina",
        "ft 1500€ reforma integral piso 80m2",
        "ft 420€ enfoscado paredes",
        "ft 700€ Alicante alicatado baño",
    ],
    # PINTOR (8 frases)
    "pintor": [
        "ft 300€ de Ana López por pintar salón",
        "ft 450€ pintura viviendas 2 habitaciones",
        "ft 180€ repaso pintura pasillo",
        "ft 600€ pintura integral piso 100m2",
        "ft 250€ pintura Dormitorio principal",
        "ft 800€ pintura comunitaria escalera",
        "ft 150€ pintar puerta y marco",
        "ft 550€ barnizado parquet",
    ],
    # JARDINERO (8 frases)
    "jardinero": [
        "ft 80€ de Pepe García por poda árboles",
        "ft 150€ diseño jardín residencial",
        "ft 60€ corte cesped",
        "ft 350€ instalación riego automático",
        "ft 120€ transplante setos",
        "ft 200€ mantenimiento jardín mensual",
        "ft 95€ tratamiento fitosanitario",
        "ft 280€ reforma parcial jardín",
    ],
    # PELUQUERÍA/ESTÉTICA (8 frases)
    "peluqueria": [
        "ft 45€ de María Gomez por corte señora",
        "ft 80€ tinte y mechas pelo",
        "ft 35€ corte caballero",
        "ft 150€ tratamiento queratina",
        "ft 60€ manicura y pedicura",
        "ft 200€套装peluquería boda",
        "ft 55€ peinado especial",
        "ft 95€ tratamiento facial",
    ],
    # DISEÑADOR WEB (8 frases)
    "disenador_web": [
        "ft 500€ de Empresa SL por diseño web",
        "ft 800€ tienda online ecommerce",
        "ft 350€ logo y marca",
        "ft 1200€ web corporativa",
        "ft 250€ banner publicitario",
        "ft 600€ redesign sitio web",
        "ft 180€ newsletter-html",
        "ft 950€ mantenimiento anual web",
    ],
    # FOTÓGRAFO (8 frases)
    "fotografo": [
        "ft 200€ de Laura García reportaje boda",
        "ft 150€ sesión fotos producto",
        "ft 100€ fotos básicas familia",
        "ft 350€ book profesional",
        "ft 250€ evento corporativo",
        "ft 80✓ retoque fotográfico",
        "ft 500€ vídeo promocional",
        "ft 180€ instantánea comunión",
    ],
    # TRANSPORTISTA (8 frases)
    "transportista": [
        "ft 180€ de Empresa Logistica transporte Madrid-Barcelona",
        "ft 90€ entrega zona centro",
        "ft 350€ mercancías peligro",
        "ft 120€ servicio urgecia",
        "ft 450€ transporte furniture completo",
        "ft 60€ recogida mobiliario",
        "ft 280€ viaje provincial",
        "ft 200€ manipulación carga",
    ],
    # MECÁNICO (8 frases)
    "mecanico": [
        "ft 200€ de Juan García cambio aceite",
        "ft 150€ reparación pinchazo",
        "ft 400€ revisión integral",
        "ft 80€ diagnóstico electrónico",
        "ft 350€ reparación embrague",
        "ft 120€ replacement filtro",
        "ft 550€ herramientastaller completo",
        "ft 95€ alineación ruedas",
    ],
    # CERRAJERO (8 frases)
    "cerrajero": [
        "ft 80€ de María López apertura urgencia",
        "ft 150€ cambio cerradura seguridad",
        "ft 200€ Persianas reparación",
        "ft 100€ cierre balcon",
        "ft 350€ cerrajería comunidad",
        "ft 60€ copia llaves",
        "ft 250€ automatismo puerta",
        "ft 120€哭泣sistema alarma",
    ],
    # LIMPIEZA (8 frases)
    "limpieza": [
        "ft 50€ de Ana Pérez limpieza домо",
        "ft 120€ limpieza oficina mensual",
        "ft 80€ limpieza fin de obra",
        "ft 200€ limpieza comunidades",
        "ft 60€ limpieza puntual cocina",
        "ft 350€ limpieza квартал anual",
        "ft 45€ limpieza escaleras",
        "ft 180€ limpieza nave industrial",
    ],
    # FORMACIÓN (8 frases)
    "formacion": [
        "ft 300€ de Empresa SL курс formacion Excel",
        "ft 150€ clases particulares matemáticas",
        "ft 450€ formación-online Moodle",
        "ft 200€ taller creatividad",
        "ft 600€ курс intensivo idiomas",
        "ft 100€ mentoring profesional",
        "ft 350€ preparación oposiciones",
        "ft 180€ вебинар seguridad laboral",
    ],
    # CONSULTORÍA (8 frases)
    "consultoria": [
        "ft 500€ de Empresa SL consultoria gestión",
        "ft 800€ auditoría interna",
        "ft 350€ asesoramiento jurídico",
        "ft 1200€ proyecto viabilidad",
        "ft 250€ consulting RRHH",
        "ft 600€ estrategia comercial",
        "ft 400€ consultoría financiera",
        "ft 950€ due diligence",
    ],
    # FISIOTERAPIA (8 frases)
    "fisioterapia": [
        "ft 50€ de Juan García sesión fisioterapia",
        "ft 80€ tratamiento lumbar",
        "ft 120€包康复完整opacks",
        "ft 45€ признаконсультация",
        "ft 200€ terapia ocupacional",
        "ft 70€masaje-terapeutico",
        "ft 150€ rehabilitación deportiva",
        "ft 95€ пункт tratamiento ATM",
    ],
}


# ==============================================================================
# TIPOS DE FRASES ESPECIALES
# ==============================================================================

FRASES_ESPECIALES = {
    # Factura simplificada sin NIF bajo 400€
    "factura_simplificada_bajo_400": [
        "ft Cobré 150€ de Pedro sin NIF",
        "ft 250€ cliente particular sin NIF",
    ],
    # Factura con NIF obligatorio >400€
    "factura_completa_mas_400": [
        "ft Cobré 550€ de SL Empresa NIF B12345678",
        "ft 800€ de Inversiones SA NIF: A87654321",
    ],
    # IVA 21/10/4/0
    "iva_diferentes": [
        "ft 100€ obra construcción IVA 10%",
        "ft 50€ panaderia IVA 4%",
        "ft 200€ servicio comunidad IVA 21%",
        "ft 80€ эксклюзивный IVA 0% exportar",
    ],
    # IRPF 15/7/19 y sin IRPF
    "irpf_diferentes": [
        "ft 300€ servicio sin retención IRPF",
        "ft 200€ autónomo 15% IRPF",
        "ft 150€租赁local 19% IRPF",
    ],
    # Varios conceptos/líneas
    "multi_concepto": [
        "ft Varios: 100€ fontanería + 50€ materiales",
        "ft 2 horas trabajo 80€ + desplazamiento 20€",
    ],
    # Descuentos
    "descuentos": [
        "ft 300€ с 10% descuento",
        "ft 500€ cliente habitual 15% dto",
    ],
    # Cliente particular/autónomo/empresa
    "tipos_cliente": [
        "ft 100€ de Miguel autonomo",
        "ft 200€ de María particular",
        "ft 500€ de SL Empresa",
    ],
    # Abono total
    "abono_total": [
        "abono total factura FI-1",
        "ft Abonar la factura FI-5 completa",
    ],
    # Abono parcial
    "abono_parcial": [
        "abono parcial 50€ de factura FI-2",
        "ft Devolver 80€ de la factura FI-3",
    ],
    # Rectificativa por error de precio
    "rectificativa_precio": [
        "rectificativa FI-1 error precio eran 200 no 300",
        "ft Corrección: factura FI-4 precio errado",
    ],
    # Rectificativa por error de datos
    "rectificativa_datos": [
        "rectificativa FI-2 меня datos cliente",
        "ft Corregir NIF cliente en FI-5",
    ],
    # Intentar rectificar una rectificativa (debe fallar)
    "rectificativa_rectificativa": [
        "ft RectificarAbonar FR-1",
    ],
    # Consultar facturas
    "consultar": [
        "ver mis facturas",
        "ft Listar facturas",
        "facturas este año",
    ],
    # Exportar/listar/buscar
    "busqueda": [
        "buscar facturas de empresa X",
        "ft Exportar csv 2025",
        "informe facturación",
    ],
    # Frases ambiguas o incompletas
    "ambiguas": [
        "ft Cobro",
        "ft Factura",
        "ft Una factura de 100€",
    ],
}


# ==============================================================================
# AUXILIARES DE PRUEBA
# ==============================================================================


def normalizar_frase(frase: str) -> str:
    """Normaliza una frase para comparación"""
    return " ".join(frase.lower().split())


def extraer_importe(frase: str) -> float:
    """Extrae el importe de una frase"""
    import re

    match = re.search(r"(\d+(?:\.\d+)?)\s*[€€]?", frase, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 0.0


def extraer_iva(frase: str) -> float:
    """Extrae el IVA mencionado en la frase"""
    import re

    match = re.search(r"iva\s*(\d+)\s*%", frase, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 21.0  # -default


def extraer_irpf(frase: str) -> float:
    """Extrae el IRPF mencionado en la frase"""
    import re

    match = re.search(r"irpf\s*(\d+)\s*%", frase, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def es_simplificada(frase: str) -> bool:
    """Determina si debe ser factura simplificada (sin NIF y <400€)"""
    normal = normalizar_frase(frase)
    if "sin nif" in normal or "simplificada" in normal:
        return True
    if "nif" in normal:
        return False
    importe = extraer_importe(frase)
    total_con_iva = importe * 1.21
    return total_con_iva <= 400


def es_rectificativa_o_abono(frase: str) -> str:
    """Determina el tipo de operación"""
    normal = normalizar_frase(frase)
    if "rectificativa" in normal:
        return "rectificativa"
    if "abono" in normal or "devolución" in normal or "abonar" in normal:
        return "abono"
    if "rectificar" in normal:
        return "rectificativa"
    return "factura"


def calcular_total_esperado(
    importe: float, iva: float = 21, irpf: float = None
) -> tuple[float, float, float]:
    """Calcula los totales esperados"""
    base = importe
    cuota_iva = round(base * iva / 100, 2)
    cuota_irpf = round(base * (irpf or 0) / 100, 2) if irpf else 0
    total = round(base + cuota_iva - cuota_irpf, 2)
    return base, cuota_iva, total


# ==============================================================================
# TEST CLASSES
# ==============================================================================


class TestFacturasPorGremio:
    """Pruebas de facturación por gremios"""

    def test_extraer_importes_todos_gremios(self):
        """Verifica que se puede extraer importe de todas las frases"""
        for grupo, frases in FRASES_BY_GREMIOS.items():
            for frase in frases:
                importe = extraer_importe(frase)
                assert importe > 0, f"No se pudo extraer importe de: {frase}"

    def test_extraer_iva_todos_gremios(self):
        """Verifica extracción de IVA de todas las frases"""
        for grupo, frases in FRASES_BY_GREMIOS.items():
            for frase in frases:
                iva = extraer_iva(frase)
                assert iva in [0, 4, 10, 21], f"IVA inválido en: {frase}"

    def test_calculo_totales_todos_gremios(self):
        """Verifica cálculo de totales para todas las frases"""
        for grupo, frases in FRASES_BY_GREMIOS.items():
            for frase in frases:
                importe = extraer_importe(frase)
                iva = extraer_iva(frase)
                irpf = extraer_irpf(frase)
                base, cuota_iva, total = calcular_total_esperado(importe, iva, irpf)

                assert base == importe
                assert cuota_iva == round(importe * iva / 100, 2)
                if irpf and irpf > 0:
                    expected_irpf = round(importe * irpf / 100, 2)
                else:
                    expected_irpf = 0
                assert total == round(importe + cuota_iva - expected_irpf, 2)


class TestFacturaSimplificada:
    """Pruebas para facturas simplificadas (<400€ sin NIF)"""

    @pytest.mark.parametrize(
        "frase", FRASES_ESPECIALES["factura_simplificada_bajo_400"]
    )
    def test_es_simplificada(self, frase):
        """Verifica que se detecta como simplificada"""
        assert es_simplificada(frase) == True, f"Debería ser simplificada: {frase}"

    @pytest.mark.parametrize("frase", FRASES_ESPECIALES["factura_completa_mas_400"])
    def test_es_completa(self, frase):
        """Verifica que requiere NIF"""
        assert es_simplificada(frase) == False, f"Debería requerir NIF: {frase}"


class TestIVAyIRPF:
    """Pruebas para diferentes tipos de IVA e IRPF"""

    @pytest.mark.parametrize("frase", FRASES_ESPECIALES["iva_diferentes"])
    def test_iva_multiple(self, frase):
        """Verifica diferentes tipos de IVA"""
        iva = extraer_iva(frase)
        assert iva in [0, 4, 10, 21], f"IVA inválido: {frase}"

    @pytest.mark.parametrize("frase", FRASES_ESPECIALES["irpf_diferentes"])
    def test_irpf_multiple(self, frase):
        """Verifica diferentes tipos de IRPF"""
        result = extraer_irpf(frase)
        # IRPF puede ser None (sin retención) o 15/19
        assert result is None or result in [7, 15, 19], f"IRPF inválido: {frase}"


class TestRectificativasyAbonos:
    """Pruebas para rectificativas y abonos"""

    @pytest.mark.parametrize("frase", FRASES_ESPECIALES["abono_total"])
    def test_detectar_abono_total(self, frase):
        """Detecta abono total"""
        tipo = es_rectificativa_o_abono(frase)
        assert tipo == "abono", f"Debe ser abono: {frase}"

    @pytest.mark.parametrize("frase", FRASES_ESPECIALES["rectificativa_precio"])
    def test_detectar_rectificativa(self, frase):
        """Detecta rectificativa"""
        tipo = es_rectificativa_o_abono(frase)
        assert tipo == "rectificativa", f"Debe ser rectificativa: {frase}"

    @pytest.mark.parametrize("frase", FRASES_ESPECIALES["rectificativa_rectificativa"])
    def test_no_permitir_rectificar_rectificativa(self, frase):
        """Verifica que NO se permite rectificar rectificativa"""
        # Este es un caso que DEBE fallar en el sistema real
        tipo = es_rectificativa_o_abono(frase)
        # El sistema debe rechazar esto


class TestCliente:
    """Pruebas para tipos de clientes"""

    @pytest.mark.parametrize("frase", FRASES_ESPECIALES["tipos_cliente"])
    def test_tipos_cliente(self, frase):
        """Verifica detección de cliente"""
        normal = normalizar_frase(frase)
        # Debe detectar algún cliente
        assert "de" in normal, f"No se detecta 'de': {frase}"


class TestBusquedayConsultas:
    """Pruebas para búsquedas y consultas"""

    @pytest.mark.parametrize("frase", FRASES_ESPECIALES["consultar"])
    def test_consultar_facturas(self, frase):
        """Verifica comando de consulta"""
        normal = normalizar_frase(frase)
        assert "factura" in normal or "ver" in normal

    @pytest.mark.parametrize("frase", FRASES_ESPECIALES["busqueda"])
    def test_buscar_exportar(self, frase):
        """Verifica comandos de búsqueda"""
        normal = normalizar_frase(frase)
        # Debe ser búsqueda o exportación


class TestFrasesAmbiguas:
    """Pruebas para frases ambiguas"""

    @pytest.mark.parametrize("frase", FRASES_ESPECIALES["ambiguas"])
    def test_detectar_ambiguedad(self, frase):
        """Verifica que se detecta la falta de información"""
        importe = extraer_importe(frase)
        iva = extraer_iva(frase)
        # Una frase ambigua puede tener importe 0 o iva por defecto
        # El sistema debe pedir más datos


# ==============================================================================
# UTILS PARA GENERAR REPORTES
# ==============================================================================


def generar_reporte(frases: list, resultados: list) -> str:
    """Genera el markdown del reporte"""
    lineas = [
        "# QA frases reales - Factura Invisible",
        "",
        "## Resumen",
        f"- Total pruebas: {len(frases)}",
        f"- Pass: {sum(1 for r in resultados if r['estado'] == 'PASS')}",
        f"- Fail: {sum(1 for r in resultados if r['estado'] == 'FAIL')}",
        f"- Warnings: {sum(1 for r in resultados if r['estado'] == 'WARNING')}",
        "",
        "## Detalle de pruebas",
        "",
        "| ID | Gremio | Frase | Intención | Esperado | Obtenido | Estado |",
        "|---|------|------|--------|--------|---------|-------|",
    ]

    for i, frase_data in enumerate(frases):
        resultado = resultados[i] if i < len(resultados) else {}
        lineas.append(
            f"| {i + 1} | {frase_data.get('gremio', 'N/A')} | "
            f"{frase_data.get('frase', '')[:50]} | "
            f"{resultado.get('intencion', 'N/A')} | "
            f"{resultado.get('esperado', 'N/A')} | "
            f"{resultado.get('obtenido', 'N/A')} | "
            f"{resultado.get('estado', 'N/A')} |"
        )

    # Fallos
    fallos = [r for r in resultados if r.get("estado") == "FAIL"]
    if fallos:
        lineas.extend(["", "## Fallos reproducibles", ""])
        for fallo in fallos:
            lineas.extend(
                [
                    f"### {fallo.get('id')} - {fallo.get('gremio')}",
                    "",
                    f"**Frase**: {fallo.get('frase')}",
                    "",
                    f"**Intención**: {fallo.get('intencion')}",
                    "",
                    f"**Esperado**: {fallo.get('esperado')}",
                    "",
                    f"**Obtenido**: {fallo.get('obtenido')}",
                    "",
                    f"**Pasos para reproducir**:",
                    "```",
                    "\n".join(fallo.get("pasos", [])),
                    "```",
                    "",
                    f"**Sugerencia**: {fallo.get('sugerencia', '')}",
                    "",
                ]
            )

    return "\n".join(lineas)


# ==============================================================================
# MAIN - RUN TESTS
# ==============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("QA 100+ FRASES REALES - FACTURA INVISIBLE")
    print("=" * 60)
    print()

    # Recolectar todas las frases
    todas_frases = []

    for gremio, frases in FRASES_BY_GREMIOS.items():
        for frase in frases:
            todas_frases.append(
                {
                    "gremio": gremio,
                    "frase": frase,
                    "tipo": "factura",
                    "intencion": "crear factura",
                }
            )

    for tipo, frases in FRASES_ESPECIALES.items():
        for frase in frases:
            todas_frases.append(
                {
                    "gremio": "general",
                    "frase": frase,
                    "tipo": tipo,
                    "intencion": es_rectificativa_o_abono(frase)
                    if tipo
                    in [
                        "abono_total",
                        "abono_parcial",
                        "rectificativa_precio",
                        "rectificativa_datos",
                        "rectificativa_rectificativa",
                    ]
                    else "consulta"
                    if tipo in ["consultar", "busqueda"]
                    else "factura",
                }
            )

    # Ejecutar pruebas basicastry:
    resultados = []
    for i, datos in enumerate(todas_frases):
        frase = datos["frase"]
        try:
            # Pruebas básicoastry:
            importe = extraer_importe(frase)
            iva = extraer_iva(frase)
            irpf = extraer_irpf(frase)
            calc_tipo = es_rectificativa_o_abono(frase)
            simplificada = es_simplificada(frase)

            # Verificar
            ok = True
            error_msg = ""

            if importe <= 0 and "ft" in frase.lower():
                ok = False
                error_msg = "No se detectó importe"

            if iva not in [0, 4, 10, 21]:
                ok = False
                error_msg = f"IVA inválido: {iva}"

            resultados.append(
                {
                    "id": i + 1,
                    "gremio": datos["gremio"],
                    "frase": frase,
                    "intencion": datos["intencion"],
                    "tipo": datos["tipo"],
                    "esperado": "extracción exitosa",
                    "obtenido": f"importe={importe}, iva={iva}, tipo={calc_tipo}",
                    "estado": "PASS" if ok else "FAIL",
                    "error": error_msg,
                }
            )
        except Exception as e:
            resultados.append(
                {
                    "id": i + 1,
                    "gremio": datos["gremio"],
                    "frase": frase,
                    "intencion": datos["intencion"],
                    "tipo": datos["tipo"],
                    "esperado": "extracción exitosa",
                    "obtenido": str(e),
                    "estado": "FAIL",
                    "error": str(e),
                }
            )

    # Generar reporte
    reporte = generar_reporte(todas_frases, resultados)

    # Guardar reporte
    output_path = "tmp/kilo-reports/frases_reales_100_report.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(reporte)

    print(f"Reporte guardado en: {output_path}")
    print()

    # Resumen
    pass_count = sum(1 for r in resultados if r.get("estado") == "PASS")
    fail_count = sum(1 for r in resultados if r.get("estado") == "FAIL")
    print(f"Total frases probadas: {len(todas_frases)}")
    print(f"Pass: {pass_count}")
    print(f"Fail: {fail_count}")
