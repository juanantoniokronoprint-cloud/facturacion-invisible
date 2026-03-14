"""
Generador de facturas PDF con VeriFactu
"""
import hashlib
import json
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import cm
from datetime import datetime
import qrcode
import os

def generar_qr_verifactu(factura, cliente):
    """Genera QR con datos VeriFactu para verificar en AEAT"""
    
    # Datos para el QR (estructura simplificada parademo)
    fecha = factura.fecha_emision.strftime('%Y-%m-%d') if factura.fecha_emision else datetime.now().strftime('%Y-%m-%d')
    
    # Crear contenido del QR
    qr_data = {
        "serie": factura.serie,
        "numero": factura.numero,
        "fecha": fecha,
        "nif": cliente.nif or "",
        "nombre": cliente.nombre,
        "base": factura.base_imponible,
        "iva": factura.iva_cuota,
        "total": factura.total
    }
    
    # Generar hash de verificación (simulado para demo)
    contenido = f"{factura.serie}{factura.numero}{fecha}{cliente.nif or ''}{factura.total}"
    hash_verificacion = hashlib.sha256(contenido.encode()).hexdigest()[:20]
    
    # URL de verificación (demo - en producción apunta a AEAT)
    url_verificacion = f"https://sede.agenciatributaria.gob.es/Sede/Verifica?h={hash_verificacion}"
    
    # Crear QR
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url_verificacion)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Guardar en buffer
    buffer = BytesIO()
    img.save(buffer)
    buffer.seek(0)
    
    return buffer, hash_verificacion


def generar_pdf_factura(factura, cliente, emisor=None, output_path=None, enviar_aeat=False):
    """Genera un PDF de factura con VeriFactu"""
    
    if emisor is None:
        emisor = {}
    
    if output_path is None:
        output_path = f"/tmp/factura_{factura.serie}{factura.numero}.pdf"
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    # Contenido
    elements = []
    
    # === DATOS DEL EMISOR (Art. 6 RG FAT) ===
    emisor_nif = emisor.get('nif', '00000000T')
    emisor_nombre = emisor.get('nombre', 'Facturación Invisible')
    emisor_domicilio = emisor.get('domicilio', 'Calle Mayor 1')
    emisor_cp = emisor.get('cp', '46001')
    emisor_poblacion = emisor.get('poblacion', 'Valencia')
    emisor_provincia = emisor.get('provincia', 'Valencia')
    
    # Bloque emisor
    emisor_style = ParagraphStyle('Emisor', fontSize=9, textColor=colors.darkgrey)
    elements.append(Paragraph(f"<b>EMISOR:</b> {emisor_nif} - {emisor_nombre}", emisor_style))
    elements.append(Paragraph(f"{emisor_domicilio} - {emisor_cp} {emisor_poblacion} ({emisor_provincia})", emisor_style))
    elements.append(Spacer(1, 15))
    
    # Título
    elements.append(Paragraph("FACTURA", title_style))
    elements.append(Spacer(1, 20))
    
    # Datos de la factura
    fecha = factura.fecha_emision.strftime('%d/%m/%Y') if factura.fecha_emision else 'N/A'
    fecha_operacion = getattr(factura, 'fecha_operacion', None)
    fecha_op_str = fecha_operacion.strftime('%d/%m/%Y') if fecha_operacion else fecha
    
    table_data = [
        ['Número:', f"{factura.serie}-{factura.numero}"],
        ['Fecha expedición:', fecha],
        ['Fecha operación:', fecha_op_str],
        ['Cliente:', cliente.nombre],
        ['NIF:', cliente.nif or 'N/A'],
    ]
    
    t = Table(table_data, colWidths=[3*cm, 12*cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # Líneas de la factura (detalle de conceptos)
    if hasattr(factura, 'lineas') and factura.lineas:
        # Cabecera de la tabla
        lineas_data = [['Descripción', 'Cant.', 'P.Unitario', 'Base', 'IVA', 'Total']]
        
        for linea in factura.lineas:
            lineas_data.append([
                linea.descripcion or 'Sin descripción',
                f"{linea.cantidad:.2f}",
                f"{linea.precio_unitario:.2f} €",
                f"{linea.base_imponible:.2f} €",
                f"{linea.iva_pct}%",
                f"{linea.total:.2f} €"
            ])
        
        lt = Table(lineas_data, colWidths=[7*cm, 1.5*cm, 2*cm, 2*cm, 1.5*cm, 2*cm])
        lt.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (1, 0), (5, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(lt)
        elements.append(Spacer(1, 20))
    
    # Totales
    totales_data = [
        ['Base Imponible', f"{factura.base_imponible:.2f} €"],
        [f"IVA ({factura.iva_pct}%)", f"{factura.iva_cuota:.2f} €"],
    ]
    
    if factura.irpf_pct > 0:
        totales_data.append([f"IRPF ({factura.irpf_pct}%)", f"-{factura.irpf_cuota:.2f} €"])
    
    totales_data.append(['TOTAL', f"{factura.total:.2f} €"])
    
    tt = Table(totales_data, colWidths=[12*cm, 4*cm])
    tt.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(tt)
    elements.append(Spacer(1, 30))
    
    # QR VeriFactu
    qr_buffer, hash_verificacion = generar_qr_verifactu(factura, cliente)
    
    # Guardar QR temporalmente
    qr_path = f"/tmp/qr_{factura.serie}{factura.numero}.png"
    with open(qr_path, 'wb') as f:
        f.write(qr_buffer.getvalue())
    
    # Añadir QR al PDF
    qr_img = Image(qr_path, width=4*cm, height=4*cm)
    elements.append(qr_img)
    
    # Leyenda VeriFactu
    elements.append(Spacer(1, 10))
    verifactu_style = ParagraphStyle(
        'VeriFactu',
        fontSize=8,
        textColor=colors.gray,
        alignment=1
    )
    elements.append(Paragraph("VERI*FACTU - Factura verifiable en la sede electrónica de la AEAT", verifactu_style))
    elements.append(Paragraph(f"Hash: {hash_verificacion}", verifactu_style))
    
    if enviar_aeat:
        elements.append(Paragraph("Esta factura ha sido comunicada a la AEAT", verifactu_style))
    
    # Construir PDF
    doc.build(elements)
    
    # Limpiar QR temporal
    if os.path.exists(qr_path):
        os.remove(qr_path)
    
    return output_path
