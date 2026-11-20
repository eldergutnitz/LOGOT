# Guías de desarrollo asistido por IA

Documentación y plantillas de apoyo para el desarrollo asistido por IA.

- `Style`: guías Markdown de estilo para las tres marcas.
- `yellow`: plantilla de repositorio de Nivel 2 (Python y JavaScript/npm).
- `VIBE_CODING`: documentación original de FS-X.
- `deploy`: plantilla mínima de despliegue en RHEL para frontend, backend, PostgreSQL e importador de logs.

## Frontend para visualizar datos de BDD (syslog)

Se incluye un frontend estático en `frontend/` para explorar los datos de `syslog_device_logs`.
La imagen de cabecera de SEAT y CUPRA se sirve desde `frontend/` junto a las páginas del explorador y el dashboard. Al sustituirla, actualiza sus dimensiones si cambian y la versión `v` en ambas páginas para evitar que el navegador muestre la imagen anterior.

### Qué permite

- Cambiar entre vistas: `Detalle`, `Eventos`, `Dispositivos` y `Timeline`.
- Filtrar por texto, tipo de evento y rango de fechas.
- Configurar la URL base de API (por defecto `/api`).
- Mostrar datos de ejemplo cuando la API no está disponible.

### Ejecutar en local

Con cualquier servidor estático:

```powershell
cd frontend
python -m http.server 8080
```

Luego abre `http://localhost:8080`.

### Contrato API esperado

El frontend consulta:

- `GET /api/syslog/logs?limit=2000`

Respuesta aceptada:

- Un array directo de registros, o
- Un objeto con `items` o `data` como array.

Campos usados por registro:

- `id`, `log_date`, `log_time`, `hostname`, `device`, `process_id`, `event_type`, `message`.
