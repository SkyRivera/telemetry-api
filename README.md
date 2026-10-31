# telemetry-api

API REST para la captura, almacenamiento y exposición de mediciones ambientales
(temperatura, humedad y velocidad del viento) provenientes de estaciones remotas ESP32.

## Características

- Ingesta de telemetría desde ESP32 vía HTTPS.
- Almacenamiento persistente en PostgreSQL.
- Consulta del último dato y del historial.
- Solicitud de lecturas físicas bajo demanda (polling desde el ESP32).
- Registro obligatorio de cada consulta realizada (`telemetry_queries`).
- Autenticación mediante API Keys.
- Rate limiting por IP.
- Contenerizado con Docker y Docker Compose.

## Arquitectura

```text
[ESP32] --HTTPS (saliente)--> [Nginx] --> [telemetry-api] --> [PostgreSQL]
                                   ^
                                   |
[API B / Postman] --HTTPS (saliente)
```
