from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_api_b_api_key
from app.db.database import get_db
from app.models.station import Station
from app.schemas.station import StationResponse

router = APIRouter(
    prefix="/api/v1/stations",
    tags=["stations"],
    dependencies=[Depends(verify_api_b_api_key)],
)


@router.get("", response_model=list[StationResponse])
async def list_stations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Station).order_by(Station.device_id))
    return list(result.scalars().all())
