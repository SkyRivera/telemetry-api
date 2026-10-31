from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone, timedelta
import uuid
from app.models.read_request import ReadRequest
from app.models.station import Station
from app.config import settings


async def create_read_request(db: AsyncSession, station: Station, requested_by: str = None) -> ReadRequest:
    request = ReadRequest(
        station_id=station.id,
        status="pending",
        expires_at=datetime.now(
            timezone.utc) + timedelta(seconds=settings.read_request_timeout_seconds),
        requested_by=requested_by,
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request


async def get_pending_commands(db: AsyncSession, station: Station) -> list[ReadRequest]:
    # Marcar como dispatched las solicitudes pendientes
    result = await db.execute(
        select(ReadRequest)
        .where(
            ReadRequest.station_id == station.id,
            ReadRequest.status == "pending",
            ReadRequest.expires_at > datetime.now(timezone.utc),
        )
        .limit(5)
    )
    requests = result.scalars().all()

    for req in requests:
        req.status = "dispatched"
        req.dispatched_at = datetime.now(timezone.utc)
    await db.commit()

    return requests


async def get_read_request(db: AsyncSession, request_id: uuid.UUID) -> ReadRequest:
    result = await db.execute(
        select(ReadRequest).where(ReadRequest.request_id == request_id)
    )
    return result.scalar_one_or_none()


async def complete_read_request(db: AsyncSession, request_id: uuid.UUID):
    result = await db.execute(
        update(ReadRequest)
        .where(ReadRequest.request_id == request_id)
        .values(status="completed", completed_at=datetime.now(timezone.utc))
    )
    await db.commit()
