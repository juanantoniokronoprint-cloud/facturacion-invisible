"""
Servicio de Telegram Bot
Procesa mensajes y los convierte en facturas
"""
import os
import re
import logging
from openai import OpenAI
from app.config import OPENAI_API_KEY
from app.models.models import SessionLocal, Cliente, Factura
from app.services.generador_factura import generar_pdf_factura
from datetime import datetime

client = OpenAI(api_key=OPENAI_API_KEY)
logger = logging.getLogger(__name__)

# Prompt para extraer datos de factura
FACTURA_PROMPT = """Extrae los datos de esta factura desde el mensaje del usuario.

Mensaje: "{mensaje}"

Responde en JSON con:
{{
    "cliente_nombre": "nombre del cliente",
    "cliente_nif": "NIF del cliente (X1234567A formato español)",
    "concepto": "descripción del trabajo/servicio",
    "importe": 500.00,
    "iva": 21,
    "irpf": 0,
    "fecha": "2026-03-12" (hoy si no se especifica)
}}

Si no puedes extraer algún dato, usa null."""

async def process_update(update):
    """Procesa un update de Telegram"""
    if not update.message:
        return
    
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    text = update.message.text
    
    if text == "/start":
        await update.message.reply_text(
            "¡Hola! Soy tu asistente de facturación.\n\n"
            "Dime qué has cobrado, por ejemplo:\n"
            '"Cobré 500€ de Juan García por diseño de logo"\n\n'
            "¡Y yo genero la factura!"
        )
        return
    
    if text == "/ayuda":
        await update.message.reply_text(
            "Cómo usar:\n"
            "1. Dime qué has cobrado: 'Cobré 500€ de Empresa X por servicio Y'\n"
            "2. Te pregunto los datos que falten\n"
            "3. Genero la factura en PDF\n\n"
            "Comandos:\n"
            "/start - Bienvenida\n"
            "/facturas - Ver mis facturas\n"
            "/ayuda - Esta ayuda"
        )
        return
    
    if text == "/facturas":
        await mostrar_facturas(chat_id, user_id)
        return
    
    # Procesar como factura
    await procesar_factura(update, text, chat_id)

async def procesar_factura(update, texto: str, chat_id: int):
    """Usa GPT para extraer datos y crear factura"""
    try:
        # Llamar a OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": FACTURA_PROMPT},
                {"role": "user", "content": texto}
            ],
            response_format={"type": "json_object"}
        )
        
        import json
        datos = json.loads(response.choices[0].message.content)
        
        await update.message.reply_text(
            f"📋 Datos extraídos:\n"
            f"Cliente: {datos.get('cliente_nombre', 'N/A')}\n"
            f"NIF: {datos.get('cliente_nif', 'N/A')}\n"
            f"Concepto: {datos.get('concepto', 'N/A')}\n"
            f"Importe: {datos.get('importe', 0)}€\n"
            f"IVA: {datos.get('iva', 21)}%\n"
            f"IRPF: {datos.get('irpf', 0)}%\n\n"
            f"¿Correcto? Responde 'sí' para generar factura."
        )
        
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def mostrar_facturas(chat_id: int, user_id: int):
    """Muestra las facturas del usuario"""
    db = SessionLocal()
    try:
        # Por ahora muestra todas
        facturas = db.query(Factura).limit(10).all()
        if not facturas:
            return "No tienes facturas aún."

        texto = "📄 Tus facturas:\n\n"
        for f in facturas:
            texto += f"{f.serie}-{f.numero} | {f.fecha_emision.strftime('%d/%m/%Y') if f.fecha_emision else 'N/A'} | {f.total}€ | {f.estado}\n"
        return texto
    finally:
        db.close()
