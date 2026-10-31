from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.schemas import (
    StationStatusResponse, ReadRequestCreate, ReadRequestResponse,
    CommandPollResponse, CommandAck, ErrorResponse, StationUpdate,
    TelemetryResponse
)
from app.services.telemetry_service import TelemetryService
from app.services.command_service import CommandService
from app.services.station_service import StationService
from app.security import verify_api_key, verify_iot_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/stations", tags=["stations"])


@router.get(
    "/{device_id}/status",
    response_model=StationStatusResponse,
    responses={
        404: {"model": ErrorResponse}
    }
)
async def get_station_status(
    device_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """
    Obtiene el estado completo de una estación.

    - **device_id**: Identificador de la estación
    """
    station_service = StationService(db)
    station = station_service.get_by_device_id(device_id)

    if not station:
        raise HTTPException(
            status_code=404,
            detail=f"Station '{device_id}' not found"
        )

    # Obtener última telemetría
    telemetry_service = TelemetryService(db)
    latest = telemetry_service.get_latest(device_id)

    last_telemetry = None
    if latest:
        age_seconds = int((datetime.now(timezone.utc) -
                          latest.timestamp_utc).total_seconds())
        last_telemetry = TelemetryResponse(
            id=latest.id,
            device_id=station.device_id,
            temperature=latest.temperature,
            humidity=latest.humidity,
            wind_speed_kmh=latest.wind_speed_kmh,
            temperature_valid=latest.temperature_valid,
            humidity_valid=latest.humidity_valid,
            wind_speed_valid=latest.wind_speed_valid,
            sensor_status=latest.sensor_status,
            reading_type=latest.reading_type,
            request_id=latest.request_id,
            measured_at=latest.timestamp_utc,
            reading_age_seconds=age_seconds
        )

    # Determinar si está online
    is_online = (
        station.last_seen_at is not None and
        (datetime.now(timezone.utc) - station.last_seen_at).total_seconds() < 600
    )

    # Preparar ubicación
    location = None
    if station.latitude is not None:
        location = {
            "latitude": station.latitude,
            "longitude": station.longitude,
            "altitude": station.altitude
        }

    return StationStatusResponse(
        device_id=station.device_id,
        name=station.name,
        status=station.status,
        last_seen_at=station.last_seen_at,
        last_telemetry=last_telemetry,
        firmware_version=station.firmware_version,
        wifi_rssi=station.rssi,
        battery_level=station.battery_level,
        is_online=is_online,
        location=location
    )


@router.post(
    "/{device_id}/read-request",
    response_model=ReadRequestResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse}
    }
)
async def request_read(
    device_id: str,
    request_data: ReadRequestCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """
    Solicita una lectura bajo demanda a una estación.

    - **device_id**: Identificador de la estación
    - **requested_by**: Identificador del solicitante (opcional)
    - **timeout_seconds**: Timeout en segundos (5-120)

    Retorna un request_id para consultar el estado.
    """
    command_service = CommandService(db)
    station_service = StationService(db)

    # Verificar que la estación existe
    station = station_service.get_by_device_id(device_id)
    if not station:
        raise HTTPException(
            status_code=404,
            detail=f"Station '{device_id}' not found"
        )

    # Verificar si hay solicitudes pendientes
    pending_count = command_service.get_pending_count(device_id)
    if pending_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"There are {pending_count} pending request(s) for this station"
        )

    # Crear solicitud
    read_request = command_service.create_read_request(
        device_id,
        request_data.requested_by,
        request_data.timeout_seconds
    )

    if not read_request:
        raise HTTPException(
            status_code=500,
            detail="Failed to create read request"
        )

    return ReadRequestResponse(
        request_id=read_request.id,
        station_id=read_request.station_id,
        device_id=device_id,
        status=read_request.status,
        requested_at=read_request.requested_at,
        dispatched_at=read_request.dispatched_at,
        completed_at=read_request.completed_at,
        expires_at=read_request.expires_at,
        telemetry=None
    )


