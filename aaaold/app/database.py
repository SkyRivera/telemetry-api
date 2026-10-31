from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Crear engine con pool de conexiones optimizado
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.POSTGRES_POOL_SIZE,
    max_overflow=settings.POSTGRES_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verificar conexiones antes de usarlas
    pool_recycle=settings.POSTGRES_POOL_RECYCLE,
    pool_timeout=settings.POSTGRES_POOL_TIMEOUT,
    echo=settings.DEBUG,
    echo_pool=settings.DEBUG
)

# Evento para logging de conexiones


@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    logger.debug("Nueva conexión a PostgreSQL establecida")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    logger.debug("Conexión obtenida del pool")


# Crear fábrica de sesiones
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para modelos declarativos
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Generador de sesiones de base de datos.

    Uso como dependencia en FastAPI:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Error en sesión de base de datos: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_database():
    """
    Inicializa la base de datos creando tablas si no existen.
    """
    try:
        logger.info("Creando tablas de base de datos...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tablas creadas exitosamente")
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {e}")
        raise


def get_connection_info():
    """
    Obtiene información de la conexión a la base de datos.
    """
    return {
        "host": settings.POSTGRES_HOST,
        "port": settings.POSTGRES_PORT,
        "database": settings.POSTGRES_DB,
        "user": settings.POSTGRES_USER,
        "pool_size": settings.POSTGRES_POOL_SIZE,
        "max_overflow": settings.POSTGRES_MAX_OVERFLOW
    }
