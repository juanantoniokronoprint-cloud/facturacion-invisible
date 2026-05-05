"""
Servicio de WhatsApp para Facturación Invisible
Procesa mensajes derivados desde el bridge del ERP
"""
import os
import json
import logging
import re
from datetime import datetime
from openai import OpenAI
from app.config import (
    OPENAI_API_KEY, EMISOR_NIF, EMISOR_NOMBRE, 
    EMISOR_DOMICILIO, EMISOR_CP, EMISOR_POBLACION, EMISOR_PROVINCIA,
    EMISOR_CLAVE_REGIMEN, TELEFONOS_AUTORIZADOS
)
from app.models.models import SessionLocal, Cliente, Factura
from app.services.document_service import ensure_factura_pdf, factura_pdf_public_url
from app.services.email_service import send_factura_copy_to_advisor, send_factura_to_client
from app.services.verifacti_wrapper import enviar_factura_verifacti

logger = logging.getLogger(__name__)


NIF_CIF_PATTERN = re.compile(
    r"^("
    r"\d{8}[A-Z]|"  # DNI/NIF persona física
    r"[XYZ]\d{7}[A-Z]|"  # NIE
    r"[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]"  # CIF/NIF entidad
    r")$"
)


def es_nif_cif_valido(valor: str | None) -> bool:
    """Valida formato básico de NIF/NIE/CIF español sin calcular letra de control."""
    if not valor:
        return False
    return bool(NIF_CIF_PATTERN.match(str(valor).upper().strip()))


def normalizar_telefono(telefono: str) -> str:
    """Normaliza un número de teléfono: elimina +, espacios, guiones, etc."""
    return ''.join(c for c in telefono if c.isdigit())


def is_telefono_autorizado(telefono: str) -> bool:
    """Verifica si un teléfono está autorizado (compara números normalizados)"""
    if not TELEFONOS_AUTORIZADOS:
        return True
    
    tel_normalizado = normalizar_telefono(telefono)
    
    for tel_auth in TELEFONOS_AUTORIZADOS.keys():
        tel_auth_normalizado = normalizar_telefono(tel_auth)
        if tel_normalizado == tel_auth_normalizado:
            return True
    return False

client = OpenAI(api_key=OPENAI_API_KEY)

# Sesiones en memoria
sesiones_facturas = {}

FACTURA_PROMPT = """Extrae los datos de esta factura desde el mensaje del usuario.

Mensaje: "{mensaje}"

Responde en JSON con:
{{
    "cliente_nif": "NIF del cliente (formato español: 8 dígitos + letra mayúscula)",
    "cliente_nombre": "Nombre completo del cliente",
    "importe": 0.0,
    "importe_incluye_iva": false,
    "iva": 21,
    "irpf": 0,
    "concepto": "Descripción del trabajo o servicio"
}}

Si el cliente NO tiene NIF o dice "sin NIF", usa cliente_nif: null.
Si dice "factura simplificada", usa cliente_nif: null.
Si el usuario dice "IVA incluido", "total con IVA" o similar, marca importe_incluye_iva: true."""


def normalizar_importe_extraido(datos: dict) -> dict:
    """Convierte importes IVA incluido a base imponible antes de calcular factura."""
    datos = dict(datos)
    importe = float(datos.get("importe", 0) or 0)
    iva_pct = float(datos.get("iva", 21) or 0)
    incluye_iva = bool(datos.get("importe_incluye_iva"))
    if incluye_iva and importe > 0 and iva_pct > 0:
        datos["total_iva_incluido_original"] = round(importe, 2)
        datos["importe"] = round(importe / (1 + iva_pct / 100), 2)
    return datos


