from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    station_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stations.id", ondelete="CASCADE"), nullable=False
    )
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    humidity: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    wind_speed_kmh: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reading_type: Mapped[str] = mapped_column(String(32), default="periodic")
    request_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("read_requests.request_id", ondelete="SET NULL"),
    )
    sensor_status: Mapped[str] = mapped_column(String(32), default="OK")

    station = relationship("Station", back_populates="telemetry")
