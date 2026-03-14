from urllib.parse import quote


def enviar_pdf_whatsapp(*, to_number: str, pdf_url: str, caption: str) -> dict:
    clean = "".join(ch for ch in str(to_number or "") if ch.isdigit())
    if not clean:
        return {"success": False, "error": "Teléfono no válido"}
    message = f"{caption}\n\nDescarga PDF: {pdf_url}"
    url = f"https://wa.me/{clean}?text={quote(message)}"
    return {"success": True, "message": "Enlace de WhatsApp preparado", "share_url": url}
