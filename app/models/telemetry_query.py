from sqlalchemy import Column, BigInteger, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base


class TelemetryQuery(Base):
    __tablename__ = "telemetry_queries"

    id = Column(BigInteger, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.id"))
    endpoint = Column(String(255), nullable=False)
    query_type = Column(String(32), nullable=False)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    client_identifier = Column(String(128))
    request_id = Column(UUID(as_uuid=True))
    response_status = Column(Integer)
    telemetry_id = Column(BigInteger, ForeignKey("telemetry.id"))
