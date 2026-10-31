from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional
import uuid

from app.db.database import get_db
from app.api.deps import verify_esp32_api_key, verify_api_b_api_key
from app.schemas.telemetry import TelemetryCreate, TelemetryLatestResponse, TelemetryResponse
from app.services import telemetry_service, station_service
from app.models.telemetry_query import TelemetryQuery
from app.models.telemetry import Telemetry

router = APIRouter(prefix="/api/v1", tags=["telemetry"])


@router.post("/telemetry", dependencies=[Depends(verify_esp32_api_key)])
async def ingest_telemetry(
    data: TelemetryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Ingesta de telemetría desde ESP32."""
    station = await station_service.get_station_by_device_id(db, data.device_id)
    telemetry = await telemetry_service.create_telemetry(db, station, data)
    await station_service.update_last_seen(db, station)

    # Si viene de un read_request, completarlo
    if data.request_id:
        from app.services import command_service
        await command_service.complete_read_request(db, data.request_id)

    return {"status": "ok", "telemetry_id": telemetry.id}


@router.get("/stations/{device_id}/telemetry/latest", dependencies=[Depends(verify_api_b_api_key)])
async def get_latest(
    device_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Última lectura conocida. Registra la consulta."""
    station = await station_service.get_station_by_device_id(db, device_id)
    telemetry = await telemetry_service.get_latest_telemetry(db, station.id)

    # Registrar consulta
    query_log = TelemetryQuery(
        station_id=station.id,
        endpoint=f"/stations/{device_id}/telemetry/latest",
        query_type="latest",
        client_identifier=request.client.host if request.client else None,
        response_status=200 if telemetry else 404,
        telemetry_id=telemetry.id if telemetry else None,
    )
    db.add(query_log)
    await db.commit()

    if not telemetry:
        raise HTTPException(status_code=404, detail="No telemetry found")

    return TelemetryLatestResponse(
        device_id=station.device_id,
        temperature=float(
            telemetry.temperature) if telemetry.temperature else None,
        humidity=float(telemetry.humidity) if telemetry.humidity else None,
        wind_speed_kmh=float(
            telemetry.wind_speed_kmh) if telemetry.wind_speed_kmh else None,
        measured_at=telemetry.measured_at,
        received_at=telemetry.received_at,
        reading_type=telemetry.reading_type,
        sensor_status=telemetry.sensor_status,
    )


@router.get("/stations/{device_id}/telemetry/history", dependencies=[Depends(verify_api_b_api_key)])
async def get_history(
    device_id: str,
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """Historial de lecturas. Registra la consulta."""
    station = await station_service.get_station_by_device_id(db, device_id)
    readings = await telemetry_service.get_telemetry_history(
        db, station.id, limit, start_date, end_date
    )

    query_log = TelemetryQuery(
        station_id=station.id,
        endpoint=f"/stations/{device_id}/telemetry/history",
        query_type="history",
        client_identifier=request.client.host if request.client else None,
        response_status=200,
    )
    db.add(query_log)
    await db.commit()

    return [
        TelemetryResponse(
            id=r.id,
            station_id=r.station_id,
            temperature=float(r.temperature) if r.temperature else None,
            humidity=float(r.humidity) if r.humidity else None,
            wind_speed_kmh=float(
                r.wind_speed_kmh) if r.wind_speed_kmh else None,
            sensor_status=r.sensor_status,
            measured_at=r.measured_at,
            received_at=r.received_at,
            reading_type=r.reading_type,
            request_id=r.request_id,
        )
        for r in readings
    ]


@router.post("/stations/{device_id}/telemetry/read-request", dependencies=[Depends(verify_api_b_api_key)])
async def request_reading(
    device_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Solicita una medición física nueva. Registra la solicitud."""
    station = await station_service.get_station_by_device_id(db, device_id)

    from app.services import command_service
    read_request = await command_service.create_read_request(
        db, station, requested_by=request.client.host if request.client else None
    )

    query_log = TelemetryQuery(
        station_id=station.id,
        endpoint=f"/stations/{device_id}/telemetry/read-request",
        query_type="read_request",
        client_identifier=request.client.host if request.client else None,
        request_id=read_request.request_id,
        response_status=202,
    )
    db.add(query_log)
    await db.commit()

    return {
        "request_id": str(read_request.request_id),
        "status": read_request.status,
        "expires_at": read_request.expires_at.isoformat(),
    }


@router.get("/telemetry/read-request/{request_id}", dependencies=[Depends(verify_api_b_api_key)])
async def get_read_request_status(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Consulta el estado de una solicitud de lectura."""
    from app.services import command_service
    req = await command_service.get_read_request(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Read request not found")

    return {
        "request_id": str(req.request_id),
        "station_id": req.station_id,
        "status": req.status,
        "requested_at": req.requested_at.isoformat(),
        "completed_at": req.completed_at.isoformat() if req.completed_at else None,
        "expires_at": req.expires_at.isoformat(),
    }


@router.get("/stations/{device_id}/status", dependencies=[Depends(verify_api_b_api_key)])
async def get_station_status(
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Estado de la estación."""
    station = await station_service.get_station_by_device_id(db, device_id)

    # Última telemetría
    latest = await telemetry_service.get_latest_telemetry(db, station.id)

    return {
        "device_id": station.device_id,
        "status": station.status,
        "last_seen_at": station.last_seen_at.isoformat() if station.last_seen_at else None,
        "last_reading_at": latest.received_at.isoformat() if latest else None,
        "firmware_version": station.firmware_version,
        "recent_errors": [],
    }
