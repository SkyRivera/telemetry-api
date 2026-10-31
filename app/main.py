from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.db.database import engine, Base
from app.api.routes import telemetry, commands, stations

limiter = Limiter(key_func=get_remote_address, default_limits=[
                  settings.rate_limit_default])

app = FastAPI(
    title="telemetry-api",
    version="1.0.0",
    description="API de telemetría ambiental para estaciones remotas ESP32",
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


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "telemetry-api"}
