from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import ASESOR_EMAIL, CONTABILIDAD_EMAIL
from app.models.models import Cliente, Factura, LineaFactura, get_db
from app.services.document_service import ensure_factura_pdf, factura_pdf_public_url
from app.services.email_service import (
    send_accounting_pack,
    send_factura_copy_to_advisor,
    send_factura_to_client,
)
from app.services.whatsapp_sender import enviar_pdf_whatsapp

router = APIRouter()


class LineaFacturaCreate(BaseModel):
    descripcion: str
    cantidad: float = 1
    precio_unitario: float
    descuento_pct: float = 0
    iva_pct: float = 21


class FacturaCreate(BaseModel):
    cliente_id: int
    fecha_operacion: Optional[datetime] = None
    base_imponible: float
    iva_pct: float = 21
    irpf_pct: float = 0
    estado: str = "pendiente"
    lineas: list[LineaFacturaCreate] = []


class ClienteCreate(BaseModel):
    nif: Optional[str] = None
    nombre: str
    razon_social: Optional[str] = None
    domicilio: Optional[str] = None
    codigo_postal: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None


class FacturaSimpleCreate(BaseModel):
    cliente_nif: Optional[str] = None
    cliente_nombre: str
    cliente_email: Optional[str] = None
    cliente_telefono: Optional[str] = None
    cliente_domicilio: Optional[str] = None
    concepto: str
    base_imponible: float
    iva_pct: float = 21
    irpf_pct: float = 0
    estado: str = "pendiente"


