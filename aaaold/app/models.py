from sqlalchemy import (
    Column, String, Float, Boolean, DateTime,
    Integer, ForeignKey, Index, Enum as SQLEnum,
    Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
import uuid
import enum

from app.database import Base


# ============================================
# ENUMS
# ============================================

class StationStatus(str, enum.Enum):
    """Estados posibles de una estación"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ReadingType(str, enum.Enum):
    """Tipos de lectura"""
    PERIODIC = "periodic"
    ON_DEMAND = "on_demand"


class RequestStatus(str, enum.Enum):
    """Estados de solicitudes de lectura"""
    PENDING = "pending"
    DISPATCHED = "dispatched"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SensorStatus(str, enum.Enum):
    """Estados de los sensores"""
    OK = "OK"
    PARTIAL_ERROR = "PARTIAL_ERROR"
    ERROR = "ERROR"


# ============================================
# MODELOS
# ============================================

class Station(Base):
    """Modelo de estación de monitoreo"""
    __tablename__ = "stations"
    __table_args__ = (
        Index("idx_stations_device_id", "device_id"),
        Index("idx_stations_status", "status"),
        Index("idx_stations_last_seen", "last_seen_at"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=True)

    # Ubicación
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)

    # Estado
    status = Column(SQLEnum(StationStatus), default=StationStatus.OFFLINE)
    firmware_version = Column(String(20), nullable=True)
    wifi_ssid = Column(String(50), nullable=True)
    rssi = Column(Integer, nullable=True)
    battery_level = Column(Float, nullable=True)

    # Timestamps
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    telemetry = relationship(
        "Telemetry",
        back_populates="station",
        cascade="all, delete-orphan",
        lazy="select"
    )
    read_requests = relationship(
        "ReadRequest",
        back_populates="station",
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self):
        return f"<Station(device_id='{self.device_id}', status={self.status})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "device_id": self.device_id,
            "name": self.name,
            "status": self.status.value if self.status else None,
            "firmware_version": self.firmware_version,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Telemetry(Base):
    """Modelo de datos de telemetría"""
    __tablename__ = "telemetry"
    __table_args__ = (
        Index("idx_telemetry_station_time", "station_id", "timestamp_utc"),
        Index("idx_telemetry_timestamp", "timestamp_utc"),
        Index("idx_telemetry_reading_type", "reading_type"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    station_id = Column(PGUUID(as_uuid=True), ForeignKey(
        "stations.id"), nullable=False)

    # Datos de sensores
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    wind_speed_kmh = Column(Float, nullable=True)

    # Validación
    temperature_valid = Column(Boolean, default=True)
    humidity_valid = Column(Boolean, default=True)
    wind_speed_valid = Column(Boolean, default=True)

    # Metadatos
    sensor_status = Column(SQLEnum(SensorStatus), default=SensorStatus.OK)
    reading_type = Column(SQLEnum(ReadingType), default=ReadingType.PERIODIC)

    # Relación con solicitud
    request_id = Column(PGUUID(as_uuid=True), ForeignKey(
        "read_requests.id"), nullable=True)

    # Timestamps
    timestamp_utc = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    station = relationship("Station", back_populates="telemetry")
    read_request = relationship(
        "ReadRequest", back_populates="telemetry", uselist=False)

    def __repr__(self):
        return f"<Telemetry(station_id={self.station_id}, temp={self.temperature})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "temperature": self.temperature,
            "humidity": self.humidity,
            "wind_speed_kmh": self.wind_speed_kmh,
            "sensor_status": self.sensor_status.value if self.sensor_status else None,
            "reading_type": self.reading_type.value if self.reading_type else None,
            "timestamp_utc": self.timestamp_utc.isoformat() if self.timestamp_utc else None
        }


class ReadRequest(Base):
    """Modelo de solicitudes de lectura bajo demanda"""
    __tablename__ = "read_requests"
    __table_args__ = (
        Index("idx_read_requests_station_status", "station_id", "status"),
        Index("idx_read_requests_status", "status"),
        Index("idx_read_requests_expires", "expires_at"),
    )

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    station_id = Column(PGUUID(as_uuid=True), ForeignKey(
        "stations.id"), nullable=False)

    # Estado
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING)
    requested_by = Column(String(100), nullable=True)
    attempt_count = Column(Integer, default=0)

    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relaciones
    station = relationship("Station", back_populates="read_requests")
    telemetry = relationship(
        "Telemetry", back_populates="read_request", uselist=False)

    def __repr__(self):
        return f"<ReadRequest(id={self.id}, status={self.status})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "status": self.status.value if self.status else None,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
