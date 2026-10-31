from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_esp32_api_key
from app.db.database import get_db
from app.services import command_service, station_service

router = APIRouter(prefix="/api/v1/commands", tags=["commands"])


@router.get("/pending", dependencies=[Depends(verify_esp32_api_key)])
async def get_pending_commands(
    device_id: str = Query(..., max_length=64),
    db: AsyncSession = Depends(get_db),
):
    station = await station_service.get_station_by_device_id(db, device_id)
    requests = await command_service.get_pending_commands(db, station)

    return {
        "commands": [
            {
                "type": "read_now",
                "request_id": str(req.request_id),
                "station_id": station.device_id,
            }
            for req in requests
        ]
    }
