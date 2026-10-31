from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.read_request import ReadRequest
from app.models.station import Station


async def create_read_request(
    db: AsyncSession, station: Station, requested_by: str | None = None
) -> ReadRequest:
    request = ReadRequest(
        station_id=station.id,
        status="pending",
        expires_at=datetime.now(timezone.utc)
        + timedelta(seconds=settings.read_request_timeout_seconds),
        requested_by=requested_by,
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request


async def get_pending_commands(
    db: AsyncSession, station: Station, max_items: int = 5
) -> list[ReadRequest]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ReadRequest)
        .where(
            ReadRequest.station_id == station.id,
            ReadRequest.status == "pending",
            ReadRequest.expires_at > now,
        )
        .order_by(ReadRequest.requested_at.asc())
        .limit(max_items)
    )
    requests = list(result.scalars().all())

    for req in requests:
        req.status = "dispatched"
        req.dispatched_at = now
    if requests:
        await db.commit()

    return requests


async def get_read_request(
    db: AsyncSession, request_id: UUID
) -> ReadRequest | None:
    result = await db.execute(
        select(ReadRequest).where(ReadRequest.request_id == request_id)
    )
    return result.scalar_one_or_none()


async def complete_read_request(db: AsyncSession, request_id: UUID) -> None:
    await db.execute(
        update(ReadRequest)
        .where(ReadRequest.request_id == request_id)
        .values(status="completed", completed_at=datetime.now(timezone.utc))
    )
    await db.commit()


async def expire_stale_requests(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(ReadRequest)
        .where(
            ReadRequest.status.in_(["pending", "dispatched"]),
            ReadRequest.expires_at <= now,
        )
        .values(status="timeout")
    )
    await db.commit()
    return result.rowcount or 0
