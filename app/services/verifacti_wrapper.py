"""
Wrapper para VeriFacti usando el cliente copiado del ERP
"""
import asyncio
from app.config import VERIFACTI_API_KEY, VERIFACTI_SEND_MODE
from app.services.verifacti_client import VeriFactiClient

async def enviar_factura_verifacti(factura, cliente, tipo_factura="F1") -> dict:
    """Envía una factura a VeriFacti"""
    if VERIFACTI_SEND_MODE != "live":
        return {"success": True, "status": "demo", "message": "Modo demo - factura no enviada a VeriFacti"}

    if not VERIFACTI_API_KEY:
        return {"success": False, "status": "error", "message": "API key VeriFacti no configurada"}
    
    client = VeriFactiClient(VERIFACTI_API_KEY)
    
    try:
        # Transformar al formato VeriFactu
        from app.services.verifacti_transformer import transformar_factura_verifactu
        factura_data = transformar_factura_verifactu(factura, cliente, tipo_factura)
        
        response = await client.create(factura_data)
        return {"success": True, "status": "ok", **response}
    except Exception as e:
        return {"success": False, "status": "error", "message": str(e)}

async def verificar_api_key() -> dict:
    """Verifica si la API key es válida"""
    if not VERIFACTI_API_KEY:
        return {"status": "error", "message": "API key no configurada"}
    
    client = VeriFactiClient(VERIFACTI_API_KEY)
    
    try:
        result = await client.health()
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
