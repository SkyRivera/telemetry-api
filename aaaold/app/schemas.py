from pydantic import BaseModel, Field, UUID4, validator, ConfigDict
from datetime import datetime, timezone
from typing import Optional, List, Any
from enum import Enum


# ============================================
# ENUMS
# ============================================

class StationStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ReadingType(str, Enum):
    PERIODIC = "periodic"
    ON_DEMAND = "on_demand"


class RequestStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SensorStatus(str, Enum):
    OK = "OK"
    PARTIAL_ERROR = "PARTIAL_ERROR"
    ERROR = "ERROR"


# ============================================
# REQUEST SCHEMAS
# ============================================

class TelemetryCreate(BaseModel):
    """Esquema para recibir telemetría desde el ESP32"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "BOSQUE-001",
                "temperature": 28.4,
                "humidity": 46.2,
                "wind_speed_kmh": 12.7,
                "temperature_valid": True,
                "humidity_valid": True,
                "wind_speed_valid": True,
                "sensor_status": "OK",
                "reading_type": "periodic",
                "timestamp_utc": "2024-01-01T12:00:00Z"
            }
        }
    )

    device_id: str = Field(..., min_length=1, max_length=50,
                           description="ID único del dispositivo")
    temperature: Optional[float] = Field(
        None, ge=-40, le=80, description="Temperatura en °C")
    humidity: Optional[float] = Field(
        None, ge=0, le=100, description="Humedad relativa en %")
    wind_speed_kmh: Optional[float] = Field(
        None, ge=0, description="Velocidad del viento en km/h")

    temperature_valid: bool = Field(
        True, description="¿La temperatura es válida?")
    humidity_valid: bool = Field(True, description="¿La humedad es válida?")
    wind_speed_valid: bool = Field(
        True, description="¿La velocidad del viento es válida?")

    sensor_status: SensorStatus = Field(
        SensorStatus.OK, description="Estado de los sensores")
    reading_type: ReadingType = Field(
        ReadingType.PERIODIC, description="Tipo de lectura")
    request_id: Optional[UUID4] = Field(
        None, description="ID de solicitud si es on_demand")

    timestamp_utc: Optional[datetime] = Field(
        None, description="Timestamp de la lectura")
    wifi_rssi: Optional[int] = Field(
        None, description="Intensidad de señal WiFi")
    firmware_version: Optional[str] = Field(
        None, max_length=20, description="Versión del firmware")

    @validator('timestamp_utc', pre=True, always=True)
    def set_default_timestamp(cls, v):
        """Si no se proporciona timestamp, usar UTC actual"""
        if v is None:
            return datetime.now(timezone.utc)
        return v


class ReadRequestCreate(BaseModel):
    """Esquema para crear una solicitud de lectura"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "requested_by": "api_b_external",
                "timeout_seconds": 30
            }
        }
    )

    requested_by: Optional[str] = Field(
        None, max_length=100, description="Identificador del solicitante")
    timeout_seconds: int = Field(
        30, ge=5, le=120, description="Timeout en segundos")


class CommandPollResponse(BaseModel):
    """Respuesta para polling de comandos del ESP32"""
    has_commands: bool = Field(..., description="¿Hay comandos pendientes?")
    request_id: Optional[UUID4] = Field(None, description="ID de la solicitud")
    command_type: Optional[str] = Field(None, description="Tipo de comando")
    timestamp: Optional[datetime] = Field(
        None, description="Timestamp del comando")


class CommandAck(BaseModel):
    """Acknowledge de comando del ESP32"""
    request_id: UUID4 = Field(...,
                              description="ID de la solicitud a confirmar")


class StationUpdate(BaseModel):
    """Actualización de estación"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Bosque Norte",
                "latitude": 19.4326,
                "longitude": -99.1332,
                "altitude": 2240.0
            }
        }
    )

    name: Optional[str] = Field(
        None, max_length=100, description="Nombre de la estación")
    latitude: Optional[float] = Field(
        None, ge=-90, le=90, description="Latitud")
    longitude: Optional[float] = Field(
        None, ge=-180, le=180, description="Longitud")
    altitude: Optional[float] = Field(None, description="Altitud en metros")


# ============================================
# RESPONSE SCHEMAS
# ============================================

class TelemetryResponse(BaseModel):
    """Respuesta de telemetría"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID4
    device_id: str
    temperature: Optional[float]
    humidity: Optional[float]
    wind_speed_kmh: Optional[float]
    temperature_valid: bool
    humidity_valid: bool
    wind_speed_valid: bool
    sensor_status: SensorStatus
    reading_type: ReadingType
    request_id: Optional[UUID4]
    measured_at: datetime
    reading_age_seconds: Optional[int] = None


class StationStatusResponse(BaseModel):
    """Estado completo de una estación"""
    model_config = ConfigDict(from_attributes=True)

    device_id: str
    name: Optional[str] = None
    status: StationStatus
    last_seen_at: Optional[datetime]
    last_telemetry: Optional[TelemetryResponse] = None
    firmware_version: Optional[str]
    wifi_rssi: Optional[int]
    battery_level: Optional[float]
    is_online: bool
    location: Optional[dict] = None


class ReadRequestResponse(BaseModel):
    """Respuesta de solicitud de lectura"""
    model_config = ConfigDict(from_attributes=True)

    request_id: UUID4
    station_id: UUID4
    device_id: str
    status: RequestStatus
    requested_at: datetime
    dispatched_at: Optional[datetime]
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]
    telemetry: Optional[TelemetryResponse] = None


class ErrorResponse(BaseModel):
    """Respuesta de error estandarizada"""
    status: str = "error"
    message: str
    request_id: Optional[UUID4] = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    details: Optional[dict] = None


class HealthResponse(BaseModel):
    """Respuesta de health check"""
    status: str
    timestamp: datetime
    database: str
    service: str = "telemetry-api"
    version: str = "1.0.0"


class PaginatedResponse(BaseModel):
    """Respuesta paginada"""
    items: List[Any]
    total: int
    page: int = 1
    per_page: int = 100
    has_next: bool = False
    has_previous: bool = False
    total_pages: int = 1
