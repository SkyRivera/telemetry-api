# Guía de Contribución

## Flujo de trabajo

1. Crear una rama desde `main`: `git checkout -b feature/nombre-descriptivo`
2. Realizar cambios siguiendo el estilo del proyecto.
3. Ejecutar pruebas locales: `docker compose up -d && curl http://localhost:8000/health`
4. Hacer commit usando [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: agregar endpoint de historial`
   - `fix: corregir validación de humedad`
5. Abrir un Pull Request describiendo el cambio.

## Estilo de código

- Python 3.11, tipado estricto con `typing`.
- Formateo con `ruff format`.
- Linting con `ruff check`.
- Docstrings en español.

## Pruebas

- Toda nueva funcionalidad debe incluir pruebas o ejemplos en cURL.
- Los cambios en esquemas de BD deben reflejarse en `db/init.sql`.

## Seguridad

- **Nunca** commitear el archivo `.env`.
- **Nunca** incluir API Keys en el código.
- Reportar vulnerabilidades a `iot-telemetry@example.org`.
