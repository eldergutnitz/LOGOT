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
    limit: int = Query(default=10000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
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
    sql += " ORDER BY log_date DESC NULLS LAST, log_time DESC NULLS LAST, id DESC LIMIT %s OFFSET %s"
    parameters.append(limit)
    parameters.append(offset)

    try:
        with db_connection() as connection:
            with connection.cursor() as cursor:
                count_sql = "SELECT COUNT(*) FROM syslog_device_logs"
                if conditions:
                    count_sql += " WHERE " + " AND ".join(conditions)
                cursor.execute(count_sql, parameters[:-2])
                total_count = cursor.fetchone()[0]

                cursor.execute(sql, parameters)
                columns = [description.name for description in cursor.description]
                rows = cursor.fetchall()
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    items = [
        {column: iso_value(value) for column, value in zip(columns, row)}
        for row in rows
    ]
    return {
        "items": items,
        "count": len(items),
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/syslog/stats")
def get_syslog_stats():
    try:
        with db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM syslog_device_logs")
                total = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(DISTINCT event_type) FROM syslog_device_logs")
                event_types = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(DISTINCT device) FROM syslog_device_logs WHERE device IS NOT NULL AND device <> ''")
                devices = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(DISTINCT hostname) FROM syslog_device_logs WHERE hostname IS NOT NULL AND hostname <> ''")
                hosts = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT event_type, COUNT(*)
                    FROM syslog_device_logs
                    GROUP BY event_type
                    ORDER BY COUNT(*) DESC
                    LIMIT 10
                """)
                event_distribution = [
                    {"name": row[0] or "OTHER", "count": row[1]}
                    for row in cursor.fetchall()
                ]

                cursor.execute("""
                    SELECT COALESCE(device, 'N/A'), COUNT(*)
                    FROM syslog_device_logs
                    GROUP BY COALESCE(device, 'N/A')
                    ORDER BY COUNT(*) DESC
                    LIMIT 10
                """)
                device_distribution = [
                    {"name": row[0], "count": row[1]}
                    for row in cursor.fetchall()
                ]

                cursor.execute("""
                    SELECT COALESCE(CAST(log_date AS TEXT), 'Sin fecha'), COUNT(*)
                    FROM syslog_device_logs
                    GROUP BY log_date
                    ORDER BY log_date ASC NULLS LAST
                """)
                timeline_distribution = [
                    {"name": row[0], "count": row[1]}
                    for row in cursor.fetchall()
                ]
    except psycopg.Error as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc

    return {
        "total": total,
        "event_types": event_types,
        "devices": devices,
        "hosts": hosts,
        "event_distribution": event_distribution,
        "device_distribution": device_distribution,
        "timeline_distribution": timeline_distribution,
    }
