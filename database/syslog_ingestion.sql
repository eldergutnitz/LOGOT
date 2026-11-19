-- Syslog ingestion schema for BASE0
-- Creates target table, dedup index, and rejected-lines table.

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
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_syslog_rawline
    ON syslog_device_logs ((md5(raw_line)));

CREATE TABLE IF NOT EXISTS syslog_rejected_logs (
    id BIGSERIAL PRIMARY KEY,
    source_file TEXT NOT NULL,
    line_number INT NOT NULL,
    raw_line TEXT NOT NULL,
    reject_reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_line_md5 TEXT GENERATED ALWAYS AS (md5(raw_line)) STORED
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_syslog_rejected_unique
    ON syslog_rejected_logs (source_file, line_number, raw_line_md5);
