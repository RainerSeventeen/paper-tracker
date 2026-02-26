"""Tests for schema migration mechanism.

Covers the five core scenarios from the migration plan:
  1. 全新数据库     - all tables created, schema_version written
  2. 存量旧库       - legacy tables preserved, schema_version added
  3. 版本已最新     - second run executes no DDL
  4. 新增迁移脚本   - v2 migration applied to existing DB, old data intact
  5. 迁移 SQL 错误  - transaction rolled back, version unchanged
Plus: version-gap validation raises ValueError at startup.
"""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import PaperTracker.storage.migration as migration_module
from PaperTracker.storage.migration import MIGRATIONS, Migration, run_migrations


def _connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(str(path))


def _current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT version FROM schema_version WHERE id = 1"
    ).fetchone()
    return row[0] if row else 0


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


_LATEST_VERSION = max(m.version for m in MIGRATIONS)


# ---------------------------------------------------------------------------
# Scenario 1: 全新数据库
# ---------------------------------------------------------------------------


class TestFreshDatabase(unittest.TestCase):
    """First run on a database file that does not yet exist."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db_path = Path(self._tmpdir.name) / "papers.db"
        self._conn = _connect(self._db_path)

    def tearDown(self):
        self._conn.close()
        self._tmpdir.cleanup()

    def test_schema_version_equals_latest(self):
        run_migrations(self._conn)
        self.assertEqual(_current_version(self._conn), _LATEST_VERSION)

    def test_main_tables_created(self):
        run_migrations(self._conn)
        tables = _table_names(self._conn)
        for name in ("seen_papers", "paper_content", "llm_generated", "schema_version"):
            with self.subTest(table=name):
                self.assertIn(name, tables)


# ---------------------------------------------------------------------------
# Scenario 2: 存量旧库（无 schema_version 表）
# ---------------------------------------------------------------------------


class TestLegacyDatabase(unittest.TestCase):
    """Upgrade path: tables exist from old code, no schema_version table."""

    _LEGACY_DDL = """
        CREATE TABLE IF NOT EXISTS seen_papers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source TEXT NOT NULL,
          source_id TEXT NOT NULL,
          doi TEXT,
          doi_norm TEXT GENERATED ALWAYS AS (
            CASE
              WHEN doi IS NULL OR trim(doi) = '' THEN NULL
              ELSE lower(trim(replace(replace(replace(replace(
                replace(trim(doi), 'https://doi.org/', ''),
              'http://doi.org/', ''),
              'https://dx.doi.org/', ''),
              'http://dx.doi.org/', ''),
              'doi:', '')))
            END
          ) STORED,
          title TEXT NOT NULL,
          first_seen_at INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
          UNIQUE(source, source_id)
        );

        CREATE TABLE IF NOT EXISTS paper_content (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          seen_paper_id INTEGER NOT NULL,
          source TEXT NOT NULL,
          source_id TEXT NOT NULL,
          title TEXT NOT NULL,
          authors TEXT NOT NULL,
          abstract TEXT NOT NULL,
          published_at INTEGER,
          updated_at INTEGER,
          fetched_at INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
          primary_category TEXT,
          categories TEXT,
          abstract_url TEXT,
          pdf_url TEXT,
          code_urls TEXT,
          project_urls TEXT,
          doi TEXT,
          extra TEXT,
          FOREIGN KEY (seen_paper_id) REFERENCES seen_papers(id) ON DELETE CASCADE,
          UNIQUE(source, source_id, fetched_at)
        );
    """

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "legacy.db"
        self._conn = _connect(db_path)
        # Build legacy state: tables without schema_version
        self._conn.executescript(self._LEGACY_DDL)
        self._conn.execute(
            "INSERT INTO seen_papers (source, source_id, title) VALUES (?, ?, ?)",
            ("arxiv", "2501.00001", "Legacy Paper"),
        )
        self._conn.commit()

    def tearDown(self):
        self._conn.close()
        self._tmpdir.cleanup()

    def test_existing_data_preserved(self):
        run_migrations(self._conn)
        count = self._conn.execute(
            "SELECT COUNT(*) FROM seen_papers"
        ).fetchone()[0]
        self.assertEqual(count, 1)
        row = self._conn.execute(
            "SELECT source_id, title FROM seen_papers"
        ).fetchone()
        self.assertEqual(row[0], "2501.00001")
        self.assertEqual(row[1], "Legacy Paper")

    def test_schema_version_created(self):
        run_migrations(self._conn)
        self.assertEqual(_current_version(self._conn), _LATEST_VERSION)


# ---------------------------------------------------------------------------
# Scenario 3: 版本已最新
# ---------------------------------------------------------------------------


class TestAlreadyUpToDate(unittest.TestCase):
    """Second run after DB is already at the latest version."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "papers.db"
        self._conn = _connect(db_path)
        run_migrations(self._conn)  # first run

    def tearDown(self):
        self._conn.close()
        self._tmpdir.cleanup()

    def test_version_unchanged_on_second_run(self):
        version_before = _current_version(self._conn)
        run_migrations(self._conn)
        self.assertEqual(_current_version(self._conn), version_before)

    def test_no_new_tables_on_second_run(self):
        tables_before = _table_names(self._conn)
        run_migrations(self._conn)
        self.assertEqual(_table_names(self._conn), tables_before)