@router.patch(
    "/{device_id}",
    response_model=StationStatusResponse,
    responses={
        404: {"model": ErrorResponse}
    }
)
async def update_station(
    device_id: str,
    update_data: StationUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """
    Actualiza metadatos de una estación.

    - **device_id**: Identificador de la estación
    - **name**: Nombre de la estación
    - **latitude**: Latitud (-90 a 90)
    - **longitude**: Longitud (-180 a 180)
    - **altitude**: Altitud en metros
    """
    station_service = StationService(db)
    station = station_service.update_metadata(
        device_id,
        update_data.name,
        update_data.latitude,
        update_data.longitude,
        update_data.altitude
    )

    if not station:
        raise HTTPException(
            status_code=404,
            detail=f"Station '{device_id}' not found"
        )

    # Obtener última telemetría
    telemetry_service = TelemetryService(db)
    latest = telemetry_service.get_latest(device_id)

    last_telemetry = None
    if latest:
        last_telemetry = TelemetryResponse(
            id=latest.id,
            device_id=station.device_id,
            temperature=latest.temperature,
            humidity=latest.humidity,
            wind_speed_kmh=latest.wind_speed_kmh,
            temperature_valid=latest.temperature_valid,
            humidity_valid=latest.humidity_valid,
            wind_speed_valid=latest.wind_speed_valid,
            sensor_status=latest.sensor_status,
            reading_type=latest.reading_type,
            request_id=latest.request_id,
            measured_at=latest.timestamp_utc,
            reading_age_seconds=0
        )

    location = None
    if station.latitude is not None:
        location = {
            "latitude": station.latitude,
            "longitude": station.longitude,
            "altitude": station.altitude
        }

    return StationStatusResponse(
        device_id=station.device_id,
        name=station.name,
        status=station.status,
        last_seen_at=station.last_seen_at,
        last_telemetry=last_telemetry,
        firmware_version=station.firmware_version,
        wifi_rssi=station.rssi,
        battery_level=station.battery_level,
        is_online=True,
        location=location
    )


@router.get(
    "/{device_id}/commands/pending",
    response_model=CommandPollResponse
)
async def get_pending_commands(
    device_id: str,
    db: Session = Depends(get_db),
    auth_data: dict = Depends(verify_iot_api_key)
):
    """
    Endpoint para que el ESP32 consulte comandos pendientes.
    """
    command_service = CommandService(db)
    read_request = command_service.get_pending_commands(device_id)

    if read_request:
        return CommandPollResponse(
            has_commands=True,
            request_id=read_request.id,
            command_type="read_sensors",
            timestamp=read_request.requested_at
        )

    return CommandPollResponse(has_commands=False)


@router.post(
    "/{device_id}/commands/ack",
    response_model=dict,
    responses={
        404: {"model": ErrorResponse}
    }
)
async def acknowledge_command(
    device_id: str,
    command_ack: CommandAck,
    db: Session = Depends(get_db),
    auth_data: dict = Depends(verify_iot_api_key)
):
    """
    Endpoint para que el ESP32 confirme la recepción de un comando.
    """
    command_service = CommandService(db)
    success = command_service.acknowledge_command(
        device_id, command_ack.request_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Command not found or already acknowledged"
        )

    return {"status": "acknowledged", "request_id": str(command_ack.request_id)}


@router.get(
    "/all/online",
    response_model=List[StationStatusResponse]
)
async def get_online_stations(
    timeout_seconds: int = Query(
        600, description="Tiempo máximo desde última conexión"),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """
    Obtiene todas las estaciones online.

    - **timeout_seconds**: Tiempo máximo en segundos desde última conexión
    """
    station_service = StationService(db)
    stations = station_service.get_online_stations(timeout_seconds)

    result = []
    for station in stations:
        # Obtener última telemetría
        telemetry_service = TelemetryService(db)
        latest = telemetry_service.get_latest(station.device_id)

        last_telemetry = None
        if latest:
            last_telemetry = TelemetryResponse(
                id=latest.id,
                device_id=station.device_id,
                temperature=latest.temperature,
                humidity=latest.humidity,
                wind_speed_kmh=latest.wind_speed_kmh,
                temperature_valid=latest.temperature_valid,
                humidity_valid=latest.humidity_valid,
                wind_speed_valid=latest.wind_speed_valid,
                sensor_status=latest.sensor_status,
                reading_type=latest.reading_type,
                request_id=latest.request_id,
                measured_at=latest.timestamp_utc,
                reading_age_seconds=0
            )

        location = None
        if station.latitude is not None:
            location = {
                "latitude": station.latitude,
                "longitude": station.longitude,
                "altitude": station.altitude
            }

        result.append(StationStatusResponse(
            device_id=station.device_id,
            name=station.name,
            status=station.status,
            last_seen_at=station.last_seen_at,
            last_telemetry=last_telemetry,
            firmware_version=station.firmware_version,
            wifi_rssi=station.rssi,
            battery_level=station.battery_level,
            is_online=True,
            location=location
        ))

    return result
