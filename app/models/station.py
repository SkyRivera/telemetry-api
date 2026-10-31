from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255))
    status = Column(String(32), default="active")
    firmware_version = Column(String(32))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True))

    telemetry = relationship("Telemetry", back_populates="station")
    read_requests = relationship("ReadRequest", back_populates="station")
