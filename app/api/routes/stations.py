from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.api.deps import verify_api_b_api_key
from app.models.station import Station
from app.schemas.station import StationResponse

router = APIRouter(prefix="/api/v1/stations", tags=["stations"])


@router.get("", dependencies=[Depends(verify_api_b_api_key)])
async def list_stations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Station))
    stations = result.scalars().all()
    return [
        StationResponse(
            id=s.id, device_id=s.device_id, name=s.name, status=s.status,
            firmware_version=s.firmware_version, created_at=s.created_at,
            last_seen_at=s.last_seen_at,
        )
        for s in stations
    ]
