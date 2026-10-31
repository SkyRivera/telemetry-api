from fastapi import Header, HTTPException, status

from app.config import settings


async def verify_esp32_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key != settings.api_key_esp32:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ESP32 API key",
        )
    return x_api_key


async def verify_api_b_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key != settings.api_key_api_b:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API B API key",
        )
    return x_api_key
