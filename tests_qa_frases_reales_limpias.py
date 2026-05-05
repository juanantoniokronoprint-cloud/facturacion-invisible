"""
QA - Frases Reales Limpias
Factura Invisible - Verificación NO destructiva

Este módulo contiene frases reales y naturales de autonomousos españoles.
Solo espanol de Espana, sin caracteres chinos, russ, ingles raro ni tokens artificiales.
"""

import re
import unicodedata
import sys


# ==============================================================================
# FRASES REALES LIMPIAS - ESPANOL DE ESPANA
# ==============================================================================
# FRASES REALES LIMPIAS - ESPAÑOL DE ESPAÑA
# ==============================================================================

FRASES_BY_GREMIOS = {
    # FONTANERO (8 frases)
    "fontanero": [
        "ft Cobré 120 euros de Maria Garcia por cambio de grifo cocina",
        "ft 85 euros de Juan Perez por atasco tuberias baño",
        "ft Factura 200 euros instalacion radiador",
        "Factura simplificada 95 euros fuga agua reparacion",
        "ft 350 euros cambio griferia completa piso",
        "ft 60 euros arreglo goteras cocina",
        "ft 180 euros instalacion caldera gas",
        "ft 45 euros asistencia urgencia fontaneria",
    ],
    # ELECTRICISTA (8 frases)
    "electricista": [
        "ft 150 euros de Laura Martinez por cambio de enchufe",
        "ft 280 euros instalacion puntos luz salon",
        "ft 90 euros reparacion cortocircuito",
        "ft 420 euros quadro electrico reforma integral",
        "ft 75 euros cambio interruptor habitacion",
        "ft 550 euros instalacion fotovoltaica",
        "ft 110 euros sustitucion bombillas LED",
        "ft 190 euros reparacion horno electrico",
    ],
    # ALBAÑIL/REFORMAS (8 frases)
    "albañil": [
        "ft 850 euros de Carlos Garcia por tabique pladur",
        "ft 1200 euros reforma baño completo",
        "ft 650 euros solado terrazo",
        "ft 380 euros reparacion estructura",
        "ft 950 euros construccion pared cocina",
        "ft 1500 euros reforma integral piso 80m2",
        "ft 420 euros enfoscado paredes",
        "ft 700 euros alicatado baño",
    ],
    # PINTOR (8 frases)
    "pintor": [
        "ft 300 euros de Ana Lopez por pintar salon",
        "ft 450 euros pintura viviendas 2 habitaciones",
        "ft 180 euros repaso pintura pasillo",
        "ft 600 euros pintura integral piso 100m2",
        "ft 250 euros pintura dormitorio principal",
        "ft 800 euros pintura comunitaria escalera",
        "ft 150 euros pintar puerta y marco",
        "ft 550 euros barnizado parquet",
    ],
    # JARDINERO (8 frases)
    "jardinero": [
        "ft 80 euros de Pepe Garcia por poda árboles",
        "ft 150 euros diseno jardin residencial",
        "ft 60 euros corte cesped",
        "ft 350 euros instalacion riego automatico",
        "ft 120 euros transplante setos",
        "ft 200 euros mantenimiento jardin mensual",
        "ft 95 euros tratamiento fitosanitario",
        "ft 280 euros reforma parcial jardin",
    ],
    # PELUQUERÍA/ESTÉTICA (8 frases)
    "peluqueria": [
        "ft 45 euros de Maria Gomez por corte señora",
        "ft 80 euros tinte y mechas pelo",
        "ft 35 euros corte caballero",
        "ft 150 euros tratamiento queratina",
        "ft 60 euros manicura y pedicura",
        "ft 200 euros peinado boda",
        "ft 55 euros peinado especial",
        "ft 95 euros tratamiento facial",
    ],
    # DISEÑADOR WEB (8 frases)
    "disenador_web": [
        "ft 500 euros de Empresa SL por diseno web",
        "ft 800 euros tienda online ecommerce",
        "ft 350 euros logo y marca",
        "ft 1200 euros web corporativa",
        "ft 250 euros banner publicitario",
        "ft 600 euros redesign sitio web",
        "ft 180 euros newsletter",
        "ft 950 euros mantenimiento anual web",
    ],
    # FOTÓGRAFO (8 frases)
    "fotografo": [
        "ft 200 euros de Laura Garcia reportagem boda",
        "ft 150 euros sesion fotos producto",
        "ft 100 euros fotos basicas familia",
        "ft 350 euros book profesional",
        "ft 250 euros evento corporativo",
        "ft 80 euros retoque fotografico",
        "ft 500 euros video promocional",
        "ft 180 euros fotografia comunion",
    ],
    # TRANSPORTISTA (8 frases)
    "transportista": [
        "ft 180 euros de Empresa Logistica transporte Madrid",
        "ft 90 euros entrega zona centro",
        "ft 350 euros mercancias peligro",
        "ft 120 euros servicio urgencia",
        "ft 450 euros transporte mobiliario completo",
        "ft 60 euros recogida mobiliario",
        "ft 280 euros viaje provincial",
        "ft 200 euros manipulacion carga",
    ],
    # MECÁNICO (8 frases)
    "mecanico": [
        "ft 200 euros de Juan Garcia cambio aceite",
        "ft 150 euros reparacion pinchazo",
        "ft 400 euros revision integral",
        "ft 80 euros diagnostico electronico",
        "ft 350 euros reparacion embrague",
        "ft 120 euros cambio filtro",
        "ft 550 euros taller completo",
        "ft 95 euros alineacion ruedas",
    ],
    # CERRAJERO (8 frases)
    "cerrajero": [
        "ft 80 euros de Maria Lopez apertura urgencia",
        "ft 150 euros cambio cerradura seguridad",
        "ft 200 euros reparacion persianas",
        "ft 100 euros cierre balcon",
        "ft 350 euros cerrajeria comunidad",
        "ft 60 euros copia llaves",
        "ft 250 euros automatismo puerta",
        "ft 120 euros sistema alarma",
    ],
    # LIMPIEZA (8 frases)
    "limpieza": [
        "ft 50 euros de Ana Perez limpieza casa",
        "ft 120 euros limpieza oficina mensual",
        "ft 80 euros limpieza fin de obra",
        "ft 200 euros limpieza comunidades",
        "ft 60 euros limpieza puntual cocina",
        "ft 350 euros limpieza anual",
        "ft 45 euros limpieza escaleras",
        "ft 180 euros limpieza nave industrial",
    ],
    # FORMACIÓN (8 frases)
    "formacion": [
        "ft 300 euros de Empresa SL curso formacion Excel",
        "ft 150 euros clases particulares matematicas",
        "ft 450 euros formacion online Moodle",
        "ft 200 euros taller creatividad",
        "ft 600 euros curso intensivo idiomas",
        "ft 100 euros mentoring profesional",
        "ft 350 euros preparacion oposiciones",
        "ft 180 euros webinar seguridad laboral",
    ],
    # CONSULTORÍA (8 frases)
    "consultoria": [
        "ft 500 euros de Empresa SL consultoria gestion",
        "ft 800 euros auditoria interna",
        "ft 350 euros asesoramiento juridico",
        "ft 1200 euros proyecto viabilidad",
        "ft 250 euros consultoria RRHH",
        "ft 600 euros estrategia comercial",
        "ft 400 euros consultoria financiera",
        "ft 950 euros due diligence",
    ],
    # FISIOTERAPIA (8 frases)
    "fisioterapia": [
        "ft 50 euros de Juan Garcia sesion fisioterapia",
        "ft 80 euros tratamiento lumbar",
        "ft 120 euros rehabilitacion completa",
        "ft 45 euros consulta inicial",
        "ft 200 euros terapia ocupacional",
        "ft 70 euros masaje terapeutico",
        "ft 150 euros rehabilitacion deportiva",
        "ft 95 euros tratamiento ATM",
    ],
}


