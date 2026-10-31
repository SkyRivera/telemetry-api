-- =====================================================================
-- telemetry-api — Esquema inicial
-- Ejecutar conectado a la base de datos telemetry_db
-- =====================================================================

-- Extensión para gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------
-- Tabla: stations
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stations (
    id               SERIAL PRIMARY KEY,
    device_id        VARCHAR(64) UNIQUE NOT NULL,
    name             VARCHAR(255),
    status           VARCHAR(32) NOT NULL DEFAULT 'active',
    firmware_version VARCHAR(32),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_stations_device_id ON stations(device_id);

-- ---------------------------------------------------------------------
-- Tabla: read_requests
-- Se crea antes que telemetry porque telemetry referencia request_id.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS read_requests (
    id            SERIAL PRIMARY KEY,
    request_id    UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    station_id    INTEGER NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    status        VARCHAR(32) NOT NULL DEFAULT 'pending',
    requested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    dispatched_at TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ,
    expires_at    TIMESTAMPTZ NOT NULL,
    requested_by  VARCHAR(128)
);

CREATE INDEX IF NOT EXISTS idx_read_requests_station_status
    ON read_requests(station_id, status);
CREATE INDEX IF NOT EXISTS idx_read_requests_request_id
    ON read_requests(request_id);
CREATE INDEX IF NOT EXISTS idx_read_requests_expires
    ON read_requests(expires_at);

-- ---------------------------------------------------------------------
-- Tabla: telemetry
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS telemetry (
    id              BIGSERIAL PRIMARY KEY,
    station_id      INTEGER NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
    temperature     NUMERIC(5,2),
    humidity        NUMERIC(5,2),
    wind_speed_kmh  NUMERIC(6,2),
    measured_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    received_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reading_type    VARCHAR(32) NOT NULL DEFAULT 'periodic',
    request_id      UUID REFERENCES read_requests(request_id) ON DELETE SET NULL,
    sensor_status   VARCHAR(32) NOT NULL DEFAULT 'OK'
);

CREATE INDEX IF NOT EXISTS idx_telemetry_station_received
    ON telemetry(station_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_station_measured
    ON telemetry(station_id, measured_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_request_id
    ON telemetry(request_id);

-- ---------------------------------------------------------------------
-- Tabla: telemetry_queries
-- Registra cada consulta hecha a la API.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS telemetry_queries (
    id                BIGSERIAL PRIMARY KEY,
    station_id        INTEGER REFERENCES stations(id) ON DELETE SET NULL,
    endpoint          VARCHAR(255) NOT NULL,
    query_type        VARCHAR(32) NOT NULL,
    requested_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    client_identifier VARCHAR(128),
    request_id        UUID,
    response_status   INTEGER,
    telemetry_id      BIGINT REFERENCES telemetry(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_queries_station_time
    ON telemetry_queries(station_id, requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_queries_type
    ON telemetry_queries(query_type);

-- ---------------------------------------------------------------------
-- Estación inicial para pruebas
-- ---------------------------------------------------------------------
INSERT INTO stations (device_id, name, status, firmware_version)
VALUES ('BOSQUE-001', 'Estación Bosque 1', 'active', '2.1.0')
ON CONFLICT (device_id) DO NOTHING;