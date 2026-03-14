# Facturación Invisible

Asistente contable por Telegram para freelancers españoles.

## Setup

```bash
cd /home/debian/proyectos-express/facturacion-invisible
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuración

Copia `.env.example` a `.env` y configura:

```
TELEGRAM_BOT_TOKEN=tu_token
OPENAI_API_KEY=tu_key
DATABASE_URL=sqlite:///facturas.db
```

## Ejecución

```bash
uvicorn app.main:app --reload --port 8000
```

## Estructura

```
app/
├── main.py          # Entry point
├── bot.py           # Telegram bot
├── models/         # Modelos DB
├── routes/         # API endpoints
├── services/       # Lógica de negocio
└── templates/      # Plantillas PDF
```