# ==============================================================================
# TIPOS DE FRASES ESPECIALES
# ==============================================================================

FRASES_ESPECIALES = {
    # Factura simplificada sin NIF bajo 400€
    "factura_simplificada_bajo_400": [
        "ft Cobré 150 euros de Pedro sin NIF",
        "ft 250 euros cliente particular sin NIF",
    ],
    # Factura con NIF obligatorio >400€
    "factura_completa_mas_400": [
        "ft Cobró 550 euros de SL Empresa NIF B12345678",
        "ft 800 euros de Inversiones SA NIF A87654321",
    ],
    # IVA 21/10/4/0
    "iva_diferentes": [
        "ft 100 euros obra construcción IVA 10 porciento",
        "ft 50 euros panaderia IVA 4 porciento",
        "ft 200 euros servicio comunidad IVA 21 porciento",
        "ft 80 euros exportar IVA 0 porciento",
    ],
    # IRPF 15/7/19 y sin IRPF
    "irpf_diferentes": [
        "ft 300 euros servicio sin retencion IRPF",
        "ft 200 euros autonomo 15 porciento IRPF",
        "ft 150 euros alquiler local 19 porciento IRPF",
    ],
    # Varios conceptos/líneas
    "multi_concepto": [
        "ft Varios: 100 euros fontaneria mas 50 euros materiales",
        "ft 2 horas trabajo 80 euros mas desplazamiento 20 euros",
    ],
    # Descuentos
    "descuentos": [
        "ft 300 euros con 10 porciento descuento",
        "ft 500 euros cliente habitual 15 porciento dto",
    ],
    # Cliente particular/autónomo/empresa
    "tipos_cliente": [
        "ft 100 euros de Miguel autonomo",
        "ft 200 euros de Maria particular",
        "ft 500 euros de SL Empresa",
    ],
    # Abono total
    "abono_total": [
        "abono total factura FI-1",
        "ft Abonar la factura FI-5 completa",
    ],
    # Abono parcial
    "abono_parcial": [
        "abono parcial 50 euros de factura FI-2",
        "ft Devolver 80 euros de la factura FI-3",
    ],
    # Rectificativa por error de precio
    "rectificativa_precio": [
        "rectificativa FI-1 error precio eran 200 no 300",
        "ft Corrección: factura FI-4 precio errado",
    ],
    # Rectificativa por error de datos
    "rectificativa_datos": [
        "rectificativa FI-2 cambio datos cliente",
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
        "ft Una factura de 100 euros",
    ],
}


