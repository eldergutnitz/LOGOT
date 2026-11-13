# LOGOT

Import syslog archives from a RHEL server into a local SQLite database. Requires
Python 3.6+ with SQLite support; no third-party packages or database server are
needed. This is a batch importer, not a syslog network receiver.

## Usage

Run on the server, or copy the archives to a machine running Python:

```sh
python3 logot.py --database /path/to/logs.db /var/log/messages-20261101.gz
python3 logot.py --database /path/to/logs.db /path/to/syslog-archives/
```

Multiple files and directories may be supplied. Directories are searched
recursively; **every regular file** is treated as a log, so use a dedicated archive
directory, not all of `/var/log`. Plain files and `.gz`, `.bz2`, and `.xz` archives
are supported. Symbolic links are not followed. The database and its SQLite
sidecar files are excluded from directory imports.

The database is created automatically; its parent directory must already exist.
Use an account that can read the selected logs and write the database. Avoid
running as root: copy restricted archives into a suitably protected directory
instead. Logs may contain sensitive information; protect both archives and the
database with appropriate filesystem permissions (for example, run with
`umask 077`). Import only trusted local archives; there is no decompressed-size
limit.

## Stored data

The `logs` table contains one row per line:

- `event_timestamp`, `hostname`, `app_name`, `proc_id`, `msg_id`,
  `structured_data`, `facility`, `severity`, and `message` where recognized.
- `raw_message` retains the original line without its line ending. Input is
  decoded as UTF-8, replacing invalid bytes with the replacement character.
- `parsed` is 1 for recognized headers, otherwise 0. Unrecognized lines,
  blank lines, and multiline continuations are retained as separate rows.
- `import_id` links to `imports`, which records the original absolute source
  path, SHA-256 of the decompressed bytes, and UTC import time. `line_number`
  is the original one-based line number.

Recognizes traditional RFC3164-style messages, RHEL/rsyslog ISO-timestamp
messages, and RFC5424 headers with structured data. Timestamps are stored **as
written**, without normalization or guessing the year/timezone missing from
traditional syslog. Missing fields are NULL; facility/severity are available
only when the line includes a valid `<PRI>` prefix.

Each file is imported in one transaction. Corrupt/unreadable files are rolled
back, errors are printed to stderr, and other files continue. Exit status is 0
on success (including duplicates), 1 on an import/input error, and 2 for invalid
command-line usage.

Repeated imports of identical decompressed file contents are skipped, even if
renamed or recompressed. Repeated lines within a file are preserved. Overlapping
but nonidentical files are imported independently; this does not deduplicate
individual events across rotated logs. The source path is that of the first
successfully imported copy.

Query the database using SQLite, for example:

```sql
SELECT i.source, l.line_number, l.event_timestamp, l.hostname, l.message
FROM logs AS l JOIN imports AS i ON i.id = l.import_id
WHERE l.app_name = 'sshd'
ORDER BY l.id;
```

Timestamp and hostname columns are indexed. Textual timestamps from different
formats/timezones are not suitable for chronological sorting without further
normalization.

## Verification

```sh
python3 -m unittest -v
```