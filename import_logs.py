import os
import re
import sys
import argparse
import getpass
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values

PATTERN = re.compile(
    r"^(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+"
    r"(?P<device>[^\[]+)\[(?P<pid>\d+)\]\s+"
    r"(?P<msg>.*)$"
)

PATTERN_WITHOUT_PID = re.compile(
    r"^(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+"
    r"(?P<device>\S+)\s+"
    r"(?P<msg>.*)$"
)

ISO_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+"
    r"(?:(?P<host>[^\s]+)\s+)?"
    r"(?:(?P<device>[^\s:\[]+)(?:\[(?P<pid>\d+)\])?[\s:]+)?"
    r"(?P<msg>.*)$"
)

TARGET_FOLDERS = {
    "logs_barcelona",
    "logs centrales",
    "logs_chapisteria",
    "logs_centrales",
    "logs_CROS",
    "logs.montaje",
    "logs_pinturas",
    "logs_prensas",
    "remote",
}

DEFAULT_BASE_DIR = "/srv/logs_ot"
BATCH_SIZE = 500


def detect_event_type(message):
    msg = message.strip()
    if "Link down" in msg:
        return "Link down"
    if "Link up" in msg:
        return "Link up"
    if "Device configuration changed" in msg:
        return "Device configuration changed"
    if "WBM" in msg:
        return "WBM"
    return "OTHER"


def parse_line(line, fallback_hostname=None):
    line = line.strip()
    if not line:
        return None

    m = PATTERN.match(line)
    if m:
        mon = m.group("mon")
        day = int(m.group("day"))
        time_str = m.group("time")
        year = datetime.now().year

        try:
            dt = datetime.strptime(f"{year} {mon} {day} {time_str}", "%Y %b %d %H:%M:%S")
        except ValueError:
            dt = None

        message = m.group("msg").strip()
        return {
            "log_date": dt.date() if dt else None,
            "log_time": dt.time() if dt else None,
            "hostname": m.group("host"),
            "device": m.group("device").strip(),
            "process_id": int(m.group("pid")),
            "event_type": detect_event_type(message),
            "message": message,
            "raw_line": line,
        }

    m = PATTERN_WITHOUT_PID.match(line)
    if m:
        mon = m.group("mon")
        day = int(m.group("day"))
        time_str = m.group("time")
        year = datetime.now().year

        try:
            dt = datetime.strptime(f"{year} {mon} {day} {time_str}", "%Y %b %d %H:%M:%S")
        except ValueError:
            dt = None

        message = m.group("msg").strip()
        return {
            "log_date": dt.date() if dt else None,
            "log_time": dt.time() if dt else None,
            "hostname": m.group("host"),
            "device": m.group("device").strip(),
            "process_id": None,
            "event_type": detect_event_type(message),
            "message": message,
            "raw_line": line,
        }

    m = ISO_PATTERN.match(line)
    if m:
        timestamp = m.group("timestamp")
        try:
            normalized = timestamp.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            dt = None

        message = m.group("msg").strip()
        hostname = m.group("host") or fallback_hostname
        device = (m.group("device") or "").strip() or None
        pid_text = m.group("pid")
        return {
            "log_date": dt.date() if dt else None,
            "log_time": dt.time() if dt else None,
            "hostname": hostname,
            "device": device,
            "process_id": int(pid_text) if pid_text else None,
            "event_type": detect_event_type(message),
            "message": message,
            "raw_line": line,
        }

    return {
        "log_date": None,
        "log_time": None,
        "hostname": fallback_hostname,
        "device": None,
        "process_id": None,
        "event_type": "UNPARSED",
        "message": line,
        "raw_line": line,
    }


def get_connection(db_host, db_name, db_user, db_password, db_port):
    connect_args = {
        "host": db_host,
        "dbname": db_name,
        "user": db_user,
        "port": db_port,
    }

    if db_password:
        connect_args["password"] = db_password

    return psycopg2.connect(
        **connect_args,
    )


