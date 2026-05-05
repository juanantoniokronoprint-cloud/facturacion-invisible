"""
Servicio de integración con VeriFacti API
Documentación: https://www.verifacti.com/desarrolladores/ejemplos
"""
import os
import httpx
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# URL correcta de VeriFacti (no Verifactu)
VERIFACTI_API_URL = "https://api.verifacti.com"
VERIFACTI_API_KEY = os.getenv("VERIFACTI_API_KEY", "")

# Tipos de factura según VeriFactu
TIPO_FACTURA_F1 = "F1"  # Factura normal
TIPO_FACTURA_F2 = "F2"  # Factura simplificada
TIPO_FACTURA_F3 = "F3"  # Factura sustitutiva de simplificada

# Tipos de factura rectificativa
TIPO_FACTURA_R1 = "R1"  # Rectificativa por error fundado Art. 80.1, 80.2, 80.6
TIPO_FACTURA_R2 = "R2"  # Rectificativa por concurso Art. 80.3
TIPO_FACTURA_R3 = "R3"  # Rectificativa por crédito incobrable Art. 80.4
TIPO_FACTURA_R4 = "R4"  # Rectificativa por otras razones
TIPO_FACTURA_R5 = "R5"  # Rectificativa de factura simplificada

# Tipos de rectificación
TIPO_RECTIFICATIVA_S = "S"  # Por sustitución
TIPO_RECTIFICATIVA_I = "I"    # Por diferencias


