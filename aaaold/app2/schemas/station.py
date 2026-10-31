from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    name: str | None
    status: str
    firmware_version: str | None
    created_at: datetime
    last_seen_at: datetime | None


class StationStatusResponse(BaseModel):
    device_id: str
    status: str
    last_seen_at: datetime | None
    last_reading_at: datetime | None
    firmware_version: str | None
    recent_errors: list[str] = []
