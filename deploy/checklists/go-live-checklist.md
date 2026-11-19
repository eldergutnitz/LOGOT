# Checklist minimo de salida a produccion

## Seguridad

- [ ] Frontend servido por Nginx detras de HTTPS.
- [ ] Puerto 5432 no expuesto publicamente.
- [ ] Credenciales fuera del repositorio (`.env` con `chmod 600`).
- [ ] Usuario de app sin privilegios de superusuario en PostgreSQL.

## Backend

- [ ] Servicio `logot-backend.service` activo y habilitado.
- [ ] Endpoint de salud de API responde 200.
- [ ] Logs de backend visibles en `journalctl -u logot-backend`.

## Importador

- [ ] `import_logs.py` actualizado en `/opt/logot/importer/`.
- [ ] Wrapper `run_import_logs.sh` con permisos de ejecucion.
- [ ] Cron instalado y validado (`crontab -l`).
- [ ] Lock de `flock` evita ejecuciones simultaneas.

## Base de datos

- [ ] Tabla `syslog_device_logs` con indice `ux_syslog_rawline`.
- [ ] Tabla `syslog_rejected_logs` con indice `ux_syslog_rejected_unique`.
- [ ] Query de control de volumen y rechazos validada.

## Operacion

- [ ] Backup diario de PostgreSQL probado.
- [ ] Rotacion de logs configurada.
- [ ] Alerta simple si hay parse bad anomalo.
