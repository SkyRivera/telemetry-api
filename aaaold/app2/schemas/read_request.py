from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReadRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: UUID
    station_id: int
    status: str
    requested_at: datetime
    dispatched_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime
