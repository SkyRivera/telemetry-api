from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.schemas import (
    TelemetryCreate, TelemetryResponse, ErrorResponse,
    PaginatedResponse
)
from app.services.telemetry_service import TelemetryService
from app.services.command_service import CommandService
from app.security import verify_iot_api_key, verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["telemetry"])


@router.post(
    "/telemetry",
    response_model=TelemetryResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse}
    }
)
async def create_telemetry(
    telemetry_data: TelemetryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    auth_data: dict = Depends(verify_iot_api_key)
):
    """
    Recibe telemetría desde el ESP32.

    - **device_id**: Identificador único de la estación
    - **temperature**: Temperatura en °C (opcional)
    - **humidity**: Humedad relativa en % (opcional)
    - **wind_speed_kmh**: Velocidad del viento en km/h (opcional)
    - **temperature_valid**: Indica si la temperatura es válida
    - **humidity_valid**: Indica si la humedad es válida
    - **wind_speed_valid**: Indica si la velocidad del viento es válida
    - **sensor_status**: Estado general de los sensores
    - **reading_type**: Tipo de lectura (periodic/on_demand)
    - **request_id**: ID de solicitud si es on_demand
    """
    try:
        # Procesar telemetría
        service = TelemetryService(db)
        telemetry = service.process_telemetry(telemetry_data)

        # Limpiar solicitudes expiradas en background
        background_tasks.add_task(CommandService(db).cleanup_expired_requests)

        # Preparar respuesta
        station = telemetry.station
        age_seconds = int((datetime.now(timezone.utc) -
                          telemetry.timestamp_utc).total_seconds())

        return TelemetryResponse(
            id=telemetry.id,
            device_id=station.device_id,
            temperature=telemetry.temperature,
            humidity=telemetry.humidity,
            wind_speed_kmh=telemetry.wind_speed_kmh,
            temperature_valid=telemetry.temperature_valid,
            humidity_valid=telemetry.humidity_valid,
            wind_speed_valid=telemetry.wind_speed_valid,
            sensor_status=telemetry.sensor_status,
            reading_type=telemetry.reading_type,
            request_id=telemetry.request_id,
            measured_at=telemetry.timestamp_utc,
            reading_age_seconds=age_seconds
        )
    except Exception as e:
        logger.error(f"Error procesando telemetría: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Error processing telemetry: {str(e)}"
        )


@router.get(
    "/stations/{device_id}/telemetry/latest",
    response_model=TelemetryResponse,
    responses={
        404: {"model": ErrorResponse}
    }
)
async def get_latest_telemetry(
    device_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """
    Obtiene la última lectura de telemetría almacenada.

    - **device_id**: Identificador de la estación
    """
    service = TelemetryService(db)
    telemetry = service.get_latest(device_id)

    if not telemetry:
        raise HTTPException(
            status_code=404,
            detail=f"No telemetry found for station '{device_id}'"
        )

    station = telemetry.station
    age_seconds = int((datetime.now(timezone.utc) -
                      telemetry.timestamp_utc).total_seconds())

    return TelemetryResponse(
        id=telemetry.id,
        device_id=station.device_id,
        temperature=telemetry.temperature,
        humidity=telemetry.humidity,
        wind_speed_kmh=telemetry.wind_speed_kmh,
        temperature_valid=telemetry.temperature_valid,
        humidity_valid=telemetry.humidity_valid,
        wind_speed_valid=telemetry.wind_speed_valid,
        sensor_status=telemetry.sensor_status,
        reading_type=telemetry.reading_type,
        request_id=telemetry.request_id,
        measured_at=telemetry.timestamp_utc,
        reading_age_seconds=age_seconds
    )


@router.get(
    "/stations/{device_id}/telemetry/history",
    response_model=PaginatedResponse,
    responses={
        404: {"model": ErrorResponse}
    }
)
async def get_telemetry_history(
    device_id: str,
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(100, ge=1, le=1000,
                          description="Elementos por página"),
    start_date: Optional[datetime] = Query(
        None, description="Fecha inicio (ISO format)"),
    end_date: Optional[datetime] = Query(
        None, description="Fecha fin (ISO format)"),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """
    Obtiene el historial de telemetría de una estación con paginación.

    - **device_id**: Identificador de la estación
    - **page**: Número de página
    - **per_page**: Elementos por página (1-1000)
    - **start_date**: Fecha inicio (ISO format)
    - **end_date**: Fecha fin (ISO format)
    """
    service = TelemetryService(db)

    # Calcular offset
    offset = (page - 1) * per_page

    # Obtener datos
    telemetry_list = service.get_history(
        device_id, per_page, offset, start_date, end_date
    )

    # Obtener total
    total = service.get_count(device_id, start_date, end_date)

    # Construir respuesta
    items = []
    for telemetry in telemetry_list:
        station = telemetry.station
        age_seconds = int((datetime.now(timezone.utc) -
                          telemetry.timestamp_utc).total_seconds())
        items.append(
            TelemetryResponse(
                id=telemetry.id,
                device_id=station.device_id,
                temperature=telemetry.temperature,
                humidity=telemetry.humidity,
                wind_speed_kmh=telemetry.wind_speed_kmh,
                temperature_valid=telemetry.temperature_valid,
                humidity_valid=telemetry.humidity_valid,
                wind_speed_valid=telemetry.wind_speed_valid,
                sensor_status=telemetry.sensor_status,
                reading_type=telemetry.reading_type,
                request_id=telemetry.request_id,
                measured_at=telemetry.timestamp_utc,
                reading_age_seconds=age_seconds
            )
        )

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        has_next=page < total_pages,
        has_previous=page > 1,
        total_pages=total_pages
    )
