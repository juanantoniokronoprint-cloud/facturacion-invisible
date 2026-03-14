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