async def process_whatsapp_message(from_number: str, text: str) -> dict:
    """Procesa mensajes de WhatsApp y determina la acción"""
    
    # Verificar teléfono autorizado
    if not is_telefono_autorizado(from_number):
        return {"response": "⛔ Teléfono no autorizado. Contacta al administrador."}
    
    text_lower = text.lower().strip()
    
    # Verificar si hay sesión activa esperando confirmación
    sesion = sesiones_facturas.get(from_number)
    if sesion and sesion.get("tipo") in ["factura", "abono", "rectificativa"]:
        # Verificar si la sesión espera NIF (está esperando confirmación de datos)
        sesion_esperando_nif = sesion.get("_esperando_nif", False)
        
        if text_lower == "sí" or text_lower == "si" or text_lower == "si, confirma" or text_lower == "confirmo":
            return await confirmar_factura(from_number, sesion)
        elif text_lower == "no" or text_lower == "cancelar":
            del sesiones_facturas[from_number]
            return {"response": "❌ Cancelado. ¿En qué puedo ayudarte?"}
        elif text_lower.startswith("nif:"):
            nif = text_lower[4:].strip().upper()
            if sesion.get("datos"):
                sesion["datos"]["cliente_nif"] = nif
                sesion["_factura_simplificada"] = False
                sesion["_esperando_nif"] = False
                return await confirmar_factura(from_number, sesion)
        elif sesion_esperando_nif:
            # El usuario responde con un NIF directamente (sin "NIF:")
            if es_nif_cif_valido(text):
                nif = text.strip().upper()
                if sesion.get("datos"):
                    sesion["datos"]["cliente_nif"] = nif
                    sesion["_factura_simplificada"] = False
                    sesion["_esperando_nif"] = False
                    return await confirmar_factura(from_number, sesion)
            elif text_lower == "sin nif" or text_lower == "sin nif." or text_lower == "no tengo nif":
                if sesion.get("datos"):
                    sesion["datos"]["cliente_nif"] = None
                    sesion["_factura_simplificada"] = True
                    sesion["_esperando_nif"] = False
                    return await confirmar_factura(from_number, sesion)
    
    # Verificar si es "sin NIF"
    if "sin nif" in text_lower or "sin NIF" in text:
        if sesion and sesion.get("datos"):
            sesion["datos"]["cliente_nif"] = None
            sesion["_factura_simplificada"] = True
            return await confirmar_factura(from_number, sesion)
    
    # Comandos de ayuda
    if text_lower in ["ayuda", "help", "menu", "comandos"]:
        return {"response": """📋 *Comandos disponibles:*

• *ft [mensaje]* - Crear factura
• *abono* - Crear abono/rectificativa
• *rectificativa* - Crear factura rectificativa
• *facturas* - Listar facturas
• *buscar [cliente]* - Buscar facturas
• *informe* - Ver informe de facturación

Ejemplo: "ft Cobré 200€ de Juan por trabajo de fontanería NIF: 12345678A"
"""}
    
    # Listar facturas
    if text_lower == "facturas" or text_lower == "ver facturas":
        return {"response": await listar_facturas(from_number)}
    
    # Informe de facturación
    if "informe" in text_lower and "factur" in text_lower:
        return {"response": await informe_facturacion(from_number)}
    
    # Buscar facturas por cliente
    if text_lower.startswith("buscar "):
        busqueda = text[7:].strip()
        return {"response": await listar_facturas(from_number, filtro=busqueda)}
    
    # Ver abonos (facturas rectificativas)
    if "abono" in text_lower or "devolución" in text_lower:
        return await crear_abono(from_number, text)
    
    if "rectificativa" in text_lower:
        return await crear_rectificativa(from_number, text)
    
    if text_lower.startswith("ft "):
        text = text[3:].strip()
    
    # Procesar como factura - llamar directamente a la función de extracción
    return await extraer_datos_factura(from_number, text)


