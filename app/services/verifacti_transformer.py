"""
Transformador de datos ERP → formato VeriFacti API
Convierte facturas del ERP Krono al formato esperado por VeriFacti.com
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class VeriFactiTransformer:
    """Transforma datos de factura ERP a formato VeriFacti"""
    
    # Mapeo de tipos de IVA estándar
    TIPO_IVA_MAP = {
        21.0: "G21",
        10.0: "R10",
        4.0: "S4",
        0.0: "E0"
    }
    
    # Porcentajes de recargo de equivalencia según IVA
    RECARGO_EQUIVALENCIA = {
        21.0: 5.2,
        10.0: 1.4,
        4.0: 0.5,
        0.0: 0.0
    }
    
    @staticmethod
    def transform_factura(
        factura: Dict[str, Any],
        cliente: Dict[str, Any],
        lineas: List[Dict[str, Any]],
        empresa: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Transforma una factura del ERP al formato VeriFacti
        
        Args:
            factura: Datos de la factura (serie, numero, fecha, etc.)
            cliente: Datos del cliente (nif, nombre, etc.)
            lineas: Lista de líneas de la factura
            empresa: Datos de la empresa emisora (opcional)
        
        Returns:
            Dict en formato VeriFacti API
        """
        
        # Convertir fecha a formato DD-MM-YYYY
        try:
            # Intentar varios campos de fecha
            fecha_str = factura.get('fecha') or factura.get('DFECFAC') or factura.get('DFEC')
            if not fecha_str:
                raise ValueError("No se encontró fecha en la factura")
            
            if isinstance(fecha_str, str):
                # Intentar parsear diferentes formatos
                for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
                    try:
                        fecha_obj = datetime.strptime(fecha_str, fmt)
                        break
                    except:
                        continue
                else:
                    # Si ningún formato funcionó, usar fecha actual
                    fecha_obj = datetime.now()
            else:
                # Si es un objeto date o datetime
                fecha_obj = fecha_str
            
            fecha_expedicion = fecha_obj.strftime('%d-%m-%Y')
        except Exception as e:
            logger.error(f"Error convirtiendo fecha: {e}")
            fecha_expedicion = datetime.now().strftime('%d-%m-%Y')
        
        # Agrupar líneas por tipo de IVA (máximo 12 líneas permitidas por AEAT)
        lineas_agrupadas = VeriFactiTransformer._agrupar_lineas_por_iva(lineas, cliente)
        
        # Calcular totales
        total_base = sum(float(l.get('base_imponible', 0)) for l in lineas_agrupadas)
        total_iva = sum(float(l.get('cuota_repercutida', 0)) for l in lineas_agrupadas)
        total_re = sum(float(l.get('cuota_recargo_equivalencia', 0)) for l in lineas_agrupadas)
        importe_total = total_base + total_iva + total_re
        
        # Determinar tipo de factura
        tipo_factura = VeriFactiTransformer._determinar_tipo_factura(factura, cliente)
        
        # Construir JSON básico
        verifacti_data = {
            "serie": str(factura.get('serie', '')),
            "numero": str(factura.get('numero', '')),
            "fecha_expedicion": fecha_expedicion,
            "tipo_factura": tipo_factura,
            "descripcion": VeriFactiTransformer._generar_descripcion(factura, lineas),
            "lineas": [
                {
                    "base_imponible": str(round(float(l['base_imponible']), 2)),
                    "tipo_impositivo": str(l['tipo_impositivo']),
                    "cuota_repercutida": str(round(float(l['cuota_repercutida']), 2))
                }
                for l in lineas_agrupadas
            ],
            "importe_total": str(round(importe_total, 2))
        }
        
        # Añadir recargo de equivalencia si existe
        for i, linea in enumerate(lineas_agrupadas):
            re = float(linea.get('cuota_recargo_equivalencia', 0))
            if re > 0:
                verifacti_data["lineas"][i]["cuota_recargo_equivalencia"] = str(round(re, 2))
        
        # Añadir datos del cliente si no es factura simplificada
        if tipo_factura not in ["F2", "R5"]:
            nif_cliente = cliente.get('nif') or cliente.get('CDNICIF') or cliente.get('CIF') or ''
            nombre_cliente = cliente.get('nombre') or cliente.get('CNOMCLI') or cliente.get('NOMBRE') or ''
            
            if nif_cliente:
                verifacti_data["nif"] = str(nif_cliente).strip()
            if nombre_cliente:
                verifacti_data["nombre"] = str(nombre_cliente).strip()[:120]  # Máximo 120 caracteres
        
        # Añadir fecha de operación si es diferente
        if factura.get('fecha_operacion') and factura['fecha_operacion'] != factura.get('fecha'):
            try:
                fecha_op = datetime.strptime(factura['fecha_operacion'], '%Y-%m-%d').strftime('%d-%m-%Y')
                verifacti_data["fecha_operacion"] = fecha_op
            except:
                pass
        
        return verifacti_data
    
    @staticmethod
    def transform_rectificativa(
        factura: Dict[str, Any],
        cliente: Dict[str, Any],
        lineas: List[Dict[str, Any]],
        tipo_rectificativa: str = "R1",  # R1, R2, R3, R4, R5
        tipo: str = "I",  # S (sustitución) o I (diferencia)
        factura_original: Optional[Dict[str, Any]] = None,
        motivo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transforma una factura rectificativa
        
        Args:
            factura: Datos de la nueva factura
            cliente: Datos del cliente
            lineas: Líneas de la rectificativa
            tipo_rectificativa: R1, R2, R3, R4 o R5
            tipo: S (sustitución) o I (diferencia)
            factura_original: Datos de la factura original (opcional)
            motivo: Motivo de la rectificación
        
        Returns:
            Dict en formato VeriFacti con datos de rectificativa
        """
        # Obtener datos básicos
        factura_data = {**factura, 'tipo_factura': tipo_rectificativa}
        verifacti_data = VeriFactiTransformer.transform_factura(
            factura_data, cliente, lineas
        )
        
        # Añadir tipo de rectificativa
        verifacti_data["tipo_rectificativa"] = tipo
        
        # Añadir motivo si se proporciona
        if motivo:
            verifacti_data["motivo"] = str(motivo)[:500]  # Máximo 500 caracteres
        
        # Si es por sustitución, añadir importes rectificados
        if tipo == "S" and factura_original:
            lineas_orig = factura_original.get('lineas', [])
            total_base_orig = sum(float(l.get('base', 0)) for l in lineas_orig)
            total_iva_orig = sum(float(l.get('iva', 0)) for l in lineas_orig)
            total_re_orig = sum(float(l.get('re', 0)) for l in lineas_orig)
            
            verifacti_data["importe_rectificativa"] = {
                "base_rectificada": str(round(total_base_orig, 2)),
                "cuota_rectificada": str(round(total_iva_orig, 2))
            }
            if total_re_orig > 0:
                verifacti_data["importe_rectificativa"]["cuota_recargo_rectificada"] = str(round(total_re_orig, 2))
        
        # Añadir referencia a factura original si existe
        if factura_original:
            try:
                fecha_orig = datetime.strptime(factura_original['fecha'], '%Y-%m-%d').strftime('%d-%m-%Y')
                verifacti_data["facturas_rectificadas"] = [{
                    "serie": str(factura_original.get('serie', '')),
                    "numero": str(factura_original.get('numero', '')),
                    "fecha_expedicion": fecha_orig
                }]
            except:
                pass
        
        return verifacti_data
    
    @staticmethod
    def transform_f3_substitucion(
        factura: Dict[str, Any],
        cliente: Dict[str, Any],
        lineas: List[Dict[str, Any]],
        facturas_sustituidas: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Transforma una factura F3 (sustitución de facturas simplificadas)
        
        Args:
            factura: Datos de la nueva factura
            cliente: Datos del cliente
            lineas: Líneas de la factura
            facturas_sustituidas: Lista de facturas simplificadas que sustituye
        
        Returns:
            Dict en formato VeriFacti con datos de sustitución
        """
        # Obtener datos básicos
        factura_data = {**factura, 'tipo_factura': 'F3'}
        verifacti_data = VeriFactiTransformer.transform_factura(
            factura_data, cliente, lineas
        )
        
        # Añadir facturas sustituidas
        verifacti_data["facturas_sustituidas"] = []
        for fact_sust in facturas_sustituidas or []:
            try:
                fecha_sust = datetime.strptime(fact_sust['fecha'], '%Y-%m-%d').strftime('%d-%m-%Y')
                verifacti_data["facturas_sustituidas"].append({
                    "serie": str(fact_sust.get('serie', '')),
                    "numero": str(fact_sust.get('numero', '')),
                    "fecha_expedicion": fecha_sust
                })
            except:
                pass
        
        return verifacti_data
    
    @staticmethod
    def _agrupar_lineas_por_iva(
        lineas: List[Dict[str, Any]], 
        cliente: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Agrupa líneas por tipo de IVA (AEAT permite máximo 12 líneas)
        
        Args:
            lineas: Lista de líneas de la factura
            cliente: Datos del cliente para determinar recargo
        
        Returns:
            Lista de líneas agrupadas por IVA con base, cuota y recargo
        """
        # Determinar si el cliente tiene recargo de equivalencia
        tiene_recargo = bool(
            cliente.get('LREQ') or 
            cliente.get('RECARGO_EQUIVALENCIA') or 
            cliente.get('recargo_equivalencia') or
            0
        )
        
        agrupadas = {}
        
        for linea in lineas:
            # Extraer datos de la línea (soportar múltiples formatos)
            cantidad = float(linea.get('cantidad') or linea.get('NCANENT') or linea.get('NCANPED') or 0)
            precio = float(linea.get('precio') or linea.get('precio_unitario') or linea.get('NPREUNIT') or 0)
            descuento = float(linea.get('dto_pct') or linea.get('NDTO') or 0)
            iva_pct = float(linea.get('iva_pct') or linea.get('NIVA') or linea.get('IVA') or 21.0)
            
            # Calcular base imponible
            base = cantidad * precio * (1 - descuento / 100.0)
            
            # Calcular IVA
            iva = base * (iva_pct / 100.0)
            
            # Calcular recargo de equivalencia
            re = 0.0
            if tiene_recargo:
                re_pct = VeriFactiTransformer.RECARGO_EQUIVALENCIA.get(iva_pct, 0.0)
                # Si el IVA no está en el mapa, buscar el más cercano
                if re_pct == 0.0 and iva_pct > 0:
                    for iva_std, re_std in VeriFactiTransformer.RECARGO_EQUIVALENCIA.items():
                        if abs(iva_pct - iva_std) < 0.5:
                            re_pct = re_std
                            break
                re = base * (re_pct / 100.0)
            
            # Agrupar por tipo de IVA (usar string con 2 decimales como key)
            key = f"{iva_pct:.2f}"
            
            if key not in agrupadas:
                agrupadas[key] = {
                    "base_imponible": 0.0,
                    "tipo_impositivo": iva_pct,
                    "cuota_repercutida": 0.0,
                    "cuota_recargo_equivalencia": 0.0
                }
            
            agrupadas[key]["base_imponible"] += base
            agrupadas[key]["cuota_repercutida"] += iva
            agrupadas[key]["cuota_recargo_equivalencia"] += re
        
        # Convertir a lista y ordenar por tipo de IVA (descendente)
        result = sorted(agrupadas.values(), key=lambda x: x["tipo_impositivo"], reverse=True)
        
        # Validar que no excedemos el máximo de 12 líneas
        if len(result) > 12:
            logger.warning(f"Factura tiene {len(result)} tipos de IVA diferentes, AEAT permite máximo 12")
            # En este caso, habría que combinar los tipos de IVA menos comunes
            # Por ahora, truncamos (no debería ocurrir en la práctica)
            result = result[:12]
        
        return result
    
    @staticmethod
    def _determinar_tipo_factura(factura: Dict[str, Any], cliente: Dict[str, Any]) -> str:
        """
        Determina el tipo de factura según datos
        
        Art. 7 RD 1619/2012: Factura simplificada (F2) solo si:
        - Importe total (IVA incluido) <= 400€
        - NO incluye NIF del cliente
        
        Returns:
            Código de tipo: F1, F2, R1, R2, R3, R4, R5, F3
        """
        # Si ya viene especificado, usarlo
        if factura.get('tipo_factura'):
            return factura['tipo_factura']
        
        # Si es rectificativa, se indicará explícitamente
        if factura.get('es_rectificativa'):
            return factura.get('tipo_rectificativa', 'R1')
        
        # Determinar si tiene NIF
        tiene_nif = bool(cliente.get('nif') or cliente.get('CDNICIF') or cliente.get('CIF'))
        
        # Calcular total CON IVA para límite 400€
        base = float(factura.get('total', 0))
        iva_pct = float(factura.get('iva_pct', 21))
        total_con_iva = base * (1 + iva_pct / 100)
        
        # Si tiene NIF -> siempre F1 (factura completa)
        if tiene_nif:
            return "F1"
        
        # Si NO tiene NIF:
        # - Si total con IVA <= 400€ -> F2 (simplificada)
        # - Si total con IVA > 400€ -> F1 (pero el sistema debe pedir NIF antes)
        if total_con_iva <= 400:
            return "F2"  # Factura simplificada
        
        # Total > 400€ sin NIF: debe ser F1 (el sistema validará que necesita NIF)
        return "F1"
    
    @staticmethod
    def _generar_descripcion(factura: Dict[str, Any], lineas: List[Dict[str, Any]]) -> str:
        """
        Genera descripción de la factura (máximo 500 caracteres)
        """
        # Intentar usar descripción existente
        if factura.get('descripcion'):
            desc = str(factura['descripcion'])[:500]
            return desc
        
        # Generar descripción básica
        serie = factura.get('serie', '')
        numero = factura.get('numero', '')
        desc = f"Factura {serie}{numero}"
        
        # Añadir resumen de líneas si hay pocas
        if len(lineas) <= 3:
            items = []
            for linea in lineas[:3]:
                nombre = (
                    linea.get('descripcion') or 
                    linea.get('CDESART') or 
                    linea.get('NOMBRE') or 
                    'Artículo'
                )
                items.append(str(nombre)[:50])
            
            if items:
                desc += ": " + ", ".join(items)
        else:
            desc += f" con {len(lineas)} líneas"
        
        return desc[:500]  # Máximo 500 caracteres


def transformar_factura_verifactu(factura, cliente, tipo_factura: str = "F1") -> Dict[str, Any]:
    """Adaptador ORM de Factura Invisible → formato VeriFacti."""
    factura_dict = {
        "serie": getattr(factura, "serie", ""),
        "numero": getattr(factura, "numero", ""),
        "fecha": getattr(factura, "fecha_emision", None).strftime("%Y-%m-%d")
        if getattr(factura, "fecha_emision", None)
        else datetime.now().strftime("%Y-%m-%d"),
        "fecha_operacion": getattr(factura, "fecha_operacion", None).strftime("%Y-%m-%d")
        if getattr(factura, "fecha_operacion", None)
        else None,
        "tipo_factura": tipo_factura or getattr(factura, "tipo_factura", None) or "F1",
        "total": getattr(factura, "base_imponible", 0) or 0,
        "iva_pct": getattr(factura, "iva_pct", 21) or 21,
        "descripcion": getattr(factura, "motivo_rectificacion", None),
    }
    cliente_dict = {
        "nif": getattr(cliente, "nif", None),
        "nombre": getattr(cliente, "nombre", None),
    }
    lineas = [
        {
            "descripcion": linea.descripcion,
            "cantidad": linea.cantidad,
            "precio_unitario": linea.precio_unitario,
            "dto_pct": linea.descuento_pct,
            "iva_pct": linea.iva_pct,
        }
        for linea in getattr(factura, "lineas", []) or []
    ]
    if not lineas:
        lineas = [
            {
                "descripcion": factura_dict["descripcion"] or f"Factura {factura_dict['serie']}-{factura_dict['numero']}",
                "cantidad": 1,
                "precio_unitario": getattr(factura, "base_imponible", 0) or 0,
                "iva_pct": getattr(factura, "iva_pct", 21) or 21,
            }
        ]

    tipo_rectificacion = getattr(factura, "tipo_rectificacion", None)
    factura_origen = getattr(factura, "factura_origen", None)
    if str(factura_dict["tipo_factura"]).startswith("R") and tipo_rectificacion:
        factura_original = None
        if factura_origen:
            factura_original = {
                "serie": getattr(factura_origen, "serie", ""),
                "numero": getattr(factura_origen, "numero", ""),
                "fecha": getattr(factura_origen, "fecha_emision", None).strftime("%Y-%m-%d")
                if getattr(factura_origen, "fecha_emision", None)
                else datetime.now().strftime("%Y-%m-%d"),
                "lineas": [
                    {
                        "base": getattr(linea, "base_imponible", 0) or 0,
                        "iva": getattr(linea, "iva_cuota", 0) or 0,
                    }
                    for linea in getattr(factura_origen, "lineas", []) or []
                ],
            }
        return VeriFactiTransformer.transform_rectificativa(
            factura_dict,
            cliente_dict,
            lineas,
            factura_dict["tipo_factura"],
            tipo_rectificacion,
            factura_original=factura_original,
            motivo=getattr(factura, "motivo_rectificacion", None),
        )

    return VeriFactiTransformer.transform_factura(factura_dict, cliente_dict, lineas)


def transformar_factura_verifacti(factura, cliente=None, tipo_factura: str = "F1") -> Dict[str, Any]:
    """Alias compatible para pruebas/integraciones antiguas."""
    if cliente is None:
        cliente = getattr(factura, "cliente", None)
    data = transformar_factura_verifactu(factura, cliente, tipo_factura)
    data.setdefault("numeroFactura", f"{data.get('serie', '')}-{data.get('numero', '')}".strip("-"))
    return data


def transformar_rectificativa_verifacti(factura, cliente=None, tipo_factura: Optional[str] = None) -> Dict[str, Any]:
    """Alias compatible para rectificativas antiguas."""
    tipo = tipo_factura or getattr(factura, "tipo_factura", None) or "R1"
    if cliente is None:
        cliente = getattr(factura, "cliente", None)
    data = transformar_factura_verifactu(factura, cliente, tipo)
    data.setdefault("numeroFactura", f"{data.get('serie', '')}-{data.get('numero', '')}".strip("-"))
    return data


def validar_nif_formato(nif: str) -> bool:
    """
    Valida formato básico de NIF/NIE/CIF español.
    """
    if not nif:
        return False

    nif = nif.strip().upper()

    if len(nif) != 9:
        return False

    if nif[:8].isdigit() and nif[8].isalpha():
        return True

    if nif[0].isalpha() and nif[0] in "ABCDEFGHJNPQRSUVW" and nif[1:].isdigit():
        return True

    if nif[0] in "XYZABCDEFGHJNPQRSUVW" and nif[1:8].isdigit() and nif[8].isalpha():
        return True

    return False


VeriFactiTransformer.validar_nif_formato = staticmethod(validar_nif_formato)
