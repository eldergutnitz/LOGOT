# Manual de instalación y despliegue de LOGOT

Versión: 1.0
Sistema operativo objetivo: RHEL 8 x86_64
Arquitectura: PostgreSQL + importador Python + backend FastAPI + Nginx + frontend estático

## 1. Arquitectura y ubicaciones

```text
/opt/logot/frontend/dist       Frontend compilado o desplegado
/opt/logot/backend             Código y entorno virtual del backend
/opt/logot/backend/.env        Configuración PostgreSQL y CORS del backend
/opt/logot/backend/.venv      Entorno virtual Python
/opt/logot/importer            Importador de archivos SYSLOG
/opt/logot/importer/.env       Credenciales del importador
/opt/logot/importer/import_logs.py
/opt/logot/importer/run_import_logs.sh
/var/log/logot                 Logs del backend e importador
/srv/logs_ot                   Directorio base de archivos SYSLOG
/etc/nginx/nginx.conf          Configuración principal o bloques incluidos por Nginx
/etc/systemd/system/logot-backend.service
/etc/cron.d/import_logs        Entrada cron del importador
```

Los directorios `/opt/logot`, `/var/log/logot` y `/srv/logs_ot` deben pertenecer al usuario de operación adecuado. En la instalación realizada se utiliza el usuario `sjim216` y el grupo `mytra`; si el servidor usa otros usuarios, sustitúyalos en todos los pasos y en `logot-backend.service`.

## 2. Requisitos previos

Instale los paquetes base:

```bash
sudo dnf install -y nginx python39 python39-pip postgresql postgresql-server
```

Habilite PostgreSQL si todavía no está instalado y inicializado:

```bash
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
sudo systemctl enable --now nginx
```

Si PostgreSQL ya está operativo, no vuelva a inicializar el clúster.

## 3. Preparación de directorios y usuario

```bash
sudo mkdir -p /opt/logot/{frontend/dist,backend,importer} /var/log/logot /srv/logs_ot
sudo chown -R sjim216:mytra /opt/logot /var/log/logot /srv/logs_ot
sudo chmod 750 /opt/logot /opt/logot/backend /opt/logot/importer
sudo chmod 750 /var/log/logot
```

No entregue permisos de escritura a todo el servidor. El usuario `sjim216` debe poder leer los archivos SYSLOG de `/srv/logs_ot`.

## 4. Instalación de PostgreSQL y base de datos

Compruebe que PostgreSQL está activo:

```bash
sudo systemctl status postgresql --no-pager
sudo -u postgres psql -c 'SELECT version();'
```

Cree la base de datos y el usuario si todavía no existen:

```bash
sudo -u postgres psql
```

Dentro de `psql`:

```sql
CREATE DATABASE syslogdb;
CREATE USER sysloguser WITH PASSWORD 'CAMBIAR_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE syslogdb TO sysloguser;
\q
```

Configure en `pg_hba.conf` una autenticación segura desde `127.0.0.1`, por ejemplo con `scram-sha-256`, si PostgreSQL está en el mismo servidor. No configure `trust` ni permita conexiones públicas al puerto 5432.

### 4.1 Crear las tablas

Desde el directorio del repositorio:

```bash
sudo -u postgres psql -d syslogdb -f /ruta/repositorio/database/syslog_ingestion.sql
```

También puede usar:

```bash
psql -h 127.0.0.1 -U sysloguser -d syslogdb \
  -f /opt/logot/database/syslog_ingestion.sql
```

Objetos creados:

- `syslog_device_logs`: registros válidos e importados.
- `ux_syslog_rawline`: evita duplicados por contenido MD5 de `raw_line`.
- `syslog_rejected_logs`: líneas rechazadas.
- `ux_syslog_rejected_unique`: evita duplicados por archivo, número de línea y contenido.

Compruebe los objetos:

```bash
psql -h 127.0.0.1 -U sysloguser -d syslogdb \
  -c '\dt'
psql -h 127.0.0.1 -U sysloguser -d syslogdb \
  -c 'SELECT COUNT(*) FROM syslog_device_logs;'
```

## 5. Configuración para importar SYSLOG

El importador actual lee archivos `.log` ubicados dentro de estas carpetas de `/srv/logs_ot`:

- `logs_barcelona`
- `logs centrales`
- `logs_chapisteria`
- `logs_centrales`
- `logs_CROS`
- `logs.montaje`
- `logs_pinturas`
- `logs_prensas`
- `remote`

Los nombres se comparan sin distinguir mayúsculas/minúsculas.

Ejemplo de árbol:

```text
/srv/logs_ot/
├── logs_barcelona/
├── logs centrales/
├── logs_centrales/
├── logs_prensas/
└── remote/
```