class VerifactuAPI:
    """Cliente para la API de Verifactu"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or VERIFACTI_API_KEY
        self.base_url = VERIFACTI_API_URL
        
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def crear_factura(self, factura_data: dict) -> dict:
        """Crea una factura en Verifactu"""
        if not self.api_key:
            logger.warning("Verifactu API key no configurada - modo demo")
            return {"status": "demo", "message": "Modo demo - factura no enviada a AEAT"}
        
        url = f"{self.base_url}/verifactu/create"
        
        try:
            response = httpx.post(url, json=factura_data, headers=self._headers(), timeout=30)
            
            if response.status_code in (200, 201):
                logger.info("Factura enviada a Verifactu correctamente")
                return {"status": "ok", "data": response.json()}
            else:
                logger.error(f"Error Verifactu: {response.status_code} - {response.text}")
                return {"status": "error", "message": response.text}
                
        except Exception as e:
            logger.error(f"Excepción conectando a Verifactu: {e}")
            return {"status": "error", "message": str(e)}
    
    def consultar_estado(self, factura_id: str) -> dict:
        """Consulta el estado de una factura"""
        if not self.api_key:
            return {"status": "demo"}
        
        url = f"{self.base_url}/facturas/{factura_id}/estado"
        
        try:
            response = httpx.get(url, headers=self._headers(), timeout=30)
            return response.json() if response.status_code == 200 else {"status": "error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


def crear_factura_verifactu(
    serie: str,
    numero: str,
    fecha_expedicion: str,
    nif_cliente: str,
    nombre_cliente: str,
    lineas: list,
    importe_total: float,
    tipo_factura: str = TIPO_FACTURA_F1,
    descripcion: str = "",
    serie_rectificada: str = None,
    numero_rectificada: str = None,
    fecha_rectificada: str = None,
    tipo_rectificativa: str = None,
    base_rectificada: float = None,
    cuota_rectificada: float = None
) -> dict:
    """
    Crea el JSON para una factura VeriFactu
    
    Tipos de factura:
    - F1: Factura normal
    - F2: Factura simplificada
    - F3: Factura sustitutiva de simplificada
    - R1-R5: Facturas rectificativas
    
    Tipos de rectificación:
    - S: Por sustitución (2 pasos)
    - I: Por diferencias (1 paso)
    """
    
    factura = {
        "serie": serie,
        "numero": numero,
        "fecha_expedicion": fecha_expedicion,
        "tipo_factura": tipo_factura,
        "descripcion": descripcion,
        "nif": nif_cliente,
        "nombre": nombre_cliente,
        "lineas": lineas,
        "importe_total": str(importe_total)
    }
    
    # Si es una factura rectificativa
    if tipo_factura.startswith("R"):
        if serie_rectificada and numero_rectificada and fecha_rectificada:
            factura["facturas_rectificadas"] = [{
                "serie": serie_rectificada,
                "numero": numero_rectificada,
                "fecha_expedicion": fecha_rectificada
            }]
        
        if tipo_rectificativa:
            factura["tipo_rectificativa"] = tipo_rectificativa
            
            # Por sustitución en un paso
            if tipo_rectificativa == TIPO_RECTIFICATIVA_S and base_rectificada is not None:
                factura["importe_rectificativa"] = {
                    "base_rectificada": str(base_rectificada),
                    "cuota_rectificada": str(cuota_rectificada or 0)
                }
    
    # Si sustituye a facturas simplificadas
    if tipo_factura == TIPO_FACTURA_F3 and serie_rectificada:
        factura["facturas_sustituidas"] = [{
            "serie": serie_rectificada,
            "numero": numero_rectificada,
            "fecha_expedicion": fecha_rectificada
        }]
    
    return factura


def crear_linea_factura(
    base_imponible: float,
    tipo_impositivo: float,
    cuota_repercutida: float,
    descripcion: str = "",
    operacion_exenta: str = None,
    calificacion_operacion: str = None
) -> dict:
    """Crea una línea de factura para VeriFactu"""
    
    linea = {
        "base_imponible": str(base_imponible),
        "tipo_impositivo": str(tipo_impositivo),
        "cuota_repercutida": str(cuota_repercutida)
    }
    
    if descripcion:
        linea["descripcion"] = descripcion
    
    if operacion_exenta:
        linea["operacion_exenta"] = operacion_exenta
    
    if calificacion_operacion:
        linea["calificacion_operacion"] = calificacion_operacion
    
    return linea


def crear_factura_abono(
    serie: str,
    numero: str,
    fecha_expedicion: str,
    nif_cliente: str,
    nombre_cliente: str,
    base_imponible: float,
    tipo_impositivo: float,
    cuota_iva: float,
    descripcion: str = "",
    serie_factura_original: str = None,
    numero_factura_original: str = None,
    fecha_factura_original: str = None
) -> dict:
    """
    Crea una factura de abono (rectificativa) según VeriFactu
    
    Una factura de abono es simplemente una factura con importes negativos.
    Se puede usar para:
    - Devoluciones
    - Descuentos posteriores
    - Correcciones
    
    Para.rectificaciones formales usar crear_factura_rectificativa()
    """
    
    importe_total = base_imponible + cuota_iva
    
    lineas = [crear_linea_factura(
        base_imponible=-abs(base_imponible),
        tipo_impositivo=tipo_impositivo,
        cuota_repercutida=-abs(cuota_iva),
        descripcion=descripcion
    )]
    
    data = crear_factura_verifactu(
        serie=serie,
        numero=numero,
        fecha_expedicion=fecha_expedicion,
        nif_cliente=nif_cliente,
        nombre_cliente=nombre_cliente,
        lineas=lineas,
        importe_total=-abs(importe_total),
        tipo_factura=TIPO_FACTURA_F1,  # Una factura de abono puede ser F1 normal pero con importes negativos
        descripcion=descripcion or "Factura de abono"
    )
    
    # Opcional: vincular a factura original
    if serie_factura_original and numero_factura_original:
        data["facturas_rectificadas"] = [{
            "serie": serie_factura_original,
            "numero": numero_factura_original,
            "fecha_expedicion": fecha_factura_original
        }]
        data["tipo_rectificativa"] = TIPO_RECTIFICATIVA_I
    
    return data


def crear_rectificativa_por_sustitucion(
    serie: str,
    numero: str,
    fecha_expedicion: str,
    nif_cliente: str,
    nombre_cliente: str,
    nueva_base: float,
    nuevo_tipo_iva: float,
    nueva_cuota_iva: float,
    descripcion: str,
    serie_original: str,
    numero_original: str,
    fecha_original: str,
    base_original: float,
    cuota_original: float
) -> dict:
    """
    Crea una factura rectificativa por SUSTITUCIÓN (2 pasos o 1 paso)
    
    Args:
        nueva_base: Nueva base imponible
        base_original: Base imponible de la factura original
    """
    
    importe_nuevo = nueva_base + nueva_cuota_iva
    
    lineas = [crear_linea_factura(
        base_imponible=str(nueva_base),
        tipo_impositivo=str(nuevo_tipo_iva),
        cuota_repercutida=str(nueva_cuota_iva),
        descripcion=descripcion
    )]
    
    data = crear_factura_verifactu(
        serie=serie,
        numero=numero,
        fecha_expedicion=fecha_expedicion,
        nif_cliente=nif_cliente,
        nombre_cliente=nombre_cliente,
        lineas=lineas,
        importe_total=importe_nuevo,
        tipo_factura=TIPO_FACTURA_R1,  # Rectificativa por error fundado
        descripcion=f"Rectificativa por sustitución: {descripcion}",
        serie_rectificada=serie_original,
        numero_rectificada=numero_original,
        fecha_rectificada=fecha_original,
        tipo_rectificativa=TIPO_RECTIFICATIVA_S,
        base_rectificada=base_original,
        cuota_rectificada=cuota_original
    )
    
    return data


def crear_rectificativa_por_diferencias(
    serie: str,
    numero: str,
    fecha_expedicion: str,
    nif_cliente: str,
    nombre_cliente: str,
    diferencia_base: float,
    diferencia_cuota: float,
    tipo_iva: float,
    descripcion: str,
    serie_original: str,
    numero_original: str,
    fecha_original: str
) -> dict:
    """
    Crea una factura rectificativa por DIFERENCIAS (1 solo paso)
    
    Args:
        diferencia_base: Diferencia en base imponible (positiva o negativa)
        diferencia_cuota: Diferencia en cuota IVA (positiva o negativa)
    """
    
    importe_total = diferencia_base + diferencia_cuota
    
    lineas = [crear_linea_factura(
        base_imponible=str(diferencia_base),
        tipo_impositivo=str(tipo_iva),
        cuota_repercutida=str(diferencia_cuota),
        descripcion=descripcion
    )]
    
    data = crear_factura_verifactu(
        serie=serie,
        numero=numero,
        fecha_expedicion=fecha_expedicion,
        nif_cliente=nif_cliente,
        nombre_cliente=nombre_cliente,
        lineas=lineas,
        importe_total=importe_total,
        tipo_factura=TIPO_FACTURA_R1,
        descripcion=f"Rectificativa por diferencias: {descripcion}",
        serie_rectificada=serie_original,
        numero_rectificada=numero_original,
        fecha_rectificada=fecha_original,
        tipo_rectificativa=TIPO_RECTIFICATIVA_I
    )
    
    return data


# Función de conveniencia para enviar a Verifactu
def enviar_factura_a_verifactu(factura_data: dict) -> dict:
    """Envía una factura a la API de Verifactu"""
    api = VerifactuAPI()
    return api.crear_factura(factura_data)


def enviar_factura_verificacion(factura_data: dict) -> dict:
    """Alias legacy para smoke tests/integraciones antiguas."""
    return enviar_factura_a_verifactu(factura_data)
