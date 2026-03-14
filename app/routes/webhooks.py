from fastapi import APIRouter, Request
from telegram import Update
from telegram.ext import Application, ContextTypes
from app.services.telegram_bot import process_update
from app.services.whatsapp_handler import process_whatsapp_message, transcribe_audio
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/telegram")
async def telegram_webhook(request: Request):
    """Webhook para Telegram Bot"""
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, bot=None)
        await process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"ok": False, "error": str(e)}

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """Webhook para WhatsApp - mensajes del bridge ERP"""
    try:
        data = await request.json()
        from_number = data.get("from", "")
        
        # Verificar si es mensaje de voz
        audio_url = data.get("audio", {}).get("url") or data.get("voice", {}).get("url")
        
        if audio_url:
            logger.info(f"WhatsApp voice message from {from_number}")
            # Transcribir audio
            text = await transcribe_audio(audio_url)
            if not text:
                return {"ok": False, "response": {"response": "❌ No pude transcribir el audio. Intenta enviar el mensaje como texto."}}
            logger.info(f"Transcribed: {text[:50]}...")
        else:
            text = data.get("text", "")
            logger.info(f"WhatsApp received from {from_number}: {text[:50]}...")
        
        response = await process_whatsapp_message(from_number, text)
        return {"ok": True, "response": response}
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        return {"ok": False, "error": str(e)}
