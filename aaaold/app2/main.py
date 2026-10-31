import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.api.routes import commands, stations, telemetry
from app.config import settings
from app.db.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telemetry-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verificación de conectividad con la base de datos
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("PostgreSQL connection OK")
    yield
    await engine.dispose()


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
)

app = FastAPI(
    title=settings.app_name,
    version="2.1.0",
    description=(
        "API de telemetría ambiental para estaciones ESP32. "
        "Variables: temperatura, humedad, velocidad del viento (km/h)."
    ),
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telemetry.router)
app.include_router(commands.router)
app.include_router(stations.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy", "service": settings.app_name}
