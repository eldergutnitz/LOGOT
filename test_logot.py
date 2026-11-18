import bz2
from contextlib import redirect_stderr, redirect_stdout
import gzip
import io
import lzma
from pathlib import Path
import sqlite3
import tempfile
import unittest

import logot


class ParsingTests(unittest.TestCase):
    def test_rhel_legacy(self):
        record = logot.parse_line("<34>Oct 11 22:14:15 server sshd[123]: Accepted login")
        self.assertEqual(record["event_timestamp"], "Oct 11 22:14:15")
        self.assertEqual(record["hostname"], "server")
        self.assertEqual(record["app_name"], "sshd")
        self.assertEqual(record["proc_id"], "123")
        self.assertEqual((record["facility"], record["severity"]), (4, 2))
        self.assertEqual(record["message"], "Accepted login")

    def test_rhel_iso_timestamp(self):
        record = logot.parse_line("2026-11-13T10:00:00.123+00:00 server kernel: event")
        self.assertEqual(record["parsed"], 1)
        self.assertEqual(record["app_name"], "kernel")
        self.assertIsNone(record["facility"])

    def test_rfc5424_structured_data(self):
        structured = r'[example@123 key="escaped \] value"][other@123 a="b"]'
        record = logot.parse_line(
            '<165>1 2026-11-13T10:00:00Z server app 123 ID47 ' + structured + " event"
        )
        self.assertEqual(record["structured_data"], structured)
        self.assertEqual(record["msg_id"], "ID47")
        self.assertEqual(record["message"], "event")
        self.assertEqual((record["facility"], record["severity"]), (20, 5))

    def test_rfc5424_nil_fields_without_message(self):
        record = logot.parse_line("<13>1 - - - - - -")
        self.assertEqual(record["parsed"], 1)
        self.assertIsNone(record["hostname"])
        self.assertIsNone(record["event_timestamp"])
        self.assertEqual(record["message"], "")

    def test_unknown_lines_preserved(self):
        for raw in ("", "  stack trace", "<999>Oct 11 22:14:15 host app: invalid"):
            with self.subTest(raw=raw):
                record = logot.parse_line(raw)
                self.assertEqual(record["parsed"], 0)
                self.assertEqual(record["message"], raw)
                self.assertIsNone(record["event_timestamp"])


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.connection = sqlite3.connect(":memory:")
        self.addCleanup(self.connection.close)
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(logot.SCHEMA)

    def test_archives_and_content_deduplication(self):
        content = b"Oct 11 22:14:15 host app[1]: event\nunknown\nunknown\n"
        for suffix, compress in (
            ("", lambda value: value), (".gz", gzip.compress),
            (".bz2", bz2.compress), (".xz", lzma.compress),
        ):
            with self.subTest(suffix=suffix):
                path = self.directory / ("messages" + suffix)
                path.write_bytes(compress(content))
                self.assertEqual(
                    logot.import_archive(self.connection, path),
                    (3, False) if suffix == "" else (0, True),
                )
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM logs").fetchone()[0], 3)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM imports").fetchone()[0], 1)
        self.assertEqual(logot.import_archive(self.connection, path), (0, True))

    def test_corrupt_archive_rolls_back(self):
        path = self.directory / "broken.gz"
        path.write_bytes(gzip.compress(b"unknown\n")[:-4])
        with self.assertRaises((EOFError, OSError)):
            logot.import_archive(self.connection, path)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM logs").fetchone()[0], 0)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM imports").fetchone()[0], 0)

    def test_raw_text_and_sql_are_not_executed(self):
        path = self.directory / "messages"
        path.write_bytes(b"'; DROP TABLE logs; --\r\ninvalid \xff\nlast line")
        self.assertEqual(logot.import_archive(self.connection, path), (3, False))
        rows = self.connection.execute(
            "SELECT line_number, raw_message FROM logs ORDER BY line_number"
        ).fetchall()
        self.assertEqual(rows, [(1, "'; DROP TABLE logs; --"), (2, "invalid \ufffd"), (3, "last line")])

    def test_cli_continues_after_corrupt_file_and_excludes_database(self):
        database = self.directory / "logs.db"
        (self.directory / "a.gz").write_bytes(b"not gzip")
        nested = self.directory / "nested"
        nested.mkdir()
        (nested / "messages").write_text("unknown\n", encoding="utf-8")
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(logot.main(["--database", str(database), str(self.directory)]), 1)
            self.assertEqual(logot.main(["--database", str(database), str(nested)]), 0)
        with sqlite3.connect(str(database)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM logs").fetchone()[0], 1)
        self.assertIn("already imported", output.getvalue())
        self.assertIn("a.gz", errors.getvalue())
        self.assertNotIn(database.resolve(), logot.collect_sources([str(self.directory)], database))

    def test_invalid_deflate_stream(self):
        database = self.directory / "logs.db"
        path = self.directory / "broken.gz"
        path.write_bytes(b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff\x07")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(logot.main(["--database", str(database), str(path)]), 1)
        with sqlite3.connect(str(database)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM imports").fetchone()[0], 0)

    def test_empty_directory(self):
        database = self.directory / "logs.db"
        with redirect_stderr(io.StringIO()):
            self.assertEqual(logot.main(["--database", str(database), str(self.directory)]), 1)
        self.assertFalse(database.exists())

    def test_missing_input_and_symlinks(self):
        database = self.directory / "logs.db"
        with redirect_stderr(io.StringIO()):
            self.assertEqual(logot.main(["--database", str(database), str(self.directory / "missing")]), 1)
        self.assertFalse(database.exists())
        path = self.directory / "messages"
        path.write_text("unknown\n", encoding="utf-8")
        link = self.directory / "link"
        link.symlink_to(path)
        self.assertEqual(logot.collect_sources([str(self.directory)], database), [path])
        with self.assertRaises(ValueError):
            logot.collect_sources([str(link)], database)


if __name__ == "__main__":
    unittest.main()
