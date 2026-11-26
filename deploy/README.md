# Despliegue minimo en un solo servidor RHEL

Esta carpeta contiene una plantilla base para desplegar frontend, backend, PostgreSQL e importador de logs en un unico servidor.

## Cambios de la version 1.2

- El importador admite líneas syslog con y sin PID y deriva el hostname desde una IP presente en el nombre del archivo.
- El importador puede usar el socket Unix `/var/run/postgresql`.
- El wrapper y los archivos de configuración deben usar finales de línea LF.
- La importación programada puede realizarse con `logot-import.timer` además de cron.
- El frontend muestra como máximo 200 mensajes en Vista Detalle.
- Las estadísticas de la vista y del dashboard se calculan globalmente desde `/api/syslog/stats`.
- El frontend muestra la versión `v1.2`.

## Estructura propuesta

- `/opt/logot/frontend/dist`: build estatico del frontend
- `/opt/logot/backend`: codigo del backend
- `/opt/logot/backend/.venv`: entorno virtual Python del backend
- `/opt/logot/backend/.env`: variables del backend
- `/opt/logot/importer/import_logs.py`: script de importacion de logs
- `/opt/logot/importer/.env`: variables del importador
- `/var/log/logot`: logs de aplicacion

## Archivos incluidos en esta carpeta

- `nginx/logot.conf`: virtual host Nginx con frontend y proxy a `/api`
- `systemd/logot-backend.service`: servicio systemd del backend
- `systemd/logot-backend.env.example`: ejemplo de variables de entorno del backend
- `scripts/run_import_logs.sh`: wrapper robusto para el importador
- `cron/import_logs.cron`: entrada cron diaria con lock y log
- `checklists/go-live-checklist.md`: checklist de salida a produccion
- `systemd/logot-import.service`: ejecución manual o activada por timer del importador.
- `systemd/logot-import.timer`: programación diaria a las 02:00.

## Pasos rapidos

1. Copiar frontend compilado a `/opt/logot/frontend/dist`.
2. Desplegar backend en `/opt/logot/backend` y ajustar `ExecStart` del servicio si aplica.
3. Copiar `import_logs.py` a `/opt/logot/importer/import_logs.py`.
4. Crear `/opt/logot/importer/.env` desde el ejemplo y protegerlo con `chmod 600`.
5. Instalar y habilitar servicio backend de systemd.
6. Instalar configuracion Nginx y recargar.
7. Registrar cron diario del importador.
8. Ejecutar checklist de produccion.

## Nota de seguridad

No guardar passwords reales en Git. Usa archivos `.env` fuera del repo o secretos del sistema.
