from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class TelemetryBase(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    sensor_status: str = "OK"
    measured_at: Optional[datetime] = None


class TelemetryCreate(TelemetryBase):
    device_id: str
    reading_type: str = "periodic"
    request_id: Optional[uuid.UUID] = None


class TelemetryResponse(TelemetryBase):
    id: int
    station_id: int
    received_at: datetime
    reading_type: str
    request_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class TelemetryLatestResponse(BaseModel):
    device_id: str
    temperature: Optional[float]
    humidity: Optional[float]
    wind_speed_kmh: Optional[float]
    measured_at: Optional[datetime]
    received_at: datetime
    reading_type: str
    sensor_status: str

    class Config:
        from_attributes = True
