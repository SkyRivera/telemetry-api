from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.station import Station


async def get_station_by_device_id(db: AsyncSession, device_id: str) -> Station:
    result = await db.execute(select(Station).where(Station.device_id == device_id))
    station = result.scalar_one_or_none()
    if station is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Station {device_id} not found",
        )
    return station


async def update_last_seen(db: AsyncSession, station: Station) -> None:
    station.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
