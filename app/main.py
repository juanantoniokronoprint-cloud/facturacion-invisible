import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.routes import webhooks, facturas, clientes
from app.config import EMISOR_NIF, EMISOR_NOMBRE, EMISOR_DOMICILIO, EMISOR_CP, EMISOR_POBLACION, EMISOR_PROVINCIA

load_dotenv()

app = FastAPI(
    title="Facturación Invisible API",
    description="Asistente contable por Telegram para freelancers",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router, prefix="/webhook", tags=["webhooks"])
app.include_router(facturas.router, prefix="/api/facturas", tags=["facturas"])
app.include_router(clientes.router, prefix="/api/clientes", tags=["clientes"])

@app.get("/")
def landing():
    """Serve the landing page"""
    return FileResponse("static/landing.html")

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/portal")
def portal():
    """Serve the client portal"""
    return FileResponse("static/portal.html")

@app.get("/api/config")
def get_config():
    """Get company configuration"""
    from app.config import CONTABILIDAD_EMAIL, ASESOR_EMAIL, TELEFONOS_AUTORIZADOS
    telefonos_str = ""
    if TELEFONOS_AUTORIZADOS:
        telefonos_list = [f"{k}={v}" for k, v in TELEFONOS_AUTORIZADOS.items()]
        telefonos_str = ", ".join(telefonos_list)
    
    return {
        "nif": EMISOR_NIF,
        "nombre": EMISOR_NOMBRE,
        "domicilio": EMISOR_DOMICILIO,
        "cp": EMISOR_CP,
        "poblacion": EMISOR_POBLACION,
        "provincia": EMISOR_PROVINCIA,
        "contabilidad_email": CONTABILIDAD_EMAIL or "",
        "asesor_email": ASESOR_EMAIL or "",
        "telefonos_autorizados": telefonos_str
    }

@app.get("/api/help")
def get_help():
    """Get quick usage guide for the portal and messaging channels"""
    return {
        "whatsapp": {
            "intro": "Envía un mensaje describiendo el cobro y el sistema te guía.",
            "comandos": [
                "ft Cobré 300€ de María por traducción",
                "ver mis facturas",
                "informe de facturación",
                "ayuda"
            ]
        },
        "telegram": {
            "intro": "Usa los comandos básicos del bot para empezar.",
            "comandos": [
                "/start",
                "/facturas",
                "/ayuda"
            ]
        },
        "nota": "Gratis detecta fallos del proceso; la revisión avanzada debe completarse antes de usarlo en producción."
    }

@app.put("/api/config")
def update_config(config: dict):
    """Update company configuration (saves to .env)"""
    env_path = ".env"
    
    # Read current .env
    with open(env_path, "r") as f:
        lines = f.readlines()
    
    # Update values
    updates = {
        "EMISOR_NIF": config.get("nif", ""),
        "EMISOR_NOMBRE": config.get("nombre", ""),
        "EMISOR_DOMICILIO": config.get("domicilio", ""),
        "EMISOR_CP": config.get("cp", ""),
        "EMISOR_POBLACION": config.get("poblacion", ""),
        "EMISOR_PROVINCIA": config.get("provincia", ""),
        "CONTABILIDAD_EMAIL": config.get("contabilidad_email", ""),
        "ASESOR_EMAIL": config.get("asesor_email", ""),
        "TELEFONOS_AUTORIZADOS": config.get("telefonos_autorizados", "")
    }
    
    # Replace values in .env
    new_lines = []
    for line in lines:
        key = line.split("=")[0] if "=" in line else ""
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
        else:
            new_lines.append(line)
    
    # Add missing keys
    for key, value in updates.items():
        if not any(key in l for l in lines):
            new_lines.append(f"{key}={value}\n")
    
    with open(env_path, "w") as f:
        f.writelines(new_lines)
    
    return {"status": "ok", "message": "Configuración actualizada"}
