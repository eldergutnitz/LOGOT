# Despliegue minimo en un solo servidor RHEL

Esta carpeta contiene una plantilla base para desplegar frontend, backend, PostgreSQL e importador de logs en un unico servidor.

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