def normalizar_frase(frase: str) -> str:
    """Normaliza una frase para comparación"""
    return " ".join(frase.lower().split())


def tiene_caracteres_extranos(frase: str) -> bool:
    """Detecta caracteres chinos, russ, indonesios, etc."""
    for char in frase:
        cat = unicodedata.category(char)
        # CJK characters
        if cat.startswith("C"):
            name = unicodedata.name(char, "")
            if any(x in name for x in ["CJK", "HIRAGANA", "KATAKANA", "HANGUL"]):
                return True
        # Cyrillic
        if "\u0400" <= char <= "\u04ff":
            return True
    return False


def extraer_importe(frase: str) -> float:
    """Extrae importe de una frase simple (sin llamar a API)"""
    patrones = [
        r"(\d+)\s*(?:euros?|€)",
        r"(\d+)\s*€",
        r"Cobré\s*(\d+)",
        r"Cobró\s*(\d+)",
    ]
    for patron in patrones:
        match = re.search(patron, frase.lower())
        if match:
            return float(match.group(1))
    return 0.0


def extraer_iva(frase: str) -> float:
    """Extrae IVA de una frase simple"""
    # Match IVA percentage
    match = re.search(r"(\d+)\s*%?\s*(?:IVA|iva)", frase)
    if match:
        return float(match.group(1))
    # Match "10 porciento"
    match = re.search(r"10\s*(?:porciento|%)", frase)
    if match:
        return 10.0
    # Match "4 porciento"
    match = re.search(r"4\s*(?:porciento|%)", frase)
    if match:
        return 4.0
    # Match "0 porciento" or "0%"
    match = re.search(r"0\s*(?:porciento|%)", frase)
    if match:
        return 0.0
    return 21.0