# ---------------------------------------------------------------------------
# Scenario 4: 新增迁移脚本（模拟未来版本升级）
# ---------------------------------------------------------------------------


class TestNewMigration(unittest.TestCase):
    """Simulated v2 migration applied to a v1 database."""

    _V2 = Migration(
        version=2,
        description="Add tags column to seen_papers",
        sql="ALTER TABLE seen_papers ADD COLUMN tags TEXT;",
    )

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "papers.db"
        self._conn = _connect(db_path)
        # Bring DB to v1
        run_migrations(self._conn)
        # Insert a pre-existing row
        self._conn.execute(
            "INSERT INTO seen_papers (source, source_id, title) VALUES (?, ?, ?)",
            ("arxiv", "2501.00002", "Pre-v2 Paper"),
        )
        self._conn.commit()

    def tearDown(self):
        self._conn.close()
        self._tmpdir.cleanup()

    def test_version_advances_to_v2(self):
        with patch.object(migration_module, "MIGRATIONS", list(MIGRATIONS) + [self._V2]):
            run_migrations(self._conn)
        self.assertEqual(_current_version(self._conn), 2)

    def test_new_column_exists(self):
        with patch.object(migration_module, "MIGRATIONS", list(MIGRATIONS) + [self._V2]):
            run_migrations(self._conn)
        # tags column should be queryable
        row = self._conn.execute(
            "SELECT tags FROM seen_papers WHERE source_id = '2501.00002'"
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertIsNone(row[0])  # default NULL

    def test_old_data_preserved_after_v2(self):
        with patch.object(migration_module, "MIGRATIONS", list(MIGRATIONS) + [self._V2]):
            run_migrations(self._conn)
        count = self._conn.execute(
            "SELECT COUNT(*) FROM seen_papers"
        ).fetchone()[0]
        self.assertEqual(count, 1)


# ---------------------------------------------------------------------------
# Scenario 5: 迁移 SQL 错误 → 事务回滚
# ---------------------------------------------------------------------------


class TestRollbackOnError(unittest.TestCase):
    """Bad migration SQL causes exception; version number must not change."""

    _BAD_V2 = Migration(
        version=2,
        description="Intentionally broken migration",
        sql="THIS IS NOT VALID SQL;",
    )

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "papers.db"
        self._conn = _connect(db_path)
        run_migrations(self._conn)

    def tearDown(self):
        self._conn.close()
        self._tmpdir.cleanup()

    def test_exception_raised(self):
        with patch.object(migration_module, "MIGRATIONS", list(MIGRATIONS) + [self._BAD_V2]):
            with self.assertRaises(Exception):
                run_migrations(self._conn)

    def test_version_unchanged_after_bad_migration(self):
        version_before = _current_version(self._conn)
        with patch.object(migration_module, "MIGRATIONS", list(MIGRATIONS) + [self._BAD_V2]):
            try:
                run_migrations(self._conn)
            except Exception:
                pass
        self.assertEqual(_current_version(self._conn), version_before)


# ---------------------------------------------------------------------------
# 版本号连续性校验
# ---------------------------------------------------------------------------


class TestVersionContinuityValidation(unittest.TestCase):
    """run_migrations raises ValueError if MIGRATIONS has a version gap."""

    def test_gap_raises_value_error(self):
        gap_migrations = list(MIGRATIONS) + [
            Migration(
                version=_LATEST_VERSION + 2,  # intentional gap: skip one version
                description="Gap migration",
                sql="SELECT 1;",
            )
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            conn = _connect(Path(tmpdir) / "papers.db")
            try:
                with patch.object(migration_module, "MIGRATIONS", gap_migrations):
                    with self.assertRaises(ValueError):
                        run_migrations(conn)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
