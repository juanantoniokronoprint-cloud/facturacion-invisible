# Revisión Codex

## Estado actual

- El número `+34686981404` ya está autorizado en `.env`.
- El portal muestra facturas, datos fiscales y ayuda básica.
- La app arranca y responde en `:8001`, pero antes se estaba lanzando de forma no persistente.

## Riesgos detectados

1. Cumplimiento fiscal
- Los datos del emisor siguen con valores de ejemplo.
- No debe usarse en producción sin `NIF`, domicilio fiscal y serie revisados.

2. Operativa real
- Faltan validaciones más duras para rectificativas y abonos.
- Falta cerrar un flujo de revisión previa antes de enviar datos a VeriFacti.

3. Experiencia de usuario
- Había ayuda en WhatsApp, pero no visible en el portal.
- El portal no estaba leyendo bien la respuesta de `/api/facturas/`.

## Perfil financiero y legal

- Como experto financiero: la base sirve para pruebas, pero aún no la daría por lista para emitir facturas reales sin revisar series, impuestos y rectificativas.
- Como autónomo español: el valor está claro si me ahorra tiempo por WhatsApp, pero necesito ver rápido qué puedo escribir y qué datos fiscales están activos.
- Como oficios manuales (`albañil`, `mecánico`, `carpintero`): el producto debe ser directo, con comandos claros y sin jerga contable.

## Qué faltaría para decir "listo"

1. Completar datos del emisor reales.
2. Definir flujo de abonos y rectificativas.
3. Dejar el arranque persistente como servicio o sesión controlada.
4. Probar facturación completa de extremo a extremo con un caso real.

## Intervención 2026-05-04

### Ejecutado

1. Seguridad básica de API:
   - `PUT /api/config` queda protegido por `X-API-Key`.
   - Rutas de clientes y facturas quedan protegidas por dependencia global.
   - En `ENVIRONMENT=production`, si falta `API_KEY`, el servidor falla cerrado para endpoints protegidos.
   - CORS deja de usar comodín `*` con credenciales y pasa a `ALLOWED_ORIGINS`.

2. Calidad técnica:
   - Reparado el arranque de `app.main` por import faltante de `Depends`.
   - Eliminadas advertencias propias de Pydantic v2 y SQLAlchemy 2.
   - Añadida suite mínima de tests para autenticación e import de app.
   - Añadido `requirements-dev.txt` para instalar herramientas de test.

### Plan recomendado de siguientes mejoras

1. Separar endpoints de lectura pública del portal y endpoints operativos protegidos.
2. Sustituir cambios directos sobre `.env` por una tabla `configuracion` o panel admin autenticado.
3. Añadir flujo de previsualización antes de cualquier envío real por email, WhatsApp o VeriFacti.
4. Consolidar cálculo fiscal en un único servicio para evitar duplicidad entre API y chat.
5. Añadir tests de integración con `TestClient` para facturas, clientes y webhooks.

## Intervención 2026-05-04 — endurecimiento producción

### Ejecutado

1. `GET /api/config` también queda protegido por `X-API-Key` para no exponer emails, teléfonos ni datos fiscales.
2. Añadido `/ready` con checklist de preparación para producción.
3. Desactivados `/docs` y `/redoc` en `ENVIRONMENT=production`.
4. Añadidas cabeceras de seguridad básicas.
5. Añadidos secretos opcionales para webhooks de Telegram y WhatsApp.
6. Cambiado email a modo seguro por defecto: `EMAIL_SEND_MODE=outbox`.
7. El portal permite guardar API key localmente y la envía en llamadas API.
8. Validaciones más estrictas en creación/actualización de facturas.
9. `GET /api/facturas` deja de generar PDFs/commits como efecto lateral.
10. VeriFacti queda en modo demo salvo activación explícita `VERIFACTI_SEND_MODE=live`.
11. Añadidos `.env.example`, `PRODUCTION.md` y tests adicionales.

## Intervención 2026-05-04 — abonos y rectificativas

### Ejecutado

1. Añadida persistencia fiscal mínima en `facturas`:
   - `tipo_factura` (`F1`, `F2`, `R1`-`R5`)
   - `tipo_rectificacion` (`S`/`I`)
   - `motivo_rectificacion`
   - `factura_origen_id`
2. Añadidos endpoints web protegidos:
   - `POST /api/facturas/{factura_id}/abono`
   - `POST /api/facturas/{factura_id}/rectificativa`
3. Añadidos botones en dashboard para crear abono y rectificativa desde una factura normal.
4. Corregido flujo WhatsApp para persistir el tipo fiscal y la factura origen.
5. Corregidos transformadores VeriFacti/VeriFactu para evitar imports rotos y soportar ORM de Factura Invisible.
6. Añadidas pruebas de payloads de abono/rectificativa y smoke test aislado de endpoints.

### Validación

- Tests: `31 passed`.
- Servicio `facturacion-invisible.service` reiniciado y activo.
- Dashboard: `/portal` responde `200 OK`.
- OpenAPI expone rutas de abono y rectificativa.

### QA externo Kilobot — gremios autónomos España

Kilobot simuló 8 perfiles de autónomo español (fontanero, electricista, albañil, mecánico, diseñador, peluquería, transportista y casos borde).

Resultado inicial:
- 11/12 pruebas pasadas.
- Fallo crítico: se aceptaba factura simplificada F2 >400€ sin NIF.

Corrección aplicada:
- `crear_factura()` y `crear_factura_simple()` rechazan ahora facturas superiores a 400€ con IVA incluido si falta NIF.
- Validado en endpoint live: `POST /api/facturas/simple` devuelve `422` para base 500€ + IVA 21% sin NIF.
- Tests finales: `33 passed`.

Informe: `tmp/kilo-reports/gremios_autonomos_report.md`.

### QA ampliado Kilobot — 120 pruebas

El usuario pidió mínimo 100 pruebas. Kilobot ejecutó 120 pruebas no destructivas con SQLite/TestClient.

Resultado tras correcciones:
- 113 PASS
- 5 FAIL clasificados como falsos positivos/criterios inválidos del script
- 2 WARNING de decisión de negocio
- 0 ERROR

Mejoras reales aplicadas:
- Respuestas completas de cliente en endpoints de facturas.
- Alias legacy VeriFacti/VeriFactu para compatibilidad QA/integraciones.
- Outbox devuelve `path` además de `outbox_path`.
- Calculadora acepta líneas tipo dict.
- `irpf_pct=None` cae a 0 de forma segura.

Informe: `tmp/kilo-reports/gremios_autonomos_100_report.md`.
