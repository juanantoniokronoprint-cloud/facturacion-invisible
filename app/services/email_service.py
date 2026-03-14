from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config import ASESOR_EMAIL, CONTABILIDAD_EMAIL, GOG_ACCOUNT, OUTBOX_DIR
from app.services.document_service import accounting_report_path


def _normalize_emails(values: Iterable[str] | None) -> list[str]:
    emails: list[str] = []
    for value in values or []:
        if not value:
            continue
        for item in str(value).split(","):
            email = item.strip()
            if email and email not in emails:
                emails.append(email)
    return emails


def _write_outbox(payload: dict) -> dict:
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    path = OUTBOX_DIR / f"{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "message": f"Guardado en outbox: {path}", "outbox_path": str(path), "mode": "outbox"}


def send_email(
    *,
    to_emails: Iterable[str],
    subject: str,
    body: str,
    attachments: Iterable[str] | None = None,
    cc_emails: Iterable[str] | None = None,
    bcc_emails: Iterable[str] | None = None,
) -> dict:
    to_list = _normalize_emails(to_emails)
    cc_list = _normalize_emails(cc_emails)
    bcc_list = _normalize_emails(bcc_emails)
    attachment_list = [str(Path(p)) for p in (attachments or []) if p]

    payload = {
        "to": to_list,
        "cc": cc_list,
        "bcc": bcc_list,
        "subject": subject,
        "body": body,
        "attachments": attachment_list,
    }

    if not to_list:
        return {"success": False, "error": "No hay destinatarios"}

    if not GOG_ACCOUNT:
        return _write_outbox(payload)

    cmd = [
        "gog",
        "gmail",
        "send",
        "--account",
        GOG_ACCOUNT,
        "--to",
        ",".join(to_list),
        "--subject",
        subject,
        "--body",
        body,
    ]
    if cc_list:
        cmd.extend(["--cc", ",".join(cc_list)])
    if bcc_list:
        cmd.extend(["--bcc", ",".join(bcc_list)])
    for attachment in attachment_list:
        cmd.extend(["--attach", attachment])

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return {"success": True, "message": "Email enviado", "stdout": proc.stdout.strip(), "mode": "gmail"}

    payload["error"] = proc.stderr.strip() or proc.stdout.strip()
    fallback = _write_outbox(payload)
    fallback["warning"] = payload["error"]
    return fallback


def send_factura_to_client(*, cliente_email: str, factura, cliente_nombre: str, pdf_path: str, pdf_url: str) -> dict:
    body = (
        f"Hola {cliente_nombre},\n\n"
        f"Te enviamos la factura {factura.serie}-{factura.numero} por importe total de {factura.total:.2f} €.\n"
        f"Adjuntamos el PDF y además puedes descargarlo aquí:\n{pdf_url}\n\n"
        "Si necesitas cualquier corrección, responde a este correo.\n\n"
        "Saludos."
    )
    return send_email(
        to_emails=[cliente_email],
        subject=f"Factura {factura.serie}-{factura.numero}",
        body=body,
        attachments=[pdf_path],
    )


def send_factura_copy_to_advisor(*, factura, cliente_nombre: str, pdf_path: str, pdf_url: str) -> dict:
    if not ASESOR_EMAIL:
        return {"success": False, "error": "ASESOR_EMAIL no configurado"}
    body = (
        f"Adjuntamos copia de la factura {factura.serie}-{factura.numero} de {cliente_nombre}.\n"
        f"Importe total: {factura.total:.2f} €.\n"
        f"Descarga directa: {pdf_url}\n"
    )
    return send_email(
        to_emails=[ASESOR_EMAIL],
        subject=f"Copia factura {factura.serie}-{factura.numero}",
        body=body,
        attachments=[pdf_path],
    )


def build_accounting_report(*, facturas: list, periodo: str) -> str:
    path = accounting_report_path(periodo)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    total_base = sum(f.base_imponible for f in facturas)
    total_iva = sum(f.iva_cuota for f in facturas)
    total_irpf = sum(f.irpf_cuota for f in facturas)
    total = sum(f.total for f in facturas)

    elements = [
        Paragraph(f"Informe de facturación {periodo}", styles["Title"]),
        Spacer(1, 14),
        Paragraph(f"Facturas incluidas: {len(facturas)}", styles["BodyText"]),
        Spacer(1, 8),
    ]

    table_data = [["Factura", "Cliente", "Base", "IVA", "IRPF", "Total"]]
    for factura in facturas:
        cliente = factura.cliente.nombre if factura.cliente else "Cliente"
        table_data.append(
            [
                f"{factura.serie}-{factura.numero}",
                cliente,
                f"{factura.base_imponible:.2f} €",
                f"{factura.iva_cuota:.2f} €",
                f"{factura.irpf_cuota:.2f} €",
                f"{factura.total:.2f} €",
            ]
        )
    table_data.extend(
        [
            ["", "", "", "", "", ""],
            ["TOTAL", "", f"{total_base:.2f} €", f"{total_iva:.2f} €", f"{total_irpf:.2f} €", f"{total:.2f} €"],
        ]
    )
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return str(path)


def send_accounting_pack(*, facturas: list, periodo: str, pdf_paths: list[str]) -> dict:
    to_accounting = _normalize_emails([CONTABILIDAD_EMAIL])
    to_advisor = _normalize_emails([ASESOR_EMAIL])
    report_path = build_accounting_report(facturas=facturas, periodo=periodo)
    results = {}
    if to_accounting:
        results["contabilidad"] = send_email(
            to_emails=to_accounting,
            subject=f"Informe de facturación {periodo}",
            body=f"Adjuntamos el informe de facturación del periodo {periodo} y los PDFs asociados.",
            attachments=[report_path, *pdf_paths],
        )
    if to_advisor:
        results["asesor"] = send_email(
            to_emails=to_advisor,
            subject=f"Copias de facturas {periodo}",
            body=f"Adjuntamos las copias de los PDFs de facturas del periodo {periodo}.",
            attachments=pdf_paths,
        )
    return {"success": bool(results), "report_path": report_path, "results": results}
