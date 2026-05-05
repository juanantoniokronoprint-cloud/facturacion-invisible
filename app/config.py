import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _parse_csv_env(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# API / Seguridad
API_KEY = os.getenv("API_KEY", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()  # production | development
APP_DEBUG = os.getenv("APP_DEBUG", "false").lower() in {"1", "true", "yes", "on"}
ALLOWED_ORIGINS = _parse_csv_env(
    "ALLOWED_ORIGINS",
    "http://127.0.0.1:8001,http://localhost:8001,http://127.0.0.1:8000,http://localhost:8000",
)
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
WHATSAPP_WEBHOOK_SECRET = os.getenv("WHATSAPP_WEBHOOK_SECRET", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./facturas.db")
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
PDF_STORAGE_DIR = STORAGE_DIR / "pdfs"
REPORT_STORAGE_DIR = STORAGE_DIR / "reports"
OUTBOX_DIR = STORAGE_DIR / "outbox"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8001").rstrip("/")

# Facturación
SERIE_FACTURA = os.getenv("SERIE_FACTURA", "FI")
IVA_DEFAULT = float(os.getenv("IVA_DEFAULT", "21"))
IRPF_DEFAULT = float(os.getenv("IRPF_DEFAULT", "15"))

# VeriFacti
VERIFACTI_API_KEY = os.getenv("VERIFACTI_API_KEY", "")
VERIFACTI_SEND_MODE = os.getenv("VERIFACTI_SEND_MODE", "demo").lower()  # demo | live
GOG_ACCOUNT = os.getenv("GOG_ACCOUNT", "")
EMAIL_SEND_MODE = os.getenv("EMAIL_SEND_MODE", "outbox").lower()  # outbox | live
CONTABILIDAD_EMAIL = os.getenv("CONTABILIDAD_EMAIL", "")
ASESOR_EMAIL = os.getenv("ASESOR_EMAIL", "")

# Teléfonos autorizados para facturar (dict: teléfono -> nombre)
def parse_telefonos_autorizados():
    """Parsea TELEFONOS_AUTORIZADOS del formato: telefono=nombre,telefono2=nombre2"""
    raw = os.getenv("TELEFONOS_AUTORIZADOS", "")
    if not raw:
        return {}
    result = {}
    for item in raw.split(","):
        if "=" in item:
            tel, nombre = item.split("=", 1)
            result[tel.strip()] = nombre.strip()
    return result

TELEFONOS_AUTORIZADOS = parse_telefonos_autorizados()

# Datos del emisor
EMISOR_NIF = os.getenv("EMISOR_NIF", "00000000T")
EMISOR_NOMBRE = os.getenv("EMISOR_NOMBRE", "Facturación Invisible")
EMISOR_DOMICILIO = os.getenv("EMISOR_DOMICILIO", "")
EMISOR_CP = os.getenv("EMISOR_CP", "")
EMISOR_POBLACION = os.getenv("EMISOR_POBLACION", "")
EMISOR_PROVINCIA = os.getenv("EMISOR_PROVINCIA", "")
EMISOR_CLAVE_REGIMEN = os.getenv("EMISOR_CLAVE_REGIMEN", "01")

# VeriFactu
ENVIROMENT = ENVIRONMENT  # Compatibilidad: typo histórico usado en código antiguo.

for directory in (STORAGE_DIR, PDF_STORAGE_DIR, REPORT_STORAGE_DIR, OUTBOX_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# SMTP Email
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)

# WhatsApp
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")

# Contabilidad
CONTABILIDAD_EMAIL = os.getenv("CONTABILIDAD_EMAIL", "")
ASESOR_EMAIL = os.getenv("ASESOR_EMAIL", "")