Los permisos mínimos consisten en permitir lectura para `sjim216:mytra`:

```bash
sudo find /srv/logs_ot -type d -exec chmod 750 {} \;
sudo find /srv/logs_ot -type f -name '*.log' -exec chmod 640 {} \;
sudo chown -R sjim216:mytra /srv/logs_ot
```

### 5.1 Recepción de mensajes SYSLOG

Si el servidor debe recibir SYSLOG directamente por red, active el servicio Rsyslog correspondiente y configure su transporte apropiado. Ejemplo base para recibir archivos por TCP o UDP:

```text
module(load="imudp")
input(type="imudp" port="514")

module(load="imtcp")
input(type="imtcp" port="514")

$template LogotRemote,"/srv/logs_ot/remote/%fromhost-ip%.log"
if ($fromhost-ip != "127.0.0.1") then -?LogotRemote
& stop
```

Compruebe el servicio después de validar la configuración:

```bash
sudo rsyslogd -N1
sudo systemctl enable --now rsyslog
sudo systemctl status rsyslog --no-pager
sudo ss -lunpt | grep 514
```

Si TCP o UDP 514 no están habilitados por el cortafuegos, habilite solo el transporte autorizado por política de seguridad. Preferentemente debe utilizarse TCP con TLS si los equipos lo permiten.

Este manual no habilita TLS automáticamente. La selección de TCP/UDP, cifrado y origen autorizado debe confirmarles la administración de red y seguridad.

## 6. Instalación del importador

Copie el script y el wrapper:

```bash
sudo cp import_logs.py /opt/logot/importer/import_logs.py
sudo cp deploy/scripts/run_import_logs.sh /opt/logot/importer/run_import_logs.sh
sudo cp deploy/importer.env.example /opt/logot/importer/.env
sudo chmod 755 /opt/logot/importer/run_import_logs.sh
sudo chmod 600 /opt/logot/importer/.env
sudo chown -R sjim216:mytra /opt/logot/importer
```

Edite `/opt/logot/importer/.env`:

```bash
sudo vi /opt/logot/importer/.env
```

Contenido:

```env
PGHOST=127.0.0.1
PGPORT=5432
PGDATABASE=syslogdb
PGUSER=sysloguser
PGPASSWORD=CAMBIAR_PASSWORD
```

Instale la dependencia Python del importador:

```bash
python3.9 -m venv /opt/logot/importer/.venv
/opt/logot/importer/.venv/bin/pip install psycopg2-binary
sudo chown -R sjim216:mytra /opt/logot/importer
```

Si el servidor no tiene acceso a PyPI, instale mediante el wheelhouse del proyecto:

```bash
sudo cp -a backend/wheelhouse/. /opt/logot/backend/wheelhouse/
/opt/logot/importer/.venv/bin/pip install \
  --no-index \
  --find-links=/opt/logot/backend/wheelhouse \
  psycopg2-binary
```

El wrapper actual usa `/usr/bin/python3`, que puede ser Python 3.6 en RHEL 8. Para el entorno Python 3.9, ajuste `run_import_logs.sh` si es necesario:

```text
PYTHON=/opt/logot/importer/.venv/bin/python
```

Después:

```bash
sudo -u sjim216 /opt/logot/importer/run_import_logs.sh /srv/logs_ot
sudo tail -n 100 /var/log/logot/import_logs.log
```

## 7. Ejecución diaria del importador

Instale el cron para el usuario operativo:

```bash
sudo cp deploy/cron/import_logs.cron /etc/cron.d/import_logs
sudo chmod 644 /etc/cron.d/import_logs
sudo crontab -u sjim216 -l
```

La entrada incluida ejecuta una vez al día:

```cron
0 2 * * * /opt/logot/importer/run_import_logs.sh /srv/logs_ot
```

El wrapper utiliza `flock`, por lo que impide ejecuciones simultáneas.

Verifique el resultado:

```bash
sudo systemctl status crond --no-pager
sudo crontab -u sjim216 -l
sudo tail -n 100 /var/log/logot/import_logs.log
```

## 8. Instalación de Python y dependencias del backend

Instale Python 3.9:

```bash
sudo dnf install -y python39 python39-pip python39-devel
python3.9 --version
```

Copie el código:

```bash
sudo mkdir -p /opt/logot/backend
sudo cp -a backend/. /opt/logot/backend/
sudo chown -R sjim216:mytra /opt/logot/backend
```

Cree el entorno virtual:

```bash
sudo rm -rf /opt/logot/backend/.venv
sudo python3.9 -m venv /opt/logot/backend/.venv
sudo chown -R sjim216:mytra /opt/logot/backend/.venv
```

