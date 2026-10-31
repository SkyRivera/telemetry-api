from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from app.models import Station, StationStatus

logger = logging.getLogger(__name__)


class StationService:
    """Servicio para manejar estaciones"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_device_id(self, device_id: str) -> Optional[Station]:
        """
        Obtiene estación por device_id.

        Args:
            device_id: ID único del dispositivo

        Returns:
            Optional[Station]: Estación encontrada o None
        """
        return self.db.query(Station).filter(
            Station.device_id == device_id
        ).first()

    def get_or_create_by_device_id(
        self,
        device_id: str,
        firmware_version: Optional[str] = None,
        rssi: Optional[int] = None
    ) -> Station:
        """
        Obtiene o crea una estación por device_id.

        Args:
            device_id: ID único del dispositivo
            firmware_version: Versión del firmware
            rssi: Intensidad de señal WiFi

        Returns:
            Station: Estación encontrada o creada
        """
        station = self.get_by_device_id(device_id)

        if not station:
            logger.info(f"Creando nueva estación: {device_id}")
            station = Station(
                device_id=device_id,
                firmware_version=firmware_version,
                rssi=rssi,
                status=StationStatus.ONLINE,
                last_seen_at=datetime.utcnow()
            )
            self.db.add(station)
            self.db.flush()
            self.db.refresh(station)
        else:
            # Actualizar información
            station.last_seen_at = datetime.utcnow()
            station.status = StationStatus.ONLINE
            if firmware_version:
                station.firmware_version = firmware_version
            if rssi is not None:
                station.rssi = rssi

        return station

    def update_status(self, device_id: str, status: StationStatus) -> Optional[Station]:
        """
        Actualiza el estado de una estación.

        Args:
            device_id: ID único del dispositivo
            status: Nuevo estado

        Returns:
            Optional[Station]: Estación actualizada o None
        """
        station = self.get_by_device_id(device_id)
        if station:
            station.status = status
            station.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(station)
            logger.info(
                f"Estación {device_id} actualizada a estado {status.value}")
        return station

    def get_online_stations(self, timeout_seconds: int = 600) -> List[Station]:
        """
        Obtiene estaciones que han enviado datos recientemente.

        Args:
            timeout_seconds: Tiempo máximo desde última conexión

        Returns:
            List[Station]: Lista de estaciones online
        """
        cutoff = datetime.utcnow() - timedelta(seconds=timeout_seconds)

        return self.db.query(Station).filter(
            Station.last_seen_at >= cutoff
        ).all()

    def update_metadata(
        self,
        device_id: str,
        name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        altitude: Optional[float] = None
    ) -> Optional[Station]:
        """
        Actualiza metadatos de una estación.

        Args:
            device_id: ID único del dispositivo
            name: Nombre de la estación
            latitude: Latitud
            longitude: Longitud
            altitude: Altitud

        Returns:
            Optional[Station]: Estación actualizada o None
        """
        station = self.get_by_device_id(device_id)
        if not station:
            return None

        if name is not None:
            station.name = name
        if latitude is not None:
            station.latitude = latitude
        if longitude is not None:
            station.longitude = longitude
        if altitude is not None:
            station.altitude = altitude

        station.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(station)

        logger.info(f"Metadatos actualizados para {device_id}")
        return station

    def get_station_summary(self, device_id: str) -> Optional[dict]:
        """
        Obtiene resumen de una estación.

        Args:
            device_id: ID único del dispositivo

        Returns:
            Optional[dict]: Resumen de la estación
        """
        station = self.get_by_device_id(device_id)
        if not station:
            return None

        # Determinar si está online
        is_online = (
            station.last_seen_at and
            (datetime.utcnow() - station.last_seen_at).total_seconds() < 600
        )

        return {
            'device_id': station.device_id,
            'name': station.name,
            'status': station.status,
            'is_online': is_online,
            'last_seen_at': station.last_seen_at,
            'firmware_version': station.firmware_version,
            'rssi': station.rssi,
            'battery_level': station.battery_level,
            'location': {
                'latitude': station.latitude,
                'longitude': station.longitude,
                'altitude': station.altitude
            } if station.latitude is not None else None,
            'created_at': station.created_at
        }

    def delete_station(self, device_id: str) -> bool:
        """
        Elimina una estación y todos sus datos.

        Args:
            device_id: ID único del dispositivo

        Returns:
            bool: True si se eliminó, False si no existe
        """
        station = self.get_by_device_id(device_id)
        if not station:
            return False

        self.db.delete(station)
        self.db.commit()
        logger.info(f"Estación {device_id} eliminada")
        return True
