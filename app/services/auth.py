"""
Autenticación por API Key para endpoints protegidos
"""
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from app.config import API_KEY, ENVIRONMENT

# Endpoints que requieren autenticación
PROTECTED_ENDPOINTS = [
    "/api/facturas",
    "/api/clientes", 
    "/api/config",  # PUT /api/config
]

# Endpoints públicos (sin auth)
PUBLIC_ENDPOINTS = [
    "/",
    "/health",
    "/portal",
    "/api/help",
    "/api/config",  # GET /api/config es público
    "/webhook",
]


def get_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Dependency que verifica la API Key en el header
    
    Usage:
        @app.get("/protected")
        def protected_route(api_key: str = Depends(get_api_key)):
            ...
    """
    # Si no hay API key configurada, permitir acceso solo en desarrollo local.
    # En producción se falla cerrado para no exponer facturación sin secreto.
    if not API_KEY and ENVIRONMENT != "production":
        return "dev-mode"

    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API Key no configurada en servidor"
        )
    
    # Verificar que se proporcione API key
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta API Key. Usa header: X-API-Key"
        )
    
    # Verificar API key
    if not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key inválida"
        )
    
    return x_api_key


def require_auth():
    """Dependency para requerir autenticación"""
    return Depends(get_api_key)
