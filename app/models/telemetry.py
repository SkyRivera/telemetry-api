import uuid
from sqlalchemy import Column, BigInteger, Integer, Numeric, DateTime, String, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(BigInteger, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    temperature = Column(Numeric(5, 2))
    humidity = Column(Numeric(5, 2))
    wind_speed_kmh = Column(Numeric(6, 2))
    measured_at = Column(DateTime(timezone=True))
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    reading_type = Column(String(32), default="periodic")
    request_id = Column(UUID(as_uuid=True), ForeignKey(
        "read_requests.request_id"))
    sensor_status = Column(String(32), default="OK")

    station = relationship("Station", back_populates="telemetry")
