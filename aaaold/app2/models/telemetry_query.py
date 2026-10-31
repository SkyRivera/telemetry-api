from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class TelemetryQuery(Base):
    __tablename__ = "telemetry_queries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    station_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("stations.id", ondelete="SET NULL")
    )
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    query_type: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    client_identifier: Mapped[str | None] = mapped_column(String(128))
    request_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    response_status: Mapped[int | None] = mapped_column(Integer)
    telemetry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("telemetry.id", ondelete="SET NULL")
    )