async def extraer_datos_factura(from_number: str, texto: str) -> dict:
    """Extrae datos de factura usando GPT y guarda en sesión"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": FACTURA_PROMPT.format(mensaje=texto)},
                {"role": "user", "content": texto}
            ],
            response_format={"type": "json_object"}
        )
        
        datos = normalizar_importe_extraido(json.loads(response.choices[0].message.content))
        
        # Validar datos requeridos
        errores = []
        if not datos.get("cliente_nombre"):
            errores.append("nombre del cliente")
        if not datos.get("importe") or float(datos.get("importe", 0)) <= 0:
            errores.append("importe")
        
        if errores:
            return {"response": f"❌ No pude extraer: {', '.join(errores)}. Intenta con más detalles.\n\nEjemplo: 'ft Cobré 200€ de Juan Pérez (NIF: 12345678A) por trabajo de fontanería'"}
        
        # Validar formato NIF español (8 dígitos + letra mayúscula) o NIE
        nif = datos.get("cliente_nif")
        if nif and nif not in ["", "null", "None"]:
            nif_upper = nif.upper().strip()
            if not es_nif_cif_valido(nif_upper):
                return {"response": "❌ El NIF no tiene formato válido.\n\nFormatos válidos:\n- DNI: 8 dígitos + letra (ej: 12345678A)\n- NIE: X/Y/Z/A-W + 7 dígitos + letra (ej: X1234567A, A1234567B)\n- NIF empresa: letra + 8 dígitos (ej: B12345678)"}
        
        # Validar límite F2 (factura simplificada): máximo 400€ IVA incluido
        importe = float(datos.get("importe", 0))
        iva_pct = float(datos.get("iva", 21))
        total_con_iva = importe + (importe * iva_pct / 100)
        
        # Si no hay NIF y el total supera 400€, forzamos NIF
        if not nif or nif in ["", "null", "None"]:
            if total_con_iva > 400:
                return {"response": f"⚠️ El total ({total_con_iva:.2f}€ con IVA) supera los 400€ permitidos para factura simplificada.\n\nPara importes mayores de 400€ es obligatorio incluir el NIF del cliente.\n\nPor favor indica el NIF: 'NIF: 12345678A'"}
        
        # Guardar en sesión temporal
        nif_faltante = not datos.get("cliente_nif") or datos.get("cliente_nif") in ["", "null", "None"]
        sesiones_facturas[from_number] = {
            "tipo": "factura", 
            "datos": datos, 
            "timestamp": datetime.now().timestamp(),
            "_esperando_nif": nif_faltante
        }
        
        # Verificar NIF
        nif_faltante = not datos.get("cliente_nif") or datos.get("cliente_nif") in ["", "null", "None"]
        
        respuesta = f"📋 *Datos extraídos:*\n\n"
        respuesta += f"👤 Cliente: {datos.get('cliente_nombre', 'N/A')}\n"
        
        if nif_faltante:
            respuesta += f"📄 NIF: ⚠️ Falta\n"
        else:
            respuesta += f"📄 NIF: {datos.get('cliente_nif')}\n"
            
        respuesta += f"📝 Concepto: {datos.get('concepto', 'N/A')}\n"
        respuesta += f"💰 Base imponible: {datos.get('importe', 0)}€\n"
        if datos.get("total_iva_incluido_original"):
            respuesta += f"💶 Total indicado con IVA: {datos.get('total_iva_incluido_original')}€\n"
        respuesta += f"📊 IVA: {datos.get('iva', 21)}%\n"
        respuesta += f"📉 IRPF: {datos.get('irpf', 0)}%\n\n"
        
        if nif_faltante:
            respuesta += "⚠️ *Falta el NIF del cliente.*\nPor favor, indícalo respondiendo: 'NIF: 12345678A'\n\n"
            respuesta += "¿O confirma así si no tienes NIF (será factura simplificada)?"
        else:
            respuesta += "¿Confirmas? Responde *sí* para generar la factura."
        
        return {"response": respuesta}
        
    except Exception as e:
        logger.error(f"Error procesando factura: {e}")
        return {"response": f"❌ Error: {str(e)}"}


async def confirmar_factura(from_number: str, sesion: dict) -> dict:
    """Genera la factura confirmada"""
    try:
        datos = sesion.get("datos", {})
        tipo_operacion = sesion.get("tipo", "factura")
        
        # Calcular totales
        base = float(datos.get("importe", 0))
        iva_pct = float(datos.get("iva", 21))
        irpf_pct = float(datos.get("irpf", 0))
        iva = base * iva_pct / 100
        irpf = base * irpf_pct / 100
        total = base + iva - irpf
        
        db = SessionLocal()
        try:
            from app.models.models import Cliente, Factura
            
            cliente_autorizado = sesion.get("cliente_autorizado")
            
            # Buscar o crear cliente
            nif = datos.get("cliente_nif")
            if cliente_autorizado:
                cliente = db.query(Cliente).filter(Cliente.telefono_autorizado == from_number).first()
                if not cliente:
                    cliente = Cliente(
                        nombre=cliente_autorizado,
                        nif=nif or "",
                        email="",
                        telefono=from_number,
                        telefono_autorizado=from_number
                    )
                    db.add(cliente)
                    db.commit()
                    db.refresh(cliente)
            else:
                if nif:
                    cliente = db.query(Cliente).filter(Cliente.nif == nif).first()
                else:
                    cliente = None
                
                if not cliente:
                    cliente = Cliente(
                        nombre=datos.get("cliente_nombre", "Cliente"),
                        nif=nif or "",
                        email="",
                        telefono=from_number
                    )
                    db.add(cliente)
                    db.commit()
                    db.refresh(cliente)
            
            # Determinar serie según tipo
            if tipo_operacion == "abono":
                serie = "AB"
                tipo_factura_db = "R1"
                tipo_rectificacion_db = "I"
            elif tipo_operacion == "rectificativa":
                serie = "FR"
                tipo_factura_db = datos.get("tipo_rectificativa", "R1")
                tipo_rectificacion_db = datos.get("tipo_rectificacion", "I")
            else:
                serie = "FI"
                tipo_factura_db = "F2" if sesion.get("_factura_simplificada", False) else "F1"
                tipo_rectificacion_db = None
            
            # Obtener siguiente número
            ultimo = db.query(Factura).filter(Factura.serie == serie).order_by(Factura.numero.desc()).first()
            siguiente_num = str(int(ultimo.numero) + 1) if ultimo and ultimo.numero else "1"
            
            factura_origen_id = None
            factura_origen = sesion.get("factura_origen") or {}
            if factura_origen.get("serie") and factura_origen.get("numero"):
                origen = db.query(Factura).filter(
                    Factura.serie == factura_origen.get("serie"),
                    Factura.numero == str(factura_origen.get("numero")),
                ).first()
                factura_origen_id = origen.id if origen else None

            factura = Factura(
                cliente_id=cliente.id,
                serie=serie,
                numero=siguiente_num,
                fecha_emision=datetime.now(),
                base_imponible=base,
                iva_pct=iva_pct,
                iva_cuota=iva,
                irpf_pct=irpf_pct,
                irpf_cuota=irpf,
                total=total,
                estado="pagada",
                tipo_factura=tipo_factura_db,
                tipo_rectificacion=tipo_rectificacion_db,
                motivo_rectificacion=datos.get("concepto") if tipo_operacion in {"abono", "rectificativa"} else None,
                factura_origen_id=factura_origen_id,
            )
            
            db.add(factura)
            db.commit()
            db.refresh(factura)
            
            # Guardar línea de factura con el concepto
            from app.models.models import LineaFactura
            concepto = datos.get("concepto", "Servicio")
            linea = LineaFactura(
                factura_id=factura.id,
                numero_linea=1,
                descripcion=concepto,
                cantidad=1,
                precio_unitario=base,
                descuento_pct=0,
                base_imponible=base,
                iva_pct=iva_pct,
                iva_cuota=iva,
                total=total
            )
            db.add(linea)
            db.commit()
            
            # Generar PDF persistente y URL pública
            pdf_path = ensure_factura_pdf(db, factura, cliente)
            pdf_url = factura_pdf_public_url(factura.id)
            
            # Determinar tipo de factura (F1 = normal, F2 = simplificada sin NIF)
            es_simplificada = sesion.get("_factura_simplificada", False)
            tipo_factura = "F2" if es_simplificada else "F1"
            
            if tipo_operacion == "abono":
                tipo_factura = "R1"
            elif tipo_operacion == "rectificativa":
                tipo_factura = datos.get("tipo_rectificativa", "R1")
            
            # Enviar a VeriFacti
            verifacti_result = await enviar_factura_verifacti(factura, cliente, tipo_factura)
            
            if verifacti_result.get("success"):
                respuesta = f"✅ *{serie}-{siguiente_num} creada y enviada a VeriFacti*\n\n"
            else:
                respuesta = f"✅ *{serie}-{siguiente_num} creada (VeriFacti: error)*\n\n"
            
            respuesta += f"📋 *Resumen:*\n"
            respuesta += f"   Cliente: {cliente.nombre}\n"
            respuesta += f"   Base: {base:.2f}€ | IVA: {iva:.2f}€ | IRPF: {irpf:.2f}€\n"
            respuesta += f"   *TOTAL: {total:.2f}€*\n\n"
            if cliente.email:
                send_factura_to_client(
                    cliente_email=cliente.email,
                    factura=factura,
                    cliente_nombre=cliente.nombre,
                    pdf_path=pdf_path,
                    pdf_url=pdf_url,
                )
                respuesta += f"📧 Enviada al email del cliente: {cliente.email}\n"

            if os.getenv("ASESOR_EMAIL"):
                from app.services import email_service as email_service_module

                original_asesor = email_service_module.ASESOR_EMAIL
                email_service_module.ASESOR_EMAIL = os.getenv("ASESOR_EMAIL")
                try:
                    send_factura_copy_to_advisor(
                        factura=factura,
                        cliente_nombre=cliente.nombre,
                        pdf_path=pdf_path,
                        pdf_url=pdf_url,
                    )
                finally:
                    email_service_module.ASESOR_EMAIL = original_asesor
                respuesta += "📨 Copia enviada al asesor\n"

            respuesta += f"📄 Descargar PDF: {pdf_url}\n"
            respuesta += f"📱 Compartir por WhatsApp: https://wa.me/?text=Factura%20{factura.serie}-{factura.numero}%20{pdf_url}\n\n"
            respuesta += "¿Algo más?"
            
            # Limpiar sesión
            if from_number in sesiones_facturas:
                del sesiones_facturas[from_number]
            
            return {"response": respuesta}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error confirmando factura: {e}")
        return {"response": f"❌ Error: {str(e)}"}


async def crear_abono(from_number: str, texto: str) -> dict:
    """Crea una factura rectificativa (abono) - detecta si es por sustitución o diferencias"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """Extrae los datos para crear un ABONO (factura rectificativa).
                