Si el servidor tiene acceso interno a las dependencias, instale directamente:

```bash
sudo -u sjim216 /opt/logot/backend/.venv/bin/pip install -r \
  /opt/logot/backend/requirements.txt
```

Si no tiene acceso a Internet, use el directorio `wheelhouse` incluido en el repositorio:

```bash
sudo cp -a backend/wheelhouse/. /opt/logot/backend/wheelhouse/
sudo chown -R sjim216:mytra /opt/logot/backend/wheelhouse

sudo -u sjim216 /opt/logot/backend/.venv/bin/pip install \
  --no-index \
  --find-links=/opt/logot/backend/wheelhouse \
  fastapi gunicorn uvicorn 'psycopg[binary]'
```

El wheelhouse debe contener ruedas compatibles con Linux x86_64 y Python 3.9.

Compruebe permisos e importaciones:

```bash
sudo chown -R sjim216:myta /opt/logot/backend/.venv
sudo -u sjim216 /opt/logot/backend/.venv/bin/python -c \
  "import fastapi, psycopg, gunicorn, uvicorn; print('Dependencias OK')"
```

Nota: el grupo de ejemplo es `mytra`. Corrija el comando si el grupo real es distinto.

## 9. Configuración del backend

Cree el archivo `/opt/logot/backend/.env`:

```bash
sudo cp /opt/logot/backend/env.example /opt/logot/backend/.env
sudo vi /opt/logot/backend/.env
sudo chmod 600 /opt/logot/backend/.env
sudo chown sjim216:mytra /opt/logot/backend/.env
```

Contenido recomendado:

```env
APP_ENV=production
PORT=8000
CORS_ORIGINS=https://dominio-interno-o-real

PGHOST=127.0.0.1
PGPORT=5432
PGDATABASE=syslogdb
PGUSER=sysloguser
PGPASSWORD=CAMBIAR_PASSWORD
```

En instalaciones con frontend y backend bajo el mismo origen HTTPS, la lista CORS puede contener ese dominio exacto. No coloque el password real en Git ni en el ejemplo público.

Compruebe que el backend carga los archivos:

```bash
sudo -u sjim216 /opt/logot/backend/.venv/bin/python -c \
  "from app.main import app; print(app.title)"
```

## 10. Servicio systemd del backend

Copie la unidad:

```bash
sudo cp deploy/systemd/logot-backend.service /etc/systemd/system/logot-backend.service
sudo vi /etc/systemd/system/logot-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now logot-backend
```

Contenido esperado:

```ini
[Unit]
Description=LOGOT Backend API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=sjim216
Group=mytra
WorkingDirectory=/opt/logot/backend
EnvironmentFile=/opt/logot/backend/.env
ExecStart=/opt/logot/backend/.venv/bin/gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 127.0.0.1:8000
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

Si el usuario o grupo real cambia, actualice `User` y `Group` antes de iniciar el servicio.

Compruebe:

```bash
sudo systemctl status logot-backend --no-pager
sudo journalctl -u logot-backend -n 100 --no-pager
curl http://127.0.0.1:8000/healthz
curl 'http://127.0.0.1:8000/api/syslog/logs?limit=10'
```

La primera respuesta debe indicar `database: ok`. La segunda debe devolver JSON con `items` y `count`.

## 11. Despliegue del frontend

Copie los archivos estáticos:

```bash
sudo rm -rf /opt/logot/frontend/dist
sudo mkdir -p /opt/logot/frontend/dist
sudo cp -a frontend/. /opt/logot/frontend/dist/
sudo chown -R root:root /opt/logot/frontend/dist
sudo find /opt/logot/frontend/dist -type d -exec chmod 755 {} \;
sudo find /opt/logot/frontend/dist -type f -exec chmod 644 {} \;
```

El frontend usa la URL relativa `/api` por defecto y debe mantener ese valor en su interfaz.

## 12. Configuración de Nginx

Antes de modificar la configuración activa, conserve una copia:

```bash
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup
```

Compruebe dónde está el bloque activo:

```bash
sudo nginx -T 2>&1 | grep -n -A15 -B5 'server_name'
sudo grep -Rni 'location /api' /etc/nginx
```

Dentro del mismo bloque `server` que publica el frontend, configure:

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_read_timeout 60s;
}

location / {
    root /opt/logot/frontend/dist;
    try_files $uri $uri/ /index.html;
}

location = /healthz {
    add_header Content-Type text/plain;
    return 200 "ok\n";
}
```

`proxy_pass` no debe terminar en `/` si se desea conservar el prefijo `/api`.

Para instalaciones que usan un archivo separado:

```bash
sudo cp deploy/nginx/logot.conf /etc/nginx/conf.d/logot.conf
```

Nginx no admite dos bloques `location /` equivalentes dentro del mismo servidor. Retire el duplicado antes de recargar.

Valide y active:

```bash
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl restart nginx
```

Pruebe:

```bash
curl -i 'http://127.0.0.1/api/syslog/logs?limit=10'
curl -i 'http://127.0.0.1/healthz'
```

El primer resultado debe ser JSON y el segundo debe indicar estado correcto.

## 13. Servicios que deben estar activos

Compruebe:

```bash
sudo systemctl enable --now postgresql
sudo systemctl enable --now nginx
sudo systemctl enable --now logot-backend
sudo systemctl enable --now crond

sudo systemctl status postgresql nginx logot-backend crond --no-pager
```

Si Rsyslog recibe datos directamente:

```bash
sudo systemctl enable --now rsyslog
sudo systemctl status rsyslog --no-pager
```

## 14. Desplegar por primera vez

Secuencia mínima:

1. Instalar PostgreSQL, Python 3.9 y Nginx.
2. Crear base de datos, usuario y tablas.
3. Crear `/srv/logs_ot` y recopilar archivos SYSLOG.
4. Instalar el importador y ejecutar una importación manual.
5. Instalar dependencias offline o desde el repositorio interno.
6. Crear `/opt/logot/backend/.env`.
7. Iniciar y validar el backend.
8. Crear el servicio systemd.
9. Copiar el frontend.
10. Configurar y validar Nginx.
11. Configurar cron.
12. Validar desde el navegador y los equipos SYSLOG.

## 15. Comprobaciones finalizadas

### 15.1 Base de datos

```bash
psql -h 127.0.0.1 -U sysloguser -d syslogdb \
  -c 'SELECT COUNT(*) FROM syslog_device_logs;'
psql -h 127.0.0.1 -U sysloguser -d syslogdb \
  -c 'SELECT COUNT(*) FROM syslog_rejected_logs;'
psql -h 127.0.0.1 -U sysloguser -d syslogdb \
  -c 'SELECT event_type, COUNT(*) FROM syslog_device_logs GROUP BY event_type;'
```

### 15.2 Backend

```bash
curl -i http://127.0.0.1:8000/healthz
curl -i 'http://127.0.0.1:8000/api/syslog/logs?limit=10'
sudo journalctl -u logot-backend -n 100 --no-pager
```

### 15.3 Nginx y frontend

```bash
curl -i 'http://127.0.0.1/api/syslog/logs?limit=10'
curl -I http://127.0.0.1/
sudo nginx -t
```

## 16. Copias de seguridad

Se recomienda realizar una copia diaria de PostgreSQL:

```bash
sudo -u postgres pg_dump -Fc syslogdb \
  -f /var/backups/logot/syslogdb-$(date +%F).dump
```

Respalde además:

- `/opt/logot/backend/.env`
- `/opt/logot/importer/.env`
- `/srv/logs_ot`
- `/etc/nginx/nginx.conf` o el archivo incluido correspondiente
- `/etc/systemd/system/logot-backend.service`
- `/etc/cron.d/import_logs`

Los archivos `.env` deben cifrarse o almacenarse en un gestor de secretos. Nunca deben incluirse en Git.

## 17. Solución de problemas

### La API devuelve 503

- Compruebe PostgreSQL.
- Compruebe usuario, contraseña y nombre de base en `/opt/logot/backend/.env`.
- Compruebe `pg_hba.conf` y permisos del usuario.
- Revise `journalctl -u logot-backend`.

### Nginx devuelve el HTML del frontend en `/api`

- Compruebe que `/api/` existe antes de `location /`.
- Compruebe que no hay otro bloque duplicado para `/api/`.
- Compruebe `proxy_pass` sin barra final.
- Ejecuta `sudo nginx -t` y reinicie Nginx.

### El importador no encuentra archivos

- Compruebe `/srv/logs_ot`.
- Compruebe nombres y carpetas permitidas.
- Compruebe permisos de lectura.
- Revise `/var/log/logot/import_logs.log`.

### El backend no arranca

- Compruebe las dependencias Python.
- Compruebe `WorkingDirectory` y `app.main:app`.
- Compruebe propiedad y permisos de `/opt/logot/backend/.venv`.
- Revise `journalctl -u logot-backend`.

### No se reciben mensajes SYSLOG

- Compruebe puerto 514 UDP/TCP.
- Compruebe Rsyslog.
- Compruebe firewall y rutas.
- Confirme permisos de escritura en `/srv/logs_ot`.
- Revise archivos nuevos y el cron del importador.
