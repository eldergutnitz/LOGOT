import os
from datetime import date, time
from typing import Optional

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


def load_dotenv(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080").split(",")
    if origin.strip()
]

app = FastAPI(title="LOGOT Syslog API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)


def db_connection():
    password = os.getenv("PGPASSWORD")
    kwargs = {
        "host": os.getenv("PGHOST", "127.0.0.1"),
        "port": int(os.getenv("PGPORT", "5432")),
        "dbname": os.getenv("PGDATABASE", "syslogdb"),
        "user": os.getenv("PGUSER"),
    }
    if password:
        kwargs["password"] = password
    return psycopg.connect(**kwargs, connect_timeout=5)


def iso_value(value):
    if isinstance(value, (date, time)):
        return value.isoformat()
    return value


@app.get("/healthz")
def healthz():
    try:
        with db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        return {"status": "ok", "database": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc


@app.get("/api/syslog/logs")
def get_syslog_logs(
    limit: int = Query(default=2000, ge=1, le=10000),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    event_type: Optional[str] = Query(default=None, max_length=100),
    q: Optional[str] = Query(default=None, max_length=200),
):
    conditions = []
    parameters = []

    if from_date:
        conditions.append("log_date >= %s")
        parameters.append(from_date)
    if to_date:
        conditions.append("log_date <= %s")
        parameters.append(to_date)
    if event_type:
        conditions.append("event_type = %s")
        parameters.append(event_type)
    if q:
        conditions.append("(hostname ILIKE %s OR device ILIKE %s OR message ILIKE %s OR event_type ILIKE %s)")
        pattern = f"%{q}%"
        parameters.extend([pattern, pattern, pattern, pattern])

    sql = """
        SELECT id, log_date, log_time, hostname, device, process_id,
               event_type, message
        FROM syslog_device_logs
    """
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY log_date DESC NULLS LAST, log_time DESC NULLS LAST, id DESC LIMIT %s"
    parameters.append(limit)

    try:
        with db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, parameters)
                columns = [description.name for description in cursor.description]
                rows = cursor.fetchall()
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    items = [
        {column: iso_value(value) for column, value in zip(columns, row)}
        for row in rows
    ]
    return {"items": items, "count": len(items)}