Responde en JSON con:
{
    "cliente_nif": "NIF del cliente",
    "cliente_nombre": "Nombre del cliente",
    "importe": 0.0,
    "iva": 21,
    "concepto": "Descripción del motivo del abono",
    "factura_origen_serie": "Serie de la factura a rectificar",
    "factura_origen_numero": "Número de la factura a rectificar"
}

Si es un "abono" simple (devolución), usa el importe total negativo."""},
                {"role": "user", "content": texto}
            ],
            response_format={"type": "json_object"}
        )
        
        datos = json.loads(response.choices[0].message.content)
        
        if not datos.get("cliente_nif"):
            return {"response": "❌ Necesito el NIF del cliente para crear el abono."}
        
        db = SessionLocal()
        try:
            cliente = db.query(Cliente).filter(Cliente.nif == datos.get("cliente_nif")).first()
            if not cliente:
                return {"response": f"❌ No encontré cliente con NIF {datos.get('cliente_nif')}"}
            
            # Buscar factura origen
            serie_orig = datos.get("factura_origen_serie", "FI")
            num_orig = datos.get("factura_origen_numero", "")
            
            if num_orig:
                factura_orig = db.query(Factura).filter(
                    Factura.serie == serie_orig,
                    Factura.numero == num_orig
                ).first()
            else:
                # Tomar la última factura del cliente
                factura_orig = db.query(Factura).filter(
                    Factura.cliente_id == cliente.id
                ).order_by(Factura.fecha_emision.desc()).first()
            
            if not factura_orig:
                return {"response": f"❌ No encontré factura origen para rectificar."}
            
            # Guardar datos para confirmación
            sesiones_facturas[from_number] = {
                "tipo": "abono",
                "datos": datos,
                "factura_origen": {
                    "serie": factura_orig.serie,
                    "numero": factura_orig.numero,
                    "base": factura_orig.base_imponible,
                    "iva": factura_orig.iva_cuota
                },
                "timestamp": datetime.now().timestamp()
            }
            
            respuesta = f"📋 *ABONO - Datos extraídos:*\n\n"
            respuesta += f"👤 Cliente: {datos.get('cliente_nombre')}\n"
            respuesta += f"📄 Factura origen: {factura_orig.serie}-{factura_orig.numero}\n"
            respuesta += f"💰 Importe: {datos.get('importe', 0)}€\n"
            respuesta += f"📝 Concepto: {datos.get('concepto')}\n\n"
            respuesta += "¿Confirmas? Responde *sí* para generar el abono."
            
            return {"response": respuesta}
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error creando abono: {e}")
        return {"response": f"❌ Error: {str(e)}"}


async def crear_rectificativa(from_number: str, texto: str) -> dict:
    """Crea una factura rectificativa - requiere especificar tipo R1-R5"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """Extrae los datos para crear una FACTURA RECTIFICATIVA.

