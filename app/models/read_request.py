import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


class ReadRequest(Base):
    __tablename__ = "read_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(UUID(as_uuid=True), unique=True,
                        nullable=False, default=uuid.uuid4)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    status = Column(String(32), default="pending")
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    dispatched_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    requested_by = Column(String(128))

    station = relationship("Station", back_populates="read_requests")
