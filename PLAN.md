# 📋 PLAN: Facturación Invisible v1.0 (ACTUALIZADO)

## 1. RESUMEN EJECUTIVO

**Producto:** Asistente contable por WhatsApp/Telegram para freelancers españoles  
**Objetivo:** Automatizar la facturación mediante chat conversacional  
**Mercado:** 3.2M freelancers en España  
**Meta MRR:** 15,000-30,000€/mes (500 clientes)

---

## 2. VERIFACTU - REQUISITOS OBLIGATORIOS (CORREGIDOS)

### 2.1 Estructura de Factura Electrónica
- [ ] **Libro registro de facturas emitidas** (envío a AEAT)
- [ ] **Numeración secuencial** con serie (e.g., "FI-2026-001")
- [ ] **Datos obligatorios del emisor:**
  - NIF/CIF
  - Nombre/Razón social
  - Domicilio fiscal
  - Inscripción registro mercantil (si aplica)
- [ ] **Datos obligatorios del receptor:**
  - NIF (obligatorio si cliente empresa)
  - Nombre/Razón social
  - Domicilio
- [ ] **Desglose de IVA** (por tipos: 21%, 10%, 4%, exento)
- [ ] **IRPF** (retenciones 15%/7% según situación)
- [ ] **Fecha de operación y fecha de factura**
- [ ] **Base imponible, cuota IVA, total**

### 2.2 Plazos de Envío (CORREGIDO)
| Tipo | Plazo REAL |
|------|------------|
| Facturas emitidas | **8 días hábiles** |
| Rectificativas | 3 días hábiles |
| Bienes de inversión | 4 días hábiles |

### 2.3 SII - Requisitos
- [ ] Alta en SII (Suministro Inmediato de Facturas) - AEAT
- [ ] Clave de certificación
- [ ] XML estructurado (Schema SII v1.1)
- [ ] Firma digital del XML
- [ ] Envío al portal AEAT
- [ ] Custodia durante 6 años

---

## 3. ARQUITECTURA TÉCNICA

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Telegram   │────▶│   FastAPI   │────▶│   OpenAI    │
│   (preferido)   │     │   (propio)   │     │   (GPT-4o)   │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │  SQLite  │     │  Stripe   │     │ VeriFactu │
  │  (DB)    │     │ (Pagos)  │     │   (AEAT)  │
  └──────────┘     └──────────┘     └──────────┘
```

**Cambio:** Telegram (más fácil) + FastAPI (más control que n8n)

---

## 4. MÓDULOS DEL SISTEMA

### 4.1 Módulo: Chat Interface (Telegram)
- [ ] Bot Telegram con webhook
- [ ] Parser NLP para extraer: cliente, concepto, importe, fecha
- [ ] Estados de conversación
- [ ] Comandos: /start, /factura, /ayuda

### 4.2 Módulo: Generador de Facturas
- [ ] Motor de plantillas (JSON → PDF)
- [ ] Cálculo automático de IVA/IRPF
- [ ] Numeración secuencial con serie
- [ ] Generación XML SII
- [ ] Envío por email automático

### 4.3 Módulo: Base de Datos
- [ ] Tabla clientes (NIF, nombre, dirección, email)
- [ ] Tabla facturas (completas con líneas)
- [ ] Tabla configuración (IVA default, IRPF default)
- [ ] Backup automático

### 4.4 Módulo: VeriFactu/SII
- [ ] Alta en SII (requiere certificado digital)
- [ ] Generación XML SII
- [ ] Firma digital
- [ ] Envío a AEAT
- [ ] Libro registro

### 4.5 Módulo: Pagos (Stripe)
- [ ] Cobro recurrente
- [ ] Gestión de suscripciones
- [ ] Portal cliente
- [ ] Webhooks para cambios de estado

### 4.6 Módulo: Legal/Compliance
- [ ] Política de privacidad (GDPR)
- [ ] Términos de servicio
- [ ] Custodia facturas (6 años)
- [ ] Registro LOPD

---

## 5. ROADMAP DE IMPLEMENTACIÓN (CORREGIDO)

### Fase 1: MVP + VeriFactu EN PARALELO (Semanas 1-2)
- [ ] Setup Telegram Bot
- [ ] Chat básico: "Cobré X€ de Y por Z"
- [ ] Alta en SII AEAT (preparar certificado)
- [ ] Estructura completa factura desde día 1
- [ ] Generar PDF
- [ ] Envío email

### Fase 2: VeriFactu Completo (Semanas 3-4)
- [ ] Conexión AEAT (certificado digital)
- [ ] Envío automático XML SII
- [ ] Libro registro
- [ ] Recordatorios de plazo

### Fase 3: Pagos (Semanas 5-6)
- [ ] Stripe integración
- [ ] Suscripciones
- [ ] Portal cliente

### Fase 4: Escalado (Semanas 7-8)
- [ ] Dashboard cliente
- [ ] Reportes
- [ ] Multi-usuario

---

## 6. STACK TECNOLÓGICO

| Componente | Tecnología | Coste |
|------------|-----------|-------|
| Chat | **Telegram Bot** (preferido) | 0€/mes |
| API | **FastAPI** (propio) | 0€/mes |
| AI | OpenAI GPT-4o | 50-150€/mes |
| DB | SQLite/PostgreSQL | 0-20€/mes |
| Hosting | VPS (existing) | 0€ |
| Dominio | Cloudflare | 10€/año |
| Certificado | digital (autofirma) | 0-25€/año |
| **Total mensual** | | **50-170€/mes** |

---

## 7. PRECIOS (ACTUALIZADOS)

| Tier | Precio | Funcionalidades |
|------|--------|-----------------|
| **Starter** | 29€/mes | 10 facturas/mes, PDF, email |
| **Pro** | 59€/mes | Facturas ilimitadas, **VeriFactu completo** |
| **Premium** | 99€/mes | Todo + integración banco + soporte prioritario |

---

## 8. PRIORIDADES DE IMPLEMENTACIÓN

1. **Telegram Bot** + Parser NLP
2. **Factura completa** (no simplificada)
3. **VeriFactu desde día 1** (paralelo)
4. **Alta SII AEAT** (certificado)
5. **Stripe**
6. Portal cliente

---

## 9. PRIMEROS PASOS (ESTA SEMANA)

1. [ ] Crear bot Telegram con BotFather
2. [ ] Setup FastAPI básico
3. [ ] Parser de mensajes
4. [ ] Generar primera factura PDF de prueba

---

*Plan actualizado: 12/03/2026*
*Revisado por CodexBot ✓*