Tipos disponibles:
- R1: Error fundado en derecho (art. 80.1, 80.2, 80.6)
- R2: Concurso de acreedores (art. 80.3)
- R3: Crédito incobrable (art. 80.4)
- R4: Bienes afectados a la OSA (art. 80.5)
- R5: Bienes exportados/PNB (art. 80.6)

Responde en JSON con:
{
    "cliente_nif": "NIF del cliente",
    "cliente_nombre": "Nombre del cliente", 
    "importe": 0.0,
    "iva": 21,
    "concepto": "Descripción del motivo",
    "factura_origen_serie": "Serie",
    "factura_origen_numero": "Número",
    "tipo_rectificativa": "R1", "R2", "R3", "R4" o "R5"
}"""},
                {"role": "user", "content": texto}
            ],
            response_format={"type": "json_object"}
        )
        
        datos = json.loads(response.choices[0].message.content)
        
        if not datos.get("cliente_nif"):
            return {"response": "❌ Necesito el NIF del cliente."}
        
        if not datos.get("tipo_rectificativa"):
            return {"response": "❌ Especifica el tipo: R1, R2, R3, R4 o R5\n\nEj: 'rectificativa R1 de factura FI-5 por 50€'"}
        
        db = SessionLocal()
        try:
            cliente = db.query(Cliente).filter(Cliente.nif == datos.get("cliente_nif")).first()
            if not cliente:
                return {"response": f"❌ No encontré cliente con NIF {datos.get('cliente_nif')}"}
            
            serie_orig = datos.get("factura_origen_serie", "FI")
            num_orig = datos.get("factura_origen_numero", "")
            
            if num_orig:
                factura_orig = db.query(Factura).filter(
                    Factura.serie == serie_orig,
                    Factura.numero == num_orig
                ).first()
            else:
                factura_orig = db.query(Factura).filter(
                    Factura.cliente_id == cliente.id
                ).order_by(Factura.fecha_emision.desc()).first()
            
            if not factura_orig:
                return {"response": "❌ No encontré factura origen."}
            
            # Guardar para confirmación
            sesiones_facturas[from_number] = {
                "tipo": "rectificativa",
                "datos": datos,
                "factura_origen": {
                    "serie": factura_orig.serie,
                    "numero": factura_orig.numero,
                    "base": factura_orig.base_imponible,
                    "iva": factura_orig.iva_cuota
                },
                "timestamp": datetime.now().timestamp()
            }
            
            respuesta = f"📋 *RECTIFICATIVA {datos.get('tipo_rectificativa')} - Datos:*\n\n"
            respuesta += f"👤 Cliente: {datos.get('cliente_nombre')}\n"
            respuesta += f"📄 Factura origen: {factura_orig.serie}-{factura_orig.numero}\n"
            respuesta += f"💰 Importe: {datos.get('importe', 0)}€\n"
            respuesta += f"📝 Concepto: {datos.get('concepto')}\n\n"
            respuesta += "¿Confirmas? Responde *sí*."
            
            return {"response": respuesta}
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error creando rectificativa: {e}")
        return {"response": f"❌ Error: {str(e)}"}


async def listar_facturas(from_number: str = None, filtro: str = None) -> str:
    """Lista las facturas disponibles"""
    db = SessionLocal()
    try:
        query = db.query(Factura)
        
        if filtro:
            clientes = db.query(Cliente).filter(Cliente.nombre.like(f"%{filtro}%")).all()
            cliente_ids = [c.id for c in clientes]
            if cliente_ids:
                query = query.filter(Factura.cliente_id.in_(cliente_ids))
        
        facturas = query.order_by(Factura.fecha_emision.desc()).limit(10).all()
        if not facturas:
            return "📄 No se encontraron facturas."
        
        respuesta = "📄 *Facturas:*\n\n"
        for f in facturas:
            fecha = f.fecha_emision.strftime('%d/%m/%Y') if f.fecha_emision else 'N/A'
            respuesta += f"• {f.serie}-{f.numero} | {fecha} | {f.total:.2f}€ | {f.estado}\n"
        
        if filtro:
            respuesta += f"\n📌 Filtro: {filtro}"
        
        return respuesta
    finally:
        db.close()


async def buscar_facturas_por_cliente(nombre_cliente: str) -> str:
    """Busca facturas por nombre de cliente"""
    return await listar_facturas(None, filtro=nombre_cliente)


async def informe_facturacion(from_number: str = None) -> str:
    """Genera informe de facturación"""
    db = SessionLocal()
    try:
        facturas = db.query(Factura).all()
        
        if not facturas:
            return "📊 No hay facturas registradas."
        
        total_facturado = sum(f.total for f in facturas)
        total_base = sum(f.base_imponible for f in facturas)
        total_iva = sum(f.iva_cuota for f in facturas)
        total_irpf = sum(f.irpf_cuota for f in facturas)
        
        # Por cliente
        por_cliente = {}
        for f in facturas:
            nombre = f.cliente.nombre if f.cliente else "Sin cliente"
            if nombre not in por_cliente:
                por_cliente[nombre] = {"count": 0, "total": 0}
            por_cliente[nombre]["count"] += 1
            por_cliente[nombre]["total"] += f.total
        
        respuesta = "📊 *INFORME DE FACTURACIÓN*\n\n"
        respuesta += f"📈 *Totales:*\n"
        respuesta += f"   • Facturas: {len(facturas)}\n"
        respuesta += f"   • Base imponible: {total_base:.2f}€\n"
        respuesta += f"   • IVA: {total_iva:.2f}€\n"
        respuesta += f"   • IRPF: {total_irpf:.2f}€\n"
        respuesta += f"   • *TOTAL: {total_facturado:.2f}€*\n\n"
        respuesta += f"📋 *Por cliente:*\n"
        
        for cliente, datos in sorted(por_cliente.items(), key=lambda x: x[1]["total"], reverse=True):
            respuesta += f"   • {cliente}: {datos['count']} fac. ({datos['total']:.2f}€)\n"
        
        return respuesta
    finally:
        db.close()


# Modelo Whisper (cargado una vez)
_whisper_model = None

def get_whisper_model():
    """Carga el modelo Whisper una sola vez"""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # Modelo small es rápido y preciso suficiente
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
        logger.info("Modelo Whisper cargado")
    return _whisper_model


async def transcribe_audio(audio_url: str) -> str:
    """
    Descarga y transcribe audio usando Whisper local
    
    Args:
        audio_url: URL del archivo de audio
    
    Returns:
        Texto transcrito
    """
    import requests
    import io
    import tempfile
    import os
    
    try:
        # Descargar audio
        headers = {"User-Agent": "FacturacionInvisible/1.0"}
        response = requests.get(audio_url, headers=headers, timeout=60)
        if response.status_code != 200:
            logger.error(f"Error descargando audio: {response.status_code}")
            return None
        
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        
        try:
            # Transcribir con Whisper local
            model = get_whisper_model()
            segments, info = model.transcribe(
                tmp_path,
                language="es",
                beam_size=5,
                vad_filter=True
            )
            
            texto = " ".join([seg.text for seg in segments])
            logger.info(f"Transcripción completada: {texto[:100]}...")
            
            return texto.strip()
            
        finally:
            # Limpiar archivo temporal
            try:
                os.unlink(tmp_path)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Error transcribiendo audio: {e}")
        return None


# Alias para mantener compatibilidad
async def procesar_factura_whatsapp(from_number: str, texto: str):
    """Wrapper para procesar factura"""
    return await process_whatsapp_message(from_number, texto)
