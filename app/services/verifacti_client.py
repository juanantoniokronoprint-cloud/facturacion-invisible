"""
Cliente HTTP para API VeriFacti.com
Gestiona todas las comunicaciones con la API de VeriFacti
"""

import httpx
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class VeriFactiClient:
    """Cliente HTTP para interactuar con API VeriFacti.com"""
    
    BASE_URL = "https://api.verifacti.com"
    TIMEOUT = 30.0
    
    def __init__(self, api_key: str):
        """
        Inicializa el cliente con una API key
        
        Args:
            api_key: API key de VeriFacti (test o producción)
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def health(self) -> Dict[str, Any]:
        """
        Verifica el estado de la API y la validez de la API key
        
        Returns:
            Dict con estado, nif y entorno
        
        Raises:
            httpx.HTTPError: Si hay error de conexión
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/verifactu/health",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def create(self, factura_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea una nueva factura en VeriFacti
        
        Args:
            factura_data: Datos de la factura en formato VeriFacti
        
        Returns:
            Dict con uuid, estado, url, qr y huella
        
        Raises:
            httpx.HTTPError: Si hay error HTTP
            Exception: Si VeriFacti rechaza la factura (error 400)
        """
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/verifactu/create",
                    headers=self.headers,
                    json=factura_data
                )
                
                if response.status_code == 400:
                    error_data = response.json()
                    raise Exception(f"VeriFacti rechazó la factura: {error_data.get('error', 'Error desconocido')}")
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPError as e:
                logger.error(f"Error HTTP creando factura: {e}")
                raise
    
    async def create_bulk(self, facturas_data: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """
        Crea múltiples facturas en lote (hasta 50)
        
        Args:
            facturas_data: Lista de hasta 50 facturas
        
        Returns:
            Lista de respuestas con uuid, estado, url y qr para cada factura
        """
        if len(facturas_data) > 50:
            raise ValueError("Máximo 50 facturas por lote")
        
        async with httpx.AsyncClient(timeout=self.TIMEOUT * 2) as client:
            response = await client.post(
                f"{self.BASE_URL}/verifactu/create_bulk",
                headers=self.headers,
                json=facturas_data
            )
            
            if response.status_code == 400:
                error_data = response.json()
                raise Exception(f"Error en lote: {error_data.get('error', 'Error desconocido')}")
            
            response.raise_for_status()
            return response.json()
    
    async def status_by_uuid(self, uuid: str) -> Dict[str, Any]:
        """
        Consulta el estado de un registro por UUID
        
        Args:
            uuid: UUID del registro devuelto al crear la factura
        
        Returns:
            Dict con estado detallado del registro
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/verifactu/status",
                params={"uuid": uuid},
                headers=self.headers
            )
            
            if response.status_code == 404:
                raise Exception(f"Registro con UUID {uuid} no encontrado")
            
            response.raise_for_status()
            return response.json()
    
    async def status_by_factura(
        self, 
        serie: str, 
        numero: str, 
        fecha_expedicion: str,
        fecha_operacion: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Consulta el estado de una factura en AEAT
        
        Args:
            serie: Serie de la factura
            numero: Número de la factura
            fecha_expedicion: Fecha en formato DD-MM-YYYY
            fecha_operacion: Fecha operación (opcional)
        
        Returns:
            Dict con estado de la factura en AEAT
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            data = {
                "serie": serie,
                "numero": numero,
                "fecha_expedicion": fecha_expedicion
            }
            if fecha_operacion:
                data["fecha_operacion"] = fecha_operacion
            
            response = await client.post(
                f"{self.BASE_URL}/verifactu/status",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    async def modify(
        self, 
        factura_data: Dict[str, Any], 
        rechazo_previo: str = "N"
    ) -> Dict[str, Any]:
        """
        Subsana una factura existente
        
        Args:
            factura_data: Datos de la factura corregidos
            rechazo_previo: N (subsanación normal), S (rechazo de subsanación), X (rechazo de alta)
        
        Returns:
            Dict con uuid, estado, url y qr
        """
        factura_data["rechazo_previo"] = rechazo_previo
        
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            response = await client.put(
                f"{self.BASE_URL}/verifactu/modify",
                headers=self.headers,
                json=factura_data
            )
            
            if response.status_code == 400:
                error_data = response.json()
                raise Exception(f"Error subsanando: {error_data.get('error', 'Error desconocido')}")
            
            response.raise_for_status()
            return response.json()
    
    async def cancel(
        self, 
        serie: str, 
        numero: str, 
        fecha_expedicion: str,
        rechazo_previo: str = "N",
        sin_registro_previo: str = "N",
        incidencia: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Anula una factura
        
        Args:
            serie: Serie de la factura
            numero: Número de la factura
            fecha_expedicion: Fecha en formato DD-MM-YYYY
            rechazo_previo: N (anulación normal), S (anulación tras rechazo)
            sin_registro_previo: N (factura registrada), S (factura sin registrar)
            incidencia: S si hay incidencia
        
        Returns:
            Dict con uuid y estado
        """
        data = {
            "serie": serie,
            "numero": numero,
            "fecha_expedicion": fecha_expedicion,
            "rechazo_previo": rechazo_previo,
            "sin_registro_previo": sin_registro_previo
        }
        if incidencia:
            data["incidencia"] = incidencia
        
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            response = await client.post(
                f"{self.BASE_URL}/verifactu/cancel",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    async def list_facturas(
        self,
        ejercicio: str,
        periodo: str,
        serie: Optional[str] = None,
        numero: Optional[str] = None,
        fecha_expedicion: Optional[str] = None,
        rango_fecha_desde: Optional[str] = None,
        rango_fecha_hasta: Optional[str] = None,
        paginacion_num_serie: Optional[str] = None,
        paginacion_fecha: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista facturas registradas en AEAT
        
        Args:
            ejercicio: Año (ej: "2024")
            periodo: Mes (ej: "12")
            serie: Serie específica (opcional)
            numero: Número específico (opcional)
            fecha_expedicion: Fecha específica DD-MM-YYYY (opcional)
            rango_fecha_desde: Inicio rango DD-MM-YYYY (opcional)
            rango_fecha_hasta: Fin rango DD-MM-YYYY (opcional)
            paginacion_num_serie: Para paginación (opcional)
            paginacion_fecha: Para paginación (opcional)
        
        Returns:
            Dict con data (lista de facturas) y paginacion (S/N)
        """
        data = {
            "ejercicio": ejercicio,
            "periodo": periodo
        }
        
        if serie and numero:
            data["serie"] = serie
            data["numero"] = numero
        
        if fecha_expedicion:
            data["fecha_expedicion"] = fecha_expedicion
        elif rango_fecha_desde and rango_fecha_hasta:
            data["rango_fecha_expedicion"] = {
                "desde": rango_fecha_desde,
                "hasta": rango_fecha_hasta
            }
        
        if paginacion_num_serie and paginacion_fecha:
            data["paginacion"] = {
                "num_serie": paginacion_num_serie,
                "fecha_expedicion": paginacion_fecha
            }
        
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            response = await client.post(
                f"{self.BASE_URL}/verifactu/list",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    async def download_xml(
        self,
        serie: str,
        numero: str
    ) -> list[Dict[str, Any]]:
        """
        Descarga los XMLs (request y response) de una factura
        
        Args:
            serie: Serie de la factura
            numero: Número de la factura
        
        Returns:
            Lista de objetos con uuid, operacion, xml_req y xml_res
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/verifactu/downloadXML",
                headers=self.headers,
                json={
                    "serie": serie,
                    "numero": numero
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def export_xmls(
        self,
        ejercicio: str,
        periodo: str,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exporta XMLs en lote (hasta 500 URLs)
        
        Args:
            ejercicio: Año
            periodo: Mes
            token: Token de paginación (opcional)
        
        Returns:
            Dict con urls (lista) y token (para siguiente página)
        """
        data = {
            "ejercicio": ejercicio,
            "periodo": periodo
        }
        if token:
            data["token"] = token
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/verifactu/export",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    async def get_declaracion(self) -> Dict[str, Any]:
        """
        Obtiene la declaración responsable de VeriFacti
        
        Returns:
            Dict con url de la declaración y datos del sistema
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/verifactu/declaracion",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    # Métodos síncronos para uso directo en endpoints
    def create_sync(self, factura_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Versión síncrona de create
        """
        import asyncio
        return asyncio.run(self.create(factura_data))
    
    def cancel_sync(
        self, 
        serie: str, 
        numero: str, 
        fecha_expedicion: str,
        rechazo_previo: str = "N",
        sin_registro_previo: str = "N",
        incidencia: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Versión síncrona de cancel
        """
        import asyncio
        return asyncio.run(self.cancel(
            serie, numero, fecha_expedicion, rechazo_previo, sin_registro_previo, incidencia
        ))
    
    def modify_sync(
        self, 
        factura_data: Dict[str, Any], 
        rechazo_previo: str = "N"
    ) -> Dict[str, Any]:
        """
        Versión síncrona de modify
        """
        import asyncio
        return asyncio.run(self.modify(factura_data, rechazo_previo))
    
    def status_by_factura_sync(
        self, 
        serie: str, 
        numero: str, 
        fecha_expedicion: str,
        fecha_operacion: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Versión síncrona de status_by_factura
        """
        import asyncio
        return asyncio.run(self.status_by_factura(serie, numero, fecha_expedicion, fecha_operacion))


