# Backend LOGOT

API FastAPI para consultar `syslog_device_logs` en PostgreSQL.

## Instalación local

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edita .env con las credenciales PostgreSQL
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

El endpoint principal es:

- `GET http://127.0.0.1:8000/api/syslog/logs?limit=2000`
- `GET http://127.0.0.1:8000/healthz`

También acepta filtros opcionales: `from_date`, `to_date`, `event_type`, `q` y `limit`.