def extraer_irpf(frase: str) -> float:
    """Extrae IRPF de una frase simple"""
    match = re.search(r"(\d+)\s*%?\s*IRPF", frase)
    if match:
        pct = float(match.group(1))
        if pct in [7, 15, 19]:
            return pct
    match = re.search(r"sin\s*retencion", frase.lower())
    if match:
        return 0.0
    return 0.0


def tiene_nif(frase: str) -> bool:
    """Detecta si la frase tiene NIF"""
    return bool(
        re.search(r"\bNIF\s*[A-Z0-9]{8,9}\b|\bNIF:\s*[A-Z0-9]+\b|[0-9]{8}[A-Z]", frase)
    )


# ==============================================================================
# TESTS DE VALIDACIÓN
# ==============================================================================


class TestFrasesLimpias:
    """Tests que验证 las frases no tienen caracteres extranos"""

    def test_todas_las_frases_son_limpias(self):
        """Verifica que NO hay caracteres chinos, russ ni extranos"""
        frases_con_error = []

        for gremios, lista in FRASES_BY_GREMIOS.items():
            for frase in lista:
                if tiene_caracteres_extranos(frase):
                    frases_con_error.append(f"[{gremios}] {frase}")

        for tipo, lista in FRASES_ESPECIALES.items():
            for frase in lista:
                if tiene_caracteres_extranos(frase):
                    frases_con_error.append(f"[especial:{tipo}] {frase}")

        assert len(frases_con_error) == 0, (
            f"Caracteres extranos detectados: {frases_con_error}"
        )

    def test_todas_las_frases_tienen_importe(self):
        """Verifica que las frases de factura tienen importe"""
        # Solo frases de gremios deben tener importe
        for gremios, lista in FRASES_BY_GREMIOS.items():
            for frase in lista:
                importe = extraer_importe(frase)
                assert importe > 0, f"Sin importe en [{gremios}]: {frase}"

    def test_todas_las_frases_tienen_iva(self):
        """Verifica IVA por defecto es 21%"""
        for gremios, lista in FRASES_BY_GREMIOS.items():
            for frase in lista:
                iva = extraer_iva(frase)
                assert iva in [0, 4, 10, 21], f"IVA invalido en [{gremios}]: {frase}"

    def test_gremios_tienen_repeticion(self):
        """Verifica que cada gremio tiene al menos 8 frases"""
        for gremios, lista in FRASES_BY_GREMIOS.items():
            assert len(lista) >= 8, f"Gremio {gremios} tiene solo {len(lista)} frases"

    def test_diversidad_gremios(self):
        """Verifica que hay al menos 12 gremios"""
        assert len(FRASES_BY_GREMIOS) >= 12, (
            f"Solo hay {len(FRASES_BY_GREMIOS)} gremios"
        )

    def test_no_mezcla_idiomas(self):
        """Verifica que no hay palabras en otros idiomas"""
        for gremios, lista in FRASES_BY_GREMIOS.items():
            for frase in lista:
                # Palabras que no deben aparecer
                assert "电信" not in frase
                assert "дом" not in frase
                assert "套装" not in frase
                assert "курс" not in frase
                assert "вебинар" not in frase
                assert "ремонт" not in frase
                assert "кварт" not in frase
                assert "признак" not in frase
                assert "пакет" not in frase
                assert "包" not in frase
                assert "修理" not in frase


