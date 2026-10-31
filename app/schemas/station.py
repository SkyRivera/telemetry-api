from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StationResponse(BaseModel):
    id: int
    device_id: str
    name: Optional[str]
    status: str
    firmware_version: Optional[str]
    created_at: datetime
    last_seen_at: Optional[datetime]

    class Config:
        from_attributes = True


class StationStatusResponse(BaseModel):
    device_id: str
    status: str
    last_seen_at: Optional[datetime]
    last_reading_at: Optional[datetime]
    firmware_version: Optional[str]
    recent_errors: list[str] = []
