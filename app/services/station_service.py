from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.models.station import Station
from fastapi import HTTPException


async def get_station_by_device_id(db: AsyncSession, device_id: str) -> Station:
    result = await db.execute(select(Station).where(Station.device_id == device_id))
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(
            status_code=404, detail=f"Station {device_id} not found")
    return station


async def update_last_seen(db: AsyncSession, station: Station):
    station.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
