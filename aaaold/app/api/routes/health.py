from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone

from app.database import get_db
from app.schemas import HealthResponse
from app.config import get_settings
from app.security import verify_api_key

router = APIRouter(prefix="/api/v1/health", tags=["health"])
settings = get_settings()


@router.get("", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db), _: str = Depends(verify_api_key)):
    """
    Health check endpoint para monitoreo.
    """
    # Verificar base de datos
    db_status = "ok"
    db_error = None
    try:
        db.execute(text("SELECT 1"))
        db.commit()
    except Exception as e:
        db_status = "error"
        db_error = str(e)

    status = "healthy" if db_status == "ok" else "degraded"

    return HealthResponse(
        status=status,
        timestamp=datetime.now(timezone.utc),
        database=db_status if db_status == "ok" else f"error: {db_error}",
        service=settings.APP_NAME,
        version=settings.APP_VERSION
    )


@router.get("/readiness", response_model=dict)
async def readiness_check():
    """
    Readiness probe para Kubernetes/Docker.
    """
    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/liveness", response_model=dict)
async def liveness_check():
    """
    Liveness probe para Kubernetes/Docker.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