def ensure_schema(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS syslog_device_logs (
            id SERIAL PRIMARY KEY,
            log_date DATE,
            log_time TIME,
            hostname TEXT,
            device TEXT,
            process_id INT,
            event_type TEXT,
            message TEXT,
            raw_line TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_syslog_rawline
            ON syslog_device_logs ((md5(raw_line)))
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS syslog_rejected_logs (
            id BIGSERIAL PRIMARY KEY,
            source_file TEXT NOT NULL,
            line_number INT NOT NULL,
            raw_line TEXT NOT NULL,
            reject_reason TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            raw_line_md5 TEXT GENERATED ALWAYS AS (md5(raw_line)) STORED
        )
        """
    )

    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_syslog_rejected_unique
            ON syslog_rejected_logs (source_file, line_number, raw_line_md5)
        """
    )


def iter_target_log_files(base_dir):
    if not os.path.isdir(base_dir):
        raise FileNotFoundError(f"No existe el directorio base: {base_dir}")

    for root, dirs, files in os.walk(base_dir):
        dirs.sort()
        for filename in sorted(files):
            if filename.lower().endswith(".log"):
                yield os.path.join(root, filename)


def flush_valid_rows(cur, rows):
    if not rows:
        return 0

    execute_values(
        cur,
        """
        INSERT INTO syslog_device_logs
        (log_date, log_time, hostname, device, process_id, event_type, message, raw_line)
        VALUES %s
        ON CONFLICT ((md5(raw_line))) DO NOTHING
        """,
        rows,
    )

    inserted_now = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
    rows.clear()
    return inserted_now


def flush_rejected_rows(cur, rows):
    if not rows:
        return 0

    execute_values(
        cur,
        """
        INSERT INTO syslog_rejected_logs
        (source_file, line_number, raw_line, reject_reason)
        VALUES %s
        ON CONFLICT (source_file, line_number, raw_line_md5) DO NOTHING
        """,
        rows,
    )

    inserted_now = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
    rows.clear()
    return inserted_now


def import_logs(base_dir, db_host, db_name, db_user, db_password, db_port):
    conn = get_connection(db_host, db_name, db_user, db_password, db_port)
    conn.autocommit = False
    cur = conn.cursor()

    valid_rows = []
    rejected_rows = []

    files_processed = 0
    total_lines = 0
    parsed_ok = 0
    parsed_bad = 0
    inserted_valid = 0
    inserted_rejected = 0
    skipped_unreadable_files = 0

    try:
        try:
            ensure_schema(cur)
            conn.commit()
        except psycopg2.Error as err:
            # If schema objects already exist but belong to another owner,
            # continue importing using the current structure.
            conn.rollback()
            if err.pgcode == "42501":
                print(
                    "WARNING: permisos insuficientes para crear/alterar esquema. "
                    "Se continua con el esquema existente.",
                    file=sys.stderr,
                )
            else:
                raise

        for file_path in iter_target_log_files(base_dir):
            files_processed += 1
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    for line_number, line in enumerate(f, start=1):
                        parsed = parse_line(
                            line,
                            fallback_hostname=extract_ip_from_source(file_path)
                            or os.path.basename(file_path),
                        )
                        if parsed is None:
                            continue

                        total_lines += 1

                        if parsed["hostname"] is None and parsed["device"] is None:
                            parsed_bad += 1
                            rejected_rows.append(
                                (
                                    file_path,
                                    line_number,
                                    parsed["raw_line"],
                                    "regex_no_match",
                                )
                            )
                        elif parsed["event_type"] == "UNPARSED":
                            parsed_bad += 1
                            rejected_rows.append(
                                (
                                    file_path,
                                    line_number,
                                    parsed["raw_line"],
                                    "regex_no_match",
                                )
                            )
                        else:
                            parsed_ok += 1
                            valid_rows.append(
                                (
                                    parsed["log_date"],
                                    parsed["log_time"],
                                    parsed["hostname"],
                                    parsed["device"],
                                    parsed["process_id"],
                                    parsed["event_type"],
                                    parsed["message"],
                                    parsed["raw_line"],
                                )
                            )

                        if len(valid_rows) >= BATCH_SIZE:
                            inserted_valid += flush_valid_rows(cur, valid_rows)
                            conn.commit()

                        if len(rejected_rows) >= BATCH_SIZE:
                            inserted_rejected += flush_rejected_rows(cur, rejected_rows)
                            conn.commit()
            except PermissionError:
                skipped_unreadable_files += 1
                print(
                    f"WARNING: sin permisos de lectura para {file_path}. Se omite.",
                    file=sys.stderr,
                )
                continue

        inserted_valid += flush_valid_rows(cur, valid_rows)
        inserted_rejected += flush_rejected_rows(cur, rejected_rows)
        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    duplicates_valid = parsed_ok - inserted_valid
    duplicates_rejected = parsed_bad - inserted_rejected

    print(f"Base dir: {base_dir}")
    print(f"Files processed: {files_processed}")
    print(f"Processed lines: {total_lines}")
    print(f"Parsed OK: {parsed_ok}")
    print(f"Parsed bad: {parsed_bad}")
    print(f"Inserted new rows: {inserted_valid}")
    print(f"Ignored valid duplicates: {duplicates_valid}")
    print(f"Inserted rejected rows: {inserted_rejected}")
    print(f"Ignored rejected duplicates: {duplicates_rejected}")
    print(f"Unreadable files skipped: {skipped_unreadable_files}")


IP_PATTERN = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")


def extract_ip_from_source(source_path):
    basename = os.path.basename(source_path)
    match = IP_PATTERN.search(basename)
    if not match:
        return None

    ip = match.group(0)
    if all(int(part) <= 255 for part in ip.split(".")):
        return ip
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Importa logs syslog a PostgreSQL."
    )
    parser.add_argument(
        "base_dir",
        nargs="?",
        default=os.getenv("SYSLOG_BASE_DIR", DEFAULT_BASE_DIR),
        help="Directorio base de logs. Default: /srv/logs_ot o SYSLOG_BASE_DIR",
    )
    parser.add_argument(
        "--db-host",
        default=os.getenv("PGHOST", "127.0.0.1"),
        help="Host PostgreSQL (o PGHOST)",
    )
    parser.add_argument(
        "--db-port",
        default=os.getenv("PGPORT", "5432"),
        help="Puerto PostgreSQL (o PGPORT)",
    )
    parser.add_argument(
        "--db-name",
        default=os.getenv("PGDATABASE", "syslogdb"),
        help="Base de datos (o PGDATABASE)",
    )
    parser.add_argument(
        "--db-user",
        default=os.getenv("PGUSER"),
        help="Usuario PostgreSQL (o PGUSER)",
    )
    parser.add_argument(
        "--db-password",
        default=os.getenv("PGPASSWORD"),
        help="Password PostgreSQL (o PGPASSWORD)",
    )
    parser.add_argument(
        "--db-password-prompt",
        action="store_true",
        help="Pide el password por consola sin mostrarlo",
    )

    args = parser.parse_args()

    if not args.db_user:
        print("ERROR: falta usuario de base de datos. Usa --db-user o PGUSER.")
        sys.exit(1)

    db_password = args.db_password
    if args.db_password_prompt and not db_password:
        db_password = getpass.getpass("Password PostgreSQL: ")

    import_logs(
        args.base_dir,
        args.db_host,
        args.db_name,
        args.db_user,
        db_password,
        args.db_port,
    )
