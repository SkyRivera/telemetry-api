from fastapi import HTTPException, Security, Request
from fastapi.security import APIKeyHeader
from app.config import get_settings
import secrets
import re

settings = get_settings()

# Headers para autenticación
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
device_id_header = APIKeyHeader(name="X-Device-ID", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verificar API Key para servicios externos (API B).

    Args:
        api_key: API Key del header X-API-Key

    Returns:
        str: API Key validada

    Raises:
        HTTPException: Si la API Key es inválida
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API Key required. Please provide X-API-Key header"
        )

    # Validar contra la API key configurada
    if not secrets.compare_digest(api_key, settings.API_KEY_IOT):
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )

    return api_key


def verify_iot_api_key(
    api_key: str = Security(api_key_header),
    device_id: str = Security(device_id_header)
) -> dict:
    """
    Verificar API Key para dispositivos IoT (ESP32).

    Args:
        api_key: API Key del header X-API-Key
        device_id: Device ID del header X-Device-ID

    Returns:
        dict: Datos de autenticación

    Raises:
        HTTPException: Si la autenticación es inválida
    """
    # Validar API Key
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API Key required. Please provide X-API-Key header"
        )

    if not secrets.compare_digest(api_key, settings.API_KEY_IOT):
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )

    # Validar Device ID
    if not device_id:
        raise HTTPException(
            status_code=401,
            detail="Device ID required. Please provide X-Device-ID header"
        )

    # Validar formato de device_id (alphanumeric + guiones/guiones bajos)
    if not re.match(r'^[a-zA-Z0-9\-_]+$', device_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid Device ID format. Use alphanumeric characters, hyphens and underscores only"
        )

    if len(device_id) > 50:
        raise HTTPException(
            status_code=400,
            detail="Device ID too long (max 50 characters)"
        )

    return {"api_key": api_key, "device_id": device_id}


def get_current_device_id(auth_data: dict = Security(verify_iot_api_key)) -> str:
    """
    Obtener el device_id del dispositivo autenticado.

    Args:
        auth_data: Datos de autenticación de verify_iot_api_key

    Returns:
        str: Device ID validado
    """
    return auth_data["device_id"]


def get_client_ip(request: Request) -> str:
    """
    Obtener IP del cliente desde el request.

    Args:
        request: Request de FastAPI

    Returns:
        str: IP del cliente
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
