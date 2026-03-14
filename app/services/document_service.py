from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.config import PDF_STORAGE_DIR, PUBLIC_BASE_URL, REPORT_STORAGE_DIR, EMISOR_NIF, EMISOR_NOMBRE, EMISOR_DOMICILIO, EMISOR_CP, EMISOR_POBLACION, EMISOR_PROVINCIA
from app.services.generador_factura import generar_pdf_factura


def factura_filename(factura) -> str:
    return f"factura_{factura.serie}-{factura.numero}.pdf"


def factura_pdf_path(factura) -> Path:
    return PDF_STORAGE_DIR / factura_filename(factura)


def factura_pdf_public_url(factura_id: int) -> str:
    return f"{PUBLIC_BASE_URL}/api/facturas/{factura_id}/pdf"


def get_emisor_data() -> dict:
    """Obtiene los datos del emisor para el PDF"""
    return {
        "nif": EMISOR_NIF,
        "nombre": EMISOR_NOMBRE,
        "domicilio": EMISOR_DOMICILIO,
        "cp": EMISOR_CP,
        "poblacion": EMISOR_POBLACION,
        "provincia": EMISOR_PROVINCIA
    }


def ensure_factura_pdf(db, factura, cliente) -> str:
    path = factura_pdf_path(factura)
    if not path.exists():
        emisor = get_emisor_data()
        generar_pdf_factura(factura, cliente, emisor, str(path))
    if factura.pdf_path != str(path):
        factura.pdf_path = str(path)
        db.add(factura)
        db.commit()
        db.refresh(factura)
    return str(path)


def accounting_report_path(periodo: str) -> Path:
    safe_period = periodo.replace("/", "-").replace(" ", "_")
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    return REPORT_STORAGE_DIR / f"informe_contabilidad_{safe_period}_{stamp}.pdf"