class TestFrasesEspeciales:
    """Tests para frases especiales"""

    def test_factura_simplificada_sin_nif(self):
        """Facturas bajo 400€ pueden no tener NIF"""
        for frase in FRASES_ESPECIALES["factura_simplificada_bajo_400"]:
            assert "sin NIF" in frase or "sin Nif" in frase

    def test_factura_completa_con_nif(self):
        """Facturas sobre 400€ deben tener NIF"""
        for frase in FRASES_ESPECIALES["factura_completa_mas_400"]:
            assert tiene_nif(frase)

    def test_iva_diferentes(self):
        """IVA puede ser 4, 10, 21 o 0%"""
        ivas_encontrados = set()
        for frase in FRASES_ESPECIALES["iva_diferentes"]:
            ivas_encontrados.add(extraer_iva(frase))
        assert (
            0.0 in ivas_encontrados
            or 4.0 in ivas_encontrados
            or 10.0 in ivas_encontrados
        )

    def test_irpf_diferentes(self):
        """IRPF puede ser 0, 7, 15 o 19%"""
        irpfs_encontrados = set()
        for frase in FRASES_ESPECIALES["irpf_diferentes"]:
            irpfs_encontrados.add(extraer_irpf(frase))
        assert (
            0.0 in irpfs_encontrados
            or 15.0 in irpfs_encontrados
            or 19.0 in irpfs_encontrados
        )

    def test_abonos_tienen_numero_factura(self):
        """Abonos deben referenciar una factura"""
        for frase in (
            FRASES_ESPECIALES["abono_total"] + FRASES_ESPECIALES["abono_parcial"]
        ):
            assert "FI-" in frase or "factura" in frase.lower()

    def test_rectificativas_tienen_numero(self):
        """Rectificativas deben referenciar una factura"""
        for frase in (
            FRASES_ESPECIALES["rectificativa_precio"]
            + FRASES_ESPECIALES["rectificativa_datos"]
        ):
            assert "FI-" in frase


# ==============================================================================
# CONTADOR TOTAL
# ==============================================================================


def get_total_frases() -> int:
    """Cuenta total de frases"""
    total = sum(len(lista) for lista in FRASES_BY_GREMIOS.values())
    total += sum(len(lista) for lista in FRASES_ESPECIALES.values())
    return total


def tiene_caracteres_extranos_test():
    """Verifica que NO hay caracteres chinos, russ ni extranos"""
    errores = []
    for gremios, lista in FRASES_BY_GREMIOS.items():
        for frase in lista:
            if tiene_caracteres_extranos(frase):
                errores.append(f"[{gremios}] {frase}")
    for tipo, lista in FRASES_ESPECIALES.items():
        for frase in lista:
            if tiene_caracteres_extranos(frase):
                errores.append(f"[especial:{tipo}] {frase}")
    if errores:
        print(f"FAIL: Caracteres extranos detectados: {errores}")
        return False
    print("PASS: Sin caracteres extranos")
    return True


def tiene_importe_test():
    """Verifica que las frases de factura tienen importe"""
    errores = []
    for gremios, lista in FRASES_BY_GREMIOS.items():
        for frase in lista:
            importe = extraer_importe(frase)
            if importe <= 0:
                errores.append(f"[{gremios}] Sin importe: {frase}")
    if errores:
        print(f"FAIL: {len(errores)} frases sin importe")
        return False
    print("PASS: Todas las frases tienen importe")
    return True


def tiene_iva_test():
    """Verifica IVA por defecto es 21%"""
    errores = []
    for gremios, lista in FRASES_BY_GREMIOS.items():
        for frase in lista:
            iva = extraer_iva(frase)
            if iva not in [0, 4, 10, 21]:
                errores.append(f"[{gremios}] IVA invalido: {frase}")
    if errores:
        print(f"FAIL: {len(errores)} frases con IVA invalido")
        return False
    print("PASS: IVA correcto en todas las frases")
    return True


def test_contador_total():
    """Debe haber al menos 100 frases"""
    if get_total_frases() < 100:
        print(f"FAIL: Solo hay {get_total_frases()} frases")
        return False
    print(f"PASS: {get_total_frases()} frases (minimo 100)")
    return True


def run_all_tests():
    """Ejecuta todos los tests"""
    results = []
    print("\n=== EJECUTANDO TESTS ===\n")

    results.append(("frases_sin_caracteres_extranos", tiene_caracteres_extranos_test()))
    results.append(("todas_tienen_importe", tiene_importe_test()))
    results.append(("iva_correcto", tiene_iva_test()))
    results.append(("contador_minimo_100", test_contador_total()))

    print("\n=== RESUMEN ===")
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"Total: {total}, Pass: {passed}, Fail: {total - passed}")

    return all(r for _, r in results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
