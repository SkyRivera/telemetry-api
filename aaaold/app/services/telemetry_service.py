from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import logging

from app.models import StationStatus, Telemetry, ReadRequest, RequestStatus, ReadingType, SensorStatus
from app.schemas import TelemetryCreate
from app.services.station_service import StationService

logger = logging.getLogger(__name__)


class TelemetryService:
    """Servicio para manejar telemetría"""

    def __init__(self, db: Session):
        self.db = db
        self.station_service = StationService(db)

    def process_telemetry(self, telemetry_data: TelemetryCreate) -> Telemetry:
        """
        Procesa y almacena datos de telemetría.

        Args:
            telemetry_data: Datos de telemetría recibidos

        Returns:
            Telemetry: Registro de telemetría creado
        """
        logger.info(f"Procesando telemetría de {telemetry_data.device_id}")

        # Obtener o crear estación
        station = self.station_service.get_or_create_by_device_id(
            device_id=telemetry_data.device_id,
            firmware_version=telemetry_data.firmware_version,
            rssi=telemetry_data.wifi_rssi
        )

        # Actualizar estado de la estación
        station.last_seen_at = datetime.now(timezone.utc)
        station.status = StationStatus.ONLINE

        if telemetry_data.wifi_rssi is not None:
            station.rssi = telemetry_data.wifi_rssi

        if telemetry_data.firmware_version:
            station.firmware_version = telemetry_data.firmware_version

        # Determinar estado de sensores
        valid_count = sum([
            telemetry_data.temperature_valid,
            telemetry_data.humidity_valid,
            telemetry_data.wind_speed_valid
        ])

        if valid_count == 3:
            sensor_status = SensorStatus.OK
        elif valid_count > 0:
            sensor_status = SensorStatus.PARTIAL_ERROR
        else:
            sensor_status = SensorStatus.ERROR

        # Crear registro de telemetría
        telemetry = Telemetry(
            station_id=station.id,
            temperature=telemetry_data.temperature if telemetry_data.temperature_valid else None,
            humidity=telemetry_data.humidity if telemetry_data.humidity_valid else None,
            wind_speed_kmh=telemetry_data.wind_speed_kmh if telemetry_data.wind_speed_valid else None,
            temperature_valid=telemetry_data.temperature_valid,
            humidity_valid=telemetry_data.humidity_valid,
            wind_speed_valid=telemetry_data.wind_speed_valid,
            sensor_status=sensor_status,
            reading_type=telemetry_data.reading_type,
            timestamp_utc=telemetry_data.timestamp_utc or datetime.now(
                timezone.utc),
            request_id=telemetry_data.request_id
        )

        self.db.add(telemetry)
        self.db.flush()

        # Actualizar solicitud de lectura si existe
        if (telemetry_data.reading_type == ReadingType.ON_DEMAND and
                telemetry_data.request_id):
            read_request = self.db.query(ReadRequest).filter(
                ReadRequest.id == telemetry_data.request_id
            ).first()

            if read_request:
                read_request.status = RequestStatus.COMPLETED
                read_request.completed_at = datetime.now(timezone.utc)
                logger.info(f"Solicitud {read_request.id} completada")

        self.db.commit()
        self.db.refresh(telemetry)

        logger.info(f"Telemetría almacenada: {telemetry.id}")
        return telemetry

    def get_latest(self, device_id: str) -> Optional[Telemetry]:
        """
        Obtiene la última lectura de telemetría de una estación.

        Args:
            device_id: ID único del dispositivo

        Returns:
            Optional[Telemetry]: Última lectura o None
        """
        station = self.station_service.get_by_device_id(device_id)
        if not station:
            return None

        return self.db.query(Telemetry).filter(
            Telemetry.station_id == station.id
        ).order_by(desc(Telemetry.timestamp_utc)).first()

    def get_history(
        self,
        device_id: str,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Telemetry]:
        """
        Obtiene historial de telemetría con filtros opcionales.

        Args:
            device_id: ID único del dispositivo
            limit: Límite de registros
            offset: Desplazamiento para paginación
            start_date: Fecha inicio
            end_date: Fecha fin

        Returns:
            List[Telemetry]: Lista de lecturas
        """
        station = self.station_service.get_by_device_id(device_id)
        if not station:
            return []

        query = self.db.query(Telemetry).filter(
            Telemetry.station_id == station.id
        )

        if start_date:
            query = query.filter(Telemetry.timestamp_utc >= start_date)
        if end_date:
            query = query.filter(Telemetry.timestamp_utc <= end_date)

        return query.order_by(desc(Telemetry.timestamp_utc)).offset(offset).limit(limit).all()

    def get_count(
        self,
        device_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Obtiene el número total de lecturas con filtros.

        Args:
            device_id: ID único del dispositivo
            start_date: Fecha inicio
            end_date: Fecha fin

        Returns:
            int: Número total de lecturas
        """
        station = self.station_service.get_by_device_id(device_id)
        if not station:
            return 0

        query = self.db.query(Telemetry).filter(
            Telemetry.station_id == station.id
        )

        if start_date:
            query = query.filter(Telemetry.timestamp_utc >= start_date)
        if end_date:
            query = query.filter(Telemetry.timestamp_utc <= end_date)

        return query.count()

    def get_latest_reading_age(self, device_id: str) -> Optional[int]:
        """
        Calcula la antigüedad de la última lectura en segundos.

        Args:
            device_id: ID único del dispositivo

        Returns:
            Optional[int]: Antigüedad en segundos o None
        """
        latest = self.get_latest(device_id)
        if not latest:
            return None

        return int((datetime.now(timezone.utc) - latest.timestamp_utc).total_seconds())

    def get_average_metrics(
        self,
        device_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Calcula métricas promedio de las últimas horas.

        Args:
            device_id: ID único del dispositivo
            hours: Número de horas hacia atrás

        Returns:
            dict: Métricas calculadas
        """
        station = self.station_service.get_by_device_id(device_id)
        if not station:
            return {}

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Calcular promedios
        metrics = self.db.query(
            func.avg(Telemetry.temperature).label('avg_temp'),
            func.avg(Telemetry.humidity).label('avg_hum'),
            func.avg(Telemetry.wind_speed_kmh).label('avg_wind'),
            func.count(Telemetry.id).label('total_readings'),
            func.sum(func.cast(Telemetry.temperature_valid,
                     func.Integer())).label('valid_temp'),
            func.sum(func.cast(Telemetry.humidity_valid,
                     func.Integer())).label('valid_hum'),
            func.sum(func.cast(Telemetry.wind_speed_valid,
                     func.Integer())).label('valid_wind')
        ).filter(
            Telemetry.station_id == station.id,
            Telemetry.timestamp_utc >= since
        ).first()

        if not metrics or not metrics.total_readings:
            return {
                'period_hours': hours,
                'avg_temperature': None,
                'avg_humidity': None,
                'avg_wind_speed': None,
                'total_readings': 0,
                'valid_readings_ratio': {
                    'temperature': 0.0,
                    'humidity': 0.0,
                    'wind': 0.0
                }
            }

        return {
            'period_hours': hours,
            'avg_temperature': float(metrics.avg_temp) if metrics.avg_temp is not None else None,
            'avg_humidity': float(metrics.avg_hum) if metrics.avg_hum is not None else None,
            'avg_wind_speed': float(metrics.avg_wind) if metrics.avg_wind is not None else None,
            'total_readings': metrics.total_readings or 0,
            'valid_readings_ratio': {
                'temperature': (metrics.valid_temp or 0) / metrics.total_readings if metrics.total_readings else 0,
                'humidity': (metrics.valid_hum or 0) / metrics.total_readings if metrics.total_readings else 0,
                'wind': (metrics.valid_wind or 0) / metrics.total_readings if metrics.total_readings else 0
            }
        }

    def clean_old_telemetry(self, days_to_keep: int = 30) -> int:
        """
        Elimina telemetría más antigua que el período especificado.

        Args:
            days_to_keep: Días a mantener

        Returns:
            int: Número de registros eliminados
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        deleted = self.db.query(Telemetry).filter(
            Telemetry.timestamp_utc < cutoff
        ).delete()

        self.db.commit()
        logger.info(f"Eliminados {deleted} registros de telemetría antiguos")
        return deleted