def _get_factura_or_404(db: Session, factura_id: int) -> Factura:
    factura = db.query(Factura).filter(Factura.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return factura


def _get_cliente_or_404(db: Session, cliente_id: int) -> Cliente:
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


def _serialize_factura(db: Session, factura: Factura) -> dict:
    cliente = factura.cliente or db.query(Cliente).filter(Cliente.id == factura.cliente_id).first()

    pdf_path = factura.pdf_path
    pdf_url = factura_pdf_public_url(factura.id) if cliente else None
    if cliente:
        pdf_path = ensure_factura_pdf(db, factura, cliente)
        pdf_url = factura_pdf_public_url(factura.id)

    return {
        "id": factura.id,
        "numero": factura.numero,
        "serie": factura.serie,
        "anno": factura.anno,
        "cliente_id": factura.cliente_id,
        "cliente_nombre": cliente.nombre if cliente else None,
        "cliente_email": cliente.email if cliente else None,
        "cliente_telefono": cliente.telefono if cliente else None,
        "fecha_emision": factura.fecha_emision.isoformat() if factura.fecha_emision else None,
        "fecha_operacion": factura.fecha_operacion.isoformat() if factura.fecha_operacion else None,
        "base_imponible": factura.base_imponible,
        "iva_pct": factura.iva_pct,
        "iva_cuota": factura.iva_cuota,
        "irpf_pct": factura.irpf_pct,
        "irpf_cuota": factura.irpf_cuota,
        "total": factura.total,
        "estado": factura.estado,
        "pdf_path": pdf_path,
        "pdf_url": pdf_url,
        "verifactu_enviada": factura.verifactu_enviada,
        "verifactu_fecha": factura.verifactu_fecha.isoformat() if factura.verifactu_fecha else None,
    }


def _next_invoice_number(db: Session, serie: str) -> str:
    ultimo = (
        db.query(Factura)
        .filter(Factura.serie == serie)
        .order_by(Factura.anno.desc(), Factura.id.desc())
        .first()
    )
    if not ultimo or not ultimo.numero:
        return "1"
    try:
        return str(int(ultimo.numero) + 1)
    except ValueError:
        return str(ultimo.id + 1)


@router.post("/")
def crear_factura(payload: FacturaCreate, db: Session = Depends(get_db)):
    cliente = _get_cliente_or_404(db, payload.cliente_id)

    base = float(payload.base_imponible)
    iva_pct = float(payload.iva_pct)
    irpf_pct = float(payload.irpf_pct)
    iva_cuota = round(base * iva_pct / 100, 2)
    irpf_cuota = round(base * irpf_pct / 100, 2)
    total = round(base + iva_cuota - irpf_cuota, 2)

    factura = Factura(
        numero=_next_invoice_number(db, "FI"),
        serie="FI",
        cliente_id=cliente.id,
        fecha_emision=datetime.utcnow(),
        fecha_operacion=payload.fecha_operacion or datetime.utcnow(),
        base_imponible=base,
        iva_pct=iva_pct,
        iva_cuota=iva_cuota,
        irpf_pct=irpf_pct,
        irpf_cuota=irpf_cuota,
        total=total,
        estado=payload.estado,
    )
    db.add(factura)
    db.flush()

    for index, linea in enumerate(payload.lineas, start=1):
        base_linea = round(linea.cantidad * linea.precio_unitario * (1 - linea.descuento_pct / 100), 2)
        iva_linea = round(base_linea * linea.iva_pct / 100, 2)
        total_linea = round(base_linea + iva_linea, 2)
        db.add(
            LineaFactura(
                factura_id=factura.id,
                numero_linea=index,
                descripcion=linea.descripcion,
                cantidad=linea.cantidad,
                precio_unitario=linea.precio_unitario,
                descuento_pct=linea.descuento_pct,
                base_imponible=base_linea,
                iva_pct=linea.iva_pct,
                iva_cuota=iva_linea,
                total=total_linea,
            )
        )

    db.commit()
    db.refresh(factura)
    return _serialize_factura(db, factura)


@router.get("/")
def listar_facturas(
    skip: int = 0, 
    limit: int = 20, 
    buscar: Optional[str] = Query(default=None, description="Buscar por cliente o número"),
    estado: Optional[str] = Query(default=None, description="Filtrar por estado"),
    db: Session = Depends(get_db)
):
    query = db.query(Factura)
    if buscar:
        buscar = f"%{buscar}%"
        query = query.join(Cliente).filter(
            (Cliente.nombre.ilike(buscar)) | 
            (Factura.serie.ilike(buscar)) |
            (Factura.numero.ilike(buscar))
        )
    if estado:
        query = query.filter(Factura.estado == estado)
    
    total = query.count()
    facturas = query.order_by(Factura.fecha_emision.desc(), Factura.id.desc()).offset(skip).limit(limit).all()
    
    return {
        "facturas": [_serialize_factura(db, factura) for factura in facturas],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/clientes")
def crear_cliente(payload: ClienteCreate, db: Session = Depends(get_db)):
    existing = None
    if payload.nif:
        existing = db.query(Cliente).filter(Cliente.nif == payload.nif).first()
    if existing:
        return {"id": existing.id, "nombre": existing.nombre, "updated": False}
    
    cliente = Cliente(
        nif=payload.nif,
        nombre=payload.nombre,
        razon_social=payload.razon_social,
        domicilio=payload.domicilio,
        codigo_postal=payload.codigo_postal,
        ciudad=payload.ciudad,
        provincia=payload.provincia,
        email=payload.email,
        telefono=payload.telefono,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return {"id": cliente.id, "nombre": cliente.nombre, "updated": True}


@router.get("/clientes")
def listar_clientes(buscar: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Cliente)
    if buscar:
        query = query.filter(Cliente.nombre.ilike(f"%{buscar}%"))
    clientes = query.order_by(Cliente.nombre).limit(50).all()
    return [{"id": c.id, "nif": c.nif, "nombre": c.nombre, "email": c.email, "telefono": c.telefono} for c in clientes]


@router.post("/simple")
def crear_factura_simple(payload: FacturaSimpleCreate, db: Session = Depends(get_db)):
    cliente = None
    if payload.cliente_nif:
        cliente = db.query(Cliente).filter(Cliente.nif == payload.cliente_nif).first()
    
    if not cliente and payload.cliente_email:
        cliente = db.query(Cliente).filter(Cliente.email == payload.cliente_email).first()
    
    if not cliente:
        cliente = Cliente(
            nif=payload.cliente_nif,
            nombre=payload.cliente_nombre,
            domicilio=payload.cliente_domicilio,
            email=payload.cliente_email,
            telefono=payload.cliente_telefono,
        )
        db.add(cliente)
        db.flush()
    
    base = float(payload.base_imponible)
    iva_pct = float(payload.iva_pct)
    irpf_pct = float(payload.irpf_pct)
    iva_cuota = round(base * iva_pct / 100, 2)
    irpf_cuota = round(base * irpf_pct / 100, 2)
    total = round(base + iva_cuota - irpf_cuota, 2)

    factura = Factura(
        numero=_next_invoice_number(db, "FI"),
        serie="FI",
        cliente_id=cliente.id,
        fecha_emision=datetime.utcnow(),
        fecha_operacion=datetime.utcnow(),
        base_imponible=base,
        iva_pct=iva_pct,
        iva_cuota=iva_cuota,
        irpf_pct=irpf_pct,
        irpf_cuota=irpf_cuota,
        total=total,
        estado=payload.estado,
    )
    db.add(factura)
    db.flush()

    db.add(LineaFactura(
        factura_id=factura.id,
        numero_linea=1,
        descripcion=payload.concepto,
        cantidad=1,
        precio_unitario=base,
        descuento_pct=0,
        base_imponible=base,
        iva_pct=iva_pct,
        iva_cuota=iva_cuota,
        total=total,
    ))

    db.commit()
    db.refresh(factura)
    return _serialize_factura(db, factura)


@router.get("/exportar")
def exportar_facturas(
    anno: Optional[int] = Query(default=None),
    formato: str = Query(default="csv", description="csv o excel"),
    db: Session = Depends(get_db)
):
    anno = anno or datetime.utcnow().year
    facturas = db.query(Factura).filter(Factura.anno == anno).order_by(Factura.fecha_emision).all()
    
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Número", "Fecha", "Cliente", "NIF", "Base", "IVA", "IRPF", "Total", "Estado"])
    
    for factura in facturas:
        cliente = factura.cliente or _get_cliente_or_404(db, factura.cliente_id)
        writer.writerow([
            f"{factura.serie}-{factura.numero}",
            factura.fecha_emision.strftime("%Y-%m-%d") if factura.fecha_emision else "",
            cliente.nombre,
            cliente.nif or "",
            factura.base_imponible,
            factura.iva_cuota,
            factura.irpf_cuota,
            factura.total,
            factura.estado,
        ])
    
    output.seek(0)
    
    filename = f"facturas_{anno}.{formato}"
    content = output.getvalue()
    
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/{factura_id}")
def obtener_factura(factura_id: int, db: Session = Depends(get_db)):
    factura = _get_factura_or_404(db, factura_id)
    return _serialize_factura(db, factura)


@router.patch("/{factura_id}/estado")
def actualizar_estado_factura(
    factura_id: int,
    estado: str = Query(..., description="Nuevo estado"),
    db: Session = Depends(get_db)
):
    factura = _get_factura_or_404(db, factura_id)
    factura.estado = estado
    db.commit()
    db.refresh(factura)
    return {"ok": True, "estado": factura.estado}


@router.put("/{factura_id}")
def actualizar_factura(
    factura_id: int,
    base_imponible: Optional[float] = None,
    iva_pct: Optional[float] = None,
    irpf_pct: Optional[float] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db)
):
    factura = _get_factura_or_404(db, factura_id)
    
    if base_imponible is not None:
        factura.base_imponible = base_imponible
    if iva_pct is not None:
        factura.iva_pct = iva_pct
    if irpf_pct is not None:
        factura.irpf_pct = irpf_pct
    if estado is not None:
        factura.estado = estado
    
    # Recalcular totales
    factura.iva_cuota = round(factura.base_imponible * factura.iva_pct / 100, 2)
    factura.irpf_cuota = round(factura.base_imponible * factura.irpf_pct / 100, 2)
    factura.total = round(factura.base_imponible + factura.iva_cuota - factura.irpf_cuota, 2)
    
    db.commit()
    db.refresh(factura)
    return _serialize_factura(db, factura)


@router.get("/{factura_id}/pdf")
def descargar_pdf(factura_id: int, db: Session = Depends(get_db)):
    factura = _get_factura_or_404(db, factura_id)
    cliente = factura.cliente or _get_cliente_or_404(db, factura.cliente_id)
    pdf_path = ensure_factura_pdf(db, factura, cliente)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"factura_{factura.serie}{factura.numero}.pdf",
    )


@router.post("/{factura_id}/enviar-email")
def enviar_factura_email(
    factura_id: int,
    email: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    factura = _get_factura_or_404(db, factura_id)
    cliente = factura.cliente or _get_cliente_or_404(db, factura.cliente_id)
    destinatario = (email or cliente.email or "").strip()
    if not destinatario:
        raise HTTPException(status_code=400, detail="No hay email configurado para el cliente")

    pdf_path = ensure_factura_pdf(db, factura, cliente)
    result = send_factura_to_client(
        cliente_email=destinatario,
        factura=factura,
        cliente_nombre=cliente.nombre,
        pdf_path=pdf_path,
        pdf_url=factura_pdf_public_url(factura.id),
    )
    return {
        "ok": True,
        "mode": result.get("mode"),
        "to": destinatario,
        "pdf_path": pdf_path,
        "pdf_url": factura_pdf_public_url(factura.id),
        "result": result,
    }


@router.post("/{factura_id}/enviar-asesor")
def enviar_factura_asesor(
    factura_id: int,
    email: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    factura = _get_factura_or_404(db, factura_id)
    cliente = factura.cliente or _get_cliente_or_404(db, factura.cliente_id)
    destinatario = (email or ASESOR_EMAIL or "").strip()
    if not destinatario:
        raise HTTPException(status_code=400, detail="No hay email del asesor configurado")

    pdf_path = ensure_factura_pdf(db, factura, cliente)
    from app.services import email_service as email_service_module

    original_asesor = email_service_module.ASESOR_EMAIL
    email_service_module.ASESOR_EMAIL = destinatario
    try:
        result = send_factura_copy_to_advisor(
            factura=factura,
            cliente_nombre=cliente.nombre,
            pdf_path=pdf_path,
            pdf_url=factura_pdf_public_url(factura.id),
        )
    finally:
        email_service_module.ASESOR_EMAIL = original_asesor
    return {
        "ok": True,
        "mode": result.get("mode"),
        "to": destinatario,
        "pdf_path": pdf_path,
        "result": result,
    }


@router.get("/{factura_id}/whatsapp-link")
def obtener_whatsapp_link(
    factura_id: int,
    telefono: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    factura = _get_factura_or_404(db, factura_id)
    cliente = factura.cliente or _get_cliente_or_404(db, factura.cliente_id)
    destino = (telefono or cliente.telefono or "").strip()
    if not destino:
        raise HTTPException(status_code=400, detail="No hay teléfono configurado para el cliente")

    ensure_factura_pdf(db, factura, cliente)
    pdf_url = factura_pdf_public_url(factura.id)
    caption = f"Factura {factura.serie}-{factura.numero} de {cliente.nombre}. Puedes descargar el PDF aquí: {pdf_url}"
    result = enviar_pdf_whatsapp(to_number=destino, pdf_url=pdf_url, caption=caption)
    return {
        "ok": True,
        "to": destino,
        "pdf_url": pdf_url,
        "share_url": result["share_url"],
        "caption": caption,
    }


@router.post("/informes/contabilidad")
def enviar_informe_contabilidad(
    anno: Optional[int] = Query(default=None),
    mes: Optional[int] = Query(default=None),
    email: Optional[str] = Query(default=None),
    asesor_email: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    anno = anno or datetime.utcnow().year
    query = db.query(Factura).filter(Factura.anno == anno)
    if mes:
        query = query.filter(Factura.fecha_emision.isnot(None))
        facturas = [factura for factura in query.all() if factura.fecha_emision and factura.fecha_emision.month == mes]
    else:
        facturas = query.all()

    if not facturas:
        raise HTTPException(status_code=404, detail="No hay facturas para el período solicitado")

    enriched = []
    for factura in facturas:
        cliente = factura.cliente or _get_cliente_or_404(db, factura.cliente_id)
        pdf_path = ensure_factura_pdf(db, factura, cliente)
        enriched.append((factura, cliente, pdf_path))

    contabilidad_email = (email or CONTABILIDAD_EMAIL or "").strip()
    if not contabilidad_email:
        raise HTTPException(status_code=400, detail="No hay email de contabilidad configurado")

    from app.services import email_service as email_service_module

    original_contabilidad = email_service_module.CONTABILIDAD_EMAIL
    original_asesor = email_service_module.ASESOR_EMAIL
    email_service_module.CONTABILIDAD_EMAIL = contabilidad_email
    email_service_module.ASESOR_EMAIL = (asesor_email or ASESOR_EMAIL or "").strip()
    try:
        result = send_accounting_pack(
            facturas=[item[0] for item in enriched],
            periodo=f"{anno}-{mes:02d}" if mes else str(anno),
            pdf_paths=[item[2] for item in enriched],
        )
    finally:
        email_service_module.CONTABILIDAD_EMAIL = original_contabilidad
        email_service_module.ASESOR_EMAIL = original_asesor

    return {
        "ok": True,
        "result": {
            "report_path": result.get("report_path"),
            "accounting": result.get("results", {}).get("contabilidad"),
            "advisor": result.get("results", {}).get("asesor"),
            "success": result.get("success", False),
        },
    }
