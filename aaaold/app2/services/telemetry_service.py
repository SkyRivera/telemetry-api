from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.station import Station
from app.models.telemetry import Telemetry
from app.schemas.telemetry import TelemetryCreate


def _to_decimal(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


async def create_telemetry(
    db: AsyncSession, station: Station, data: TelemetryCreate
) -> Telemetry:
    telemetry = Telemetry(
        station_id=station.id,
        temperature=_to_decimal(data.temperature),
        humidity=_to_decimal(data.humidity),
        wind_speed_kmh=_to_decimal(data.wind_speed_kmh),
        measured_at=data.measured_at or datetime.now(timezone.utc),
        reading_type=data.reading_type,
        request_id=data.request_id,
        sensor_status=data.sensor_status,
    )
    db.add(telemetry)
    await db.commit()
    await db.refresh(telemetry)
    return telemetry


async def get_latest_telemetry(
    db: AsyncSession, station_id: int
) -> Telemetry | None:
    result = await db.execute(
        select(Telemetry)
        .where(Telemetry.station_id == station_id)
        .order_by(Telemetry.received_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_telemetry_history(
    db: AsyncSession,
    station_id: int,
    limit: int = 100,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[Telemetry]:
    query = select(Telemetry).where(Telemetry.station_id == station_id)
    if start_date is not None:
        query = query.where(Telemetry.measured_at >= start_date)
    if end_date is not None:
        query = query.where(Telemetry.measured_at <= end_date)
    query = query.order_by(Telemetry.measured_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
