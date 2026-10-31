from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timezone
from typing import Optional
from app.models.telemetry import Telemetry
from app.models.station import Station
from app.schemas.telemetry import TelemetryCreate


async def create_telemetry(db: AsyncSession, station: Station, data: TelemetryCreate) -> Telemetry:
    telemetry = Telemetry(
        station_id=station.id,
        temperature=data.temperature,
        humidity=data.humidity,
        wind_speed_kmh=data.wind_speed_kmh,
        measured_at=data.measured_at or datetime.now(timezone.utc),
        reading_type=data.reading_type,
        request_id=data.request_id,
        sensor_status=data.sensor_status,
    )
    db.add(telemetry)
    await db.commit()
    await db.refresh(telemetry)
    return telemetry


async def get_latest_telemetry(db: AsyncSession, station_id: int) -> Optional[Telemetry]:
    result = await db.execute(
        select(Telemetry)
        .where(Telemetry.station_id == station_id)
        .order_by(desc(Telemetry.received_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_telemetry_history(
    db: AsyncSession,
    station_id: int,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    query = select(Telemetry).where(Telemetry.station_id == station_id)
    if start_date:
        query = query.where(Telemetry.measured_at >= start_date)
    if end_date:
        query = query.where(Telemetry.measured_at <= end_date)
    query = query.order_by(desc(Telemetry.measured_at)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
