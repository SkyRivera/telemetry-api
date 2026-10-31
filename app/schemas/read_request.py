from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid


class ReadRequestCreate(BaseModel):
    requested_by: Optional[str] = None


class ReadRequestResponse(BaseModel):
    request_id: uuid.UUID
    station_id: int
    status: str
    requested_at: datetime
    expires_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
