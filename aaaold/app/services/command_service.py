from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
import logging

from app.models import Station, ReadRequest, RequestStatus

logger = logging.getLogger(__name__)


class CommandService:
    """Servicio para manejar comandos y solicitudes"""

    def __init__(self, db: Session):
        self.db = db

    def create_read_request(
        self,
        device_id: str,
        requested_by: Optional[str] = None,
        timeout_seconds: int = 30
    ) -> Optional[ReadRequest]:
        """
        Crea una nueva solicitud de lectura.

        Args:
            device_id: ID único del dispositivo
            requested_by: Identificador del solicitante
            timeout_seconds: Timeout en segundos

        Returns:
            Optional[ReadRequest]: Solicitud creada o None si no existe la estación
        """
        # Obtener estación
        station = self.db.query(Station).filter(
            Station.device_id == device_id
        ).first()

        if not station:
            logger.warning(f"Estación {device_id} no encontrada")
            return None

        # Verificar si ya hay una solicitud pendiente
        existing = self.db.query(ReadRequest).filter(
            ReadRequest.station_id == station.id,
            ReadRequest.status.in_(
                [RequestStatus.PENDING, RequestStatus.DISPATCHED])
        ).first()

        if existing:
            logger.info(
                f"Solicitud pendiente existente para {device_id}: {existing.id}")
            return existing

        # Crear nueva solicitud
        now = datetime.now(timezone.utc)
        read_request = ReadRequest(
            station_id=station.id,
            requested_by=requested_by,
            status=RequestStatus.PENDING,
            expires_at=now + timedelta(seconds=timeout_seconds)
        )

        self.db.add(read_request)
        self.db.commit()
        self.db.refresh(read_request)

        logger.info(
            f"Solicitud de lectura creada: {read_request.id} para {device_id}")
        return read_request

    def get_pending_commands(self, device_id: str) -> Optional[ReadRequest]:
        """
        Obtiene comandos pendientes para una estación (polling).

        Args:
            device_id: ID único del dispositivo

        Returns:
            Optional[ReadRequest]: Comando pendiente o None
        """
        station = self.db.query(Station).filter(
            Station.device_id == device_id
        ).first()

        if not station:
            logger.warning(f"Estación {device_id} no encontrada para polling")
            return None

        # Buscar solicitudes pendientes no expiradas
        read_request = self.db.query(ReadRequest).filter(
            ReadRequest.station_id == station.id,
            ReadRequest.status == RequestStatus.PENDING,
            ReadRequest.expires_at > datetime.now(timezone.utc)
        ).order_by(ReadRequest.requested_at).first()

        if read_request:
            # Marcar como despachada
            read_request.status = RequestStatus.DISPATCHED
            read_request.dispatched_at = datetime.now(timezone.utc)
            read_request.attempt_count += 1
            self.db.commit()
            self.db.refresh(read_request)
            logger.info(f"Comando {read_request.id} despachado a {device_id}")

        return read_request

    def acknowledge_command(self, device_id: str, request_id: uuid.UUID) -> bool:
        """
        Confirma que el ESP32 recibió el comando.

        Args:
            device_id: ID único del dispositivo
            request_id: ID de la solicitud

        Returns:
            bool: True si se confirmó correctamente
        """
        station = self.db.query(Station).filter(
            Station.device_id == device_id
        ).first()

        if not station:
            logger.warning(f"Estación {device_id} no encontrada para ack")
            return False

        read_request = self.db.query(ReadRequest).filter(
            ReadRequest.id == request_id,
            ReadRequest.station_id == station.id
        ).first()

        if not read_request:
            logger.warning(f"Solicitud {request_id} no encontrada")
            return False

        read_request.status = RequestStatus.DISPATCHED
        read_request.dispatched_at = datetime.now(timezone.utc)
        self.db.commit()

        logger.info(f"Comando {request_id} confirmado por {device_id}")
        return True

    def get_request_status(self, request_id: uuid.UUID) -> Optional[ReadRequest]:
        """
        Obtiene el estado de una solicitud.

        Args:
            request_id: ID de la solicitud

        Returns:
            Optional[ReadRequest]: Solicitud o None
        """
        return self.db.query(ReadRequest).filter(
            ReadRequest.id == request_id
        ).first()

    def cleanup_expired_requests(self) -> int:
        """
        Limpia solicitudes expiradas.

        Returns:
            int: Número de solicitudes expiradas
        """
        now = datetime.now(timezone.utc)
        expired = self.db.query(ReadRequest).filter(
            ReadRequest.status == RequestStatus.PENDING,
            ReadRequest.expires_at < now
        ).all()

        count = len(expired)
        for req in expired:
            req.status = RequestStatus.TIMEOUT
            req.completed_at = now
            logger.info(f"Solicitud {req.id} expirada")

        self.db.commit()
        return count

    def cancel_request(self, request_id: uuid.UUID) -> bool:
        """
        Cancela una solicitud de lectura.

        Args:
            request_id: ID de la solicitud

        Returns:
            bool: True si se canceló correctamente
        """
        read_request = self.db.query(ReadRequest).filter(
            ReadRequest.id == request_id,
            ReadRequest.status.in_(
                [RequestStatus.PENDING, RequestStatus.DISPATCHED])
        ).first()

        if not read_request:
            return False

        read_request.status = RequestStatus.CANCELLED
        read_request.completed_at = datetime.now(timezone.utc)
        self.db.commit()

        logger.info(f"Solicitud {request_id} cancelada")
        return True

    def get_pending_count(self, device_id: str) -> int:
        """
        Obtiene el número de solicitudes pendientes para una estación.

        Args:
            device_id: ID único del dispositivo

        Returns:
            int: Número de solicitudes pendientes
        """
        station = self.db.query(Station).filter(
            Station.device_id == device_id
        ).first()

        if not station:
            return 0

        return self.db.query(ReadRequest).filter(
            ReadRequest.station_id == station.id,
            ReadRequest.status == RequestStatus.PENDING,
            ReadRequest.expires_at > datetime.now(timezone.utc)
        ).count()
