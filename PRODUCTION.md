# Producción — Facturación Invisible

## Estado

La app queda endurecida para preproducción/producción básica, pero **no debe emitir facturas reales** hasta completar pruebas extremo a extremo con datos fiscales reales y criterio del asesor.

## Variables obligatorias

Copiar `.env.example` a `.env` y revisar:

- `ENVIRONMENT=production`
- `API_KEY`: secreto largo.
- `ALLOWED_ORIGINS`: dominio real, sin `*`.
- `PUBLIC_BASE_URL`: URL pública real.
- `TELEGRAM_WEBHOOK_SECRET`
- `WHATSAPP_WEBHOOK_SECRET`
- Datos reales del emisor: `EMISOR_NIF`, `EMISOR_NOMBRE`, domicilio fiscal.
- `EMAIL_SEND_MODE=outbox` inicialmente.
- `VERIFACTI_SEND_MODE=demo` inicialmente.

## Arranque recomendado

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Para producción real, ponerlo detrás de proxy HTTPS y gestor de procesos. No exponer Uvicorn directo a Internet.

## Comprobaciones

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/ready
curl -H "X-API-Key: $API_KEY" http://127.0.0.1:8001/api/config
```

`/ready` debe devolver `ready=true` antes de operar.

## Seguridad aplicada

- API de facturas/clientes/config protegida por `X-API-Key`.
- Webhooks opcionalmente protegidos por secreto:
  - Telegram: `X-Telegram-Bot-Api-Secret-Token`
  - WhatsApp bridge: `X-Webhook-Secret`
- CORS restringido por `ALLOWED_ORIGINS`.
- Docs FastAPI desactivados en `ENVIRONMENT=production`.
- Cabeceras de seguridad básicas.
- Envíos de email por defecto a `storage/outbox`, no envío real.
- VeriFacti queda en modo demo salvo `VERIFACTI_SEND_MODE=live`.

## Portal

El portal necesita API key para operar:

1. Abrir `/portal`.
2. Pulsar `🔐 API Key`.
3. Pegar la clave.

La clave queda guardada en `localStorage` del navegador. Usar solo en equipos confiables.

## Pendientes antes de producción real

1. Decidir si SQLite es suficiente o migrar a PostgreSQL.
2. Añadir migraciones de base de datos.
3. Confirmar flujo VeriFacti/AEAT con certificado y asesor.
4. Añadir backups automáticos y prueba de restauración.
5. Añadir logs estructurados y monitorización.
6. Revisar rectificativas/abonos con casos reales.
