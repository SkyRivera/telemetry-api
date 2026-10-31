from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TelemetryCreate(BaseModel):
    device_id: str = Field(..., max_length=64)
    temperature: float | None = Field(None, ge=-50, le=80)
    humidity: float | None = Field(None, ge=0, le=100)
    wind_speed_kmh: float | None = Field(None, ge=0, le=200)
    sensor_status: str = Field(default="OK", max_length=32)
    reading_type: str = Field(default="periodic", max_length=32)
    request_id: UUID | None = None
    measured_at: datetime | None = None


class TelemetryLatestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: str
    temperature: float | None
    humidity: float | None
    wind_speed_kmh: float | None
    measured_at: datetime
    received_at: datetime
    reading_type: str
    sensor_status: str


class TelemetryHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    station_id: int
    temperature: float | None
    humidity: float | None
    wind_speed_kmh: float | None
    measured_at: datetime
    received_at: datetime
    reading_type: str
    request_id: UUID | None
    sensor_status: str
