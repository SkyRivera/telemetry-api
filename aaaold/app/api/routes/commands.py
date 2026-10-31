from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import asyncio
from datetime import datetime, timezone
import logging

from app.database import get_db
from app.schemas import (
    ReadRequestResponse, TelemetryResponse, ErrorResponse,
    RequestStatus
)
from app.services.command_service import CommandService
from app.services.telemetry_service import TelemetryService
from app.security import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/telemetry", tags=["commands"])


@router.get(
    "/read-request/{request_id}",
    response_model=ReadRequestResponse,
    responses={
        404: {"model": ErrorResponse}
    }
)
async def get_read_request_status(
    request_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """
    Obtiene el estado de una solicitud de lectura.

    - **request_id**: UUID de la solicitud
    """
    import uuid
    try:
        request_uuid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid request_id format"
        )

    command_service = CommandService(db)
    read_request = command_service.get_request_status(request_uuid)

    if not read_request:
        raise HTTPException(
            status_code=404,
            detail=f"Request '{request_id}' not found"
        )

    # Obtener telemetría asociada si está completada
    telemetry_response = None
    if read_request.status == RequestStatus.COMPLETED and read_request.telemetry:
        telemetry = read_request.telemetry
        station = read_request.station
        age_seconds = int((datetime.now(timezone.utc) -
                          telemetry.timestamp_utc).total_seconds())
        telemetry_response = TelemetryResponse(
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

    return ReadRequestResponse(
        request_id=read_request.id,
        station_id=read_request.station_id,
        device_id=read_request.station.device_id,
        status=read_request.status,
        requested_at=read_request.requested_at,
        dispatched_at=read_request.dispatched_at,
        completed_at=read_request.completed_at,
        expires_at=read_request.expires_at,
        telemetry=telemetry_response
    )


@router.get(
    "/read-request/{request_id}/wait",
    response_model=ReadRequestResponse,
    responses={
        404: {"model": ErrorResponse},
        408: {"model": ErrorResponse}
    }
)
async def wait_for_read_request(
    request_id: str,
    timeout_seconds: int = Query(30, ge=5, le=120),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """
    Espera a que una solicitud de lectura se complete (polling con timeout).

    - **request_id**: UUID de la solicitud
    - **timeout_seconds**: Tiempo máximo de espera en segundos
    """
    import uuid
    try:
        request_uuid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid request_id format"
        )

    command_service = CommandService(db)

    # Validar que la solicitud existe
    read_request = command_service.get_request_status(request_uuid)
    if not read_request:
        raise HTTPException(
            status_code=404,
            detail=f"Request '{request_id}' not found"
        )

    # Si ya está completada, devolver inmediatamente
    if read_request.status in [
        RequestStatus.COMPLETED,
        RequestStatus.TIMEOUT,
        RequestStatus.FAILED,
        RequestStatus.CANCELLED
    ]:
        return await get_read_request_status(request_id, db, _)

    # Esperar a que se complete
    start_time = datetime.now(timezone.utc)
    poll_interval = 0.5  # segundos

    while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout_seconds:
        read_request = command_service.get_request_status(request_uuid)

        if read_request.status in [
            RequestStatus.COMPLETED,
            RequestStatus.TIMEOUT,
            RequestStatus.FAILED,
            RequestStatus.CANCELLED
        ]:
            break

        await asyncio.sleep(poll_interval)

    # Si aún está pendiente, marcar como timeout
    if read_request.status == RequestStatus.PENDING:
        read_request.status = RequestStatus.TIMEOUT
        read_request.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(read_request)
        logger.info(f"Solicitud {request_id} expiró por timeout")

    # Devolver resultado final
    return await get_read_request_status(request_id, db, _)


@router.delete(
    "/read-request/{request_id}",
    response_model=dict,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse}
    }
)
async def cancel_read_request(
    request_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """
    Cancela una solicitud de lectura pendiente.

    - **request_id**: UUID de la solicitud
    """
    import uuid
    try:
        request_uuid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid request_id format"
        )

    command_service = CommandService(db)

    # Verificar estado actual
    read_request = command_service.get_request_status(request_uuid)
    if not read_request:
        raise HTTPException(
            status_code=404,
            detail=f"Request '{request_id}' not found"
        )

    if read_request.status not in [RequestStatus.PENDING, RequestStatus.DISPATCHED]:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel request in status: {read_request.status.value}"
        )

    success = command_service.cancel_request(request_uuid)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel request"
        )

    return {"status": "cancelled", "request_id": str(request_id)}
