#!/usr/bin/env python3
"""Import local syslog archives into SQLite using only the Python standard library."""

import argparse
import bz2
from contextlib import closing
import gzip
import hashlib
import lzma
from pathlib import Path
import re
import sqlite3
import sys
import zlib


RFC5424 = re.compile(
    r"^<(?P<priority>\d{1,3})>[1-9]\d{0,2} "
    r"(?P<event_timestamp>\S+) (?P<hostname>\S+) (?P<app_name>\S+) "
    r"(?P<proc_id>\S+) (?P<msg_id>\S+) "
    r"(?P<structured_data>-|(?:\[(?:[^\]\\]|\\.)*\])+)"
    r"(?: (?P<message>.*))?$"
)
LEGACY = re.compile(
    r"^(?:<(?P<priority>\d{1,3})>)?"
    r"(?P<event_timestamp>[A-Z][a-z]{2} +\d{1,2} \d{2}:\d{2}:\d{2}"
    r"|\d{4}-\d{2}-\d{2}T\S+) "
    r"(?P<hostname>\S+) (?P<message>.*)$"
)
TAG = re.compile(
    r"^(?P<app_name>[^\s:\[]+)(?:\[(?P<proc_id>[^\]\s]+)\])?: ?(?P<message>.*)$"
)
FIELDS = (
    "event_timestamp", "hostname", "app_name", "proc_id", "msg_id",
    "structured_data", "facility", "severity", "message", "parsed",
)
SCHEMA = """
CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    sha256 TEXT UNIQUE,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY,
    import_id INTEGER NOT NULL REFERENCES imports(id),
    line_number INTEGER NOT NULL,
    raw_message TEXT NOT NULL,
    event_timestamp TEXT,
    hostname TEXT,
    app_name TEXT,
    proc_id TEXT,
    msg_id TEXT,
    structured_data TEXT,
    facility INTEGER,
    severity INTEGER,
    message TEXT NOT NULL,
    parsed INTEGER NOT NULL,
    UNIQUE(import_id, line_number)
);
CREATE INDEX IF NOT EXISTS logs_timestamp ON logs(event_timestamp);
CREATE INDEX IF NOT EXISTS logs_hostname ON logs(hostname);
"""
INSERT = (
    "INSERT INTO logs (import_id, line_number, raw_message, "
    + ", ".join(FIELDS)
    + ") VALUES ("
    + ", ".join("?" for _ in range(3 + len(FIELDS)))
    + ")"
)


def parse_line(raw):
    """Keep unknown lines, including multiline continuations, without guessing."""
    record = dict.fromkeys(FIELDS)
    record.update(message=raw, parsed=0)
    match = RFC5424.fullmatch(raw)
    modern = match is not None
    if match is None:
        match = LEGACY.fullmatch(raw)
    if match is None:
        return record
    values = match.groupdict()
    priority = values.pop("priority")
    if priority is not None:
        priority = int(priority)
        if priority > 191:
            return record
        record.update(facility=priority // 8, severity=priority % 8)
    if modern:
        for field in ("event_timestamp", "hostname", "app_name", "proc_id", "msg_id",
                      "structured_data"):
            if values[field] == "-":
                values[field] = None
        values["message"] = values["message"] or ""
    else:
        tag = TAG.fullmatch(values["message"])
        if tag:
            values.update(tag.groupdict())
    record.update(values, parsed=1)
    return record


def open_archive(path):
    opener = {
        ".gz": gzip.open,
        ".bz2": bz2.open,
        ".xz": lzma.open,
    }.get(path.suffix.lower(), open)
    return opener(path, "rb")


def import_archive(connection, path):
    """Commit a complete file, or roll it back on errors or duplicate content."""
    digest = hashlib.sha256()
    count = 0
    with connection:
        import_id = connection.execute(
            "INSERT INTO imports (source) VALUES (?)", (str(path),)
        ).lastrowid
        with open_archive(path) as archive:
            for count, line in enumerate(archive, 1):
                digest.update(line)
                raw = line.decode("utf-8", errors="replace").rstrip("\r\n")
                record = parse_line(raw)
                connection.execute(
                    INSERT,
                    (import_id, count, raw) + tuple(record[field] for field in FIELDS),
                )
        checksum = digest.hexdigest()
        if connection.execute(
            "SELECT 1 FROM imports WHERE sha256 = ?", (checksum,)
        ).fetchone():
            connection.rollback()
            return 0, True
        connection.execute(
            "UPDATE imports SET sha256 = ? WHERE id = ?", (checksum, import_id)
        )
    return count, False


def collect_sources(inputs, database):
    excluded = {database}
    excluded.update(Path(str(database) + suffix) for suffix in ("-wal", "-shm", "-journal"))
    sources = set()
    for name in inputs:
        path = Path(name).absolute()
        if path.is_symlink():
            raise ValueError("symbolic link inputs are not supported: {}".format(path))
        if path.is_dir():
            candidates = path.rglob("*")
        elif path.is_file():
            candidates = (path,)
        else:
            raise ValueError("input does not exist or is not a regular file: {}".format(path))
        for candidate in candidates:
            if candidate.is_symlink() or not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if resolved not in excluded:
                sources.add(resolved)
    return sorted(sources)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path, help="SQLite database path")
    parser.add_argument("inputs", nargs="+", help="log files or directories (recursive)")
    args = parser.parse_args(argv)
    database = args.database.resolve()
    try:
        sources = collect_sources(args.inputs, database)
        if not sources:
            raise ValueError("no regular log files found")
        with closing(sqlite3.connect(str(database))) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(SCHEMA)
            failed = False
            for path in sources:
                try:
                    count, duplicate = import_archive(connection, path)
                except (OSError, EOFError, lzma.LZMAError, zlib.error, sqlite3.Error) as error:
                    print("{}: {}".format(path, error), file=sys.stderr)
                    failed = True
                else:
                    status = "already imported" if duplicate else "{} lines imported".format(count)
                    print("{}: {}".format(path, status))
            return 1 if failed else 0
    except (OSError, ValueError, sqlite3.Error) as error:
        print("logot: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
