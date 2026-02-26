"""Schema migration mechanism for PaperTracker's SQLite database.

Provides versioned, ordered migrations that are applied automatically at
DatabaseManager initialization time. Each migration runs in an explicit
transaction; failures roll back atomically, leaving the database in a safe
state.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from PaperTracker.utils.log import log

# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

_MIN_SQLITE_VERSION = (3, 31, 0)

_SCHEMA_VERSION_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    id      INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
)
"""


@dataclass(frozen=True)
class Migration:
    """A single versioned schema migration.

    Attributes:
        version: Monotonically increasing integer, starting at 1.
        description: Human-readable summary of what this migration does.
        sql: One or more semicolon-separated DDL/DML statements to execute.
    """

    version: int
    description: str
    sql: str


# ---------------------------------------------------------------------------
# Migration list (append-only; never modify published entries)
# ---------------------------------------------------------------------------

MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description="Initial schema: seen_papers, paper_content, llm_generated",
        sql="""
            CREATE TABLE IF NOT EXISTS seen_papers (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source TEXT NOT NULL,
              source_id TEXT NOT NULL,
              doi TEXT,
              doi_norm TEXT GENERATED ALWAYS AS (
                CASE
                  WHEN doi IS NULL OR trim(doi) = '' THEN NULL
                  ELSE lower(
                    trim(
                      replace(
                        replace(
                          replace(
                            replace(
                              replace(trim(doi), 'https://doi.org/', ''),
                            'http://doi.org/', ''),
                          'https://dx.doi.org/', ''),
                        'http://dx.doi.org/', ''),
                      'doi:', '')
                    )
                  )
                END
              ) STORED,
              title TEXT NOT NULL,
              first_seen_at INTEGER NOT NULL DEFAULT (
                CAST(strftime('%s','now') AS INTEGER)
              ),
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

            CREATE INDEX IF NOT EXISTS idx_seen_doi_norm
              ON seen_papers(doi_norm)
              WHERE doi_norm IS NOT NULL AND doi_norm <> '';

            CREATE INDEX IF NOT EXISTS idx_seen_first_seen
              ON seen_papers(first_seen_at);

            CREATE INDEX IF NOT EXISTS idx_content_seen_paper
              ON paper_content(seen_paper_id);

            CREATE INDEX IF NOT EXISTS idx_content_source_id
              ON paper_content(source, source_id);

            CREATE INDEX IF NOT EXISTS idx_content_fetched
              ON paper_content(fetched_at);

            CREATE INDEX IF NOT EXISTS idx_content_category
              ON paper_content(primary_category);

            CREATE TABLE IF NOT EXISTS llm_generated (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              paper_content_id INTEGER NOT NULL,
              generated_at INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
              provider TEXT NOT NULL,
              model TEXT NOT NULL,
              language TEXT NOT NULL,
              abstract_translation TEXT,
              summary_tldr TEXT,
              summary_motivation TEXT,
              summary_method TEXT,
              summary_result TEXT,
              summary_conclusion TEXT,
              extra TEXT,
              FOREIGN KEY (paper_content_id) REFERENCES paper_content(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_llm_generated_paper
              ON llm_generated(paper_content_id);

            CREATE INDEX IF NOT EXISTS idx_llm_generated_time
              ON llm_generated(generated_at DESC);
        """,
    ),
]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_migrations(conn: sqlite3.Connection) -> None:
    """Apply all pending migrations to the database.

    Steps performed on every call:
      1. Check that the runtime SQLite library is >= 3.31.0.
      2. Validate that MIGRATIONS version numbers are consecutive from 1.
      3. Ensure the schema_version bookkeeping table exists.
      4. Read the current version from schema_version (0 if not yet written).
      5. Execute each migration whose version exceeds the current version,
         inside an explicit transaction.

    Args:
        conn: Active SQLite connection.

    Raises:
        RuntimeError: If the SQLite library version is below 3.31.0.
        ValueError: If MIGRATIONS contains a version gap or does not start at 1.
        sqlite3.Error: If a migration statement fails (transaction is rolled back).
    """
    _check_sqlite_version()
    _validate_migration_list(MIGRATIONS)
    _ensure_version_table(conn)

    current_ver = _get_current_version(conn)
    pending = [m for m in MIGRATIONS if m.version > current_ver]

    if not pending:
        log.debug("schema already at version %d, no migrations to run", current_ver)
        return

    for migration in pending:
        _apply_migration(conn, migration)
        log.info(
            "applied migration v%d: %s", migration.version, migration.description
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _check_sqlite_version() -> None:
    """Raise RuntimeError if the SQLite library is older than 3.31.0.

    The STORED generated column syntax used in seen_papers.doi_norm requires
    SQLite >= 3.31.0.  Older versions cannot add generated columns to existing
    tables, which would silently skip the constraint on legacy databases.
    """
    raw = sqlite3.sqlite_version  # e.g. "3.39.5"
    parts = tuple(int(x) for x in raw.split("."))
    if parts < _MIN_SQLITE_VERSION:
        required = ".".join(str(x) for x in _MIN_SQLITE_VERSION)
        raise RuntimeError(
            f"SQLite >= {required} is required (found {raw}). "
            "Please upgrade your SQLite library."
        )


def _validate_migration_list(migrations: list[Migration]) -> None:
    """Raise ValueError if migration version numbers are not consecutive from 1.

    An empty list is considered valid (no migrations registered yet).

    Args:
        migrations: The list of Migration objects to validate.

    Raises:
        ValueError: If the list does not start at version 1, or contains gaps.
    """
    if not migrations:
        return
    for expected, m in enumerate(migrations, start=1):
        if m.version != expected:
            raise ValueError(
                f"MIGRATIONS version gap: expected version {expected}, "
                f"got {m.version} (description: {m.description!r}). "
                "Migration versions must be consecutive starting from 1."
            )


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    """Create the schema_version bookkeeping table if it does not exist.

    The table enforces a single-row invariant via CHECK (id = 1).

    Args:
        conn: Active SQLite connection.
    """
    conn.execute(_SCHEMA_VERSION_DDL)
    conn.commit()


def _get_current_version(conn: sqlite3.Connection) -> int:
    """Return the highest migration version already applied to the database.

    Returns 0 when the schema_version table exists but contains no rows
    (i.e., the database has never been migrated).

    Args:
        conn: Active SQLite connection.

    Returns:
        Current schema version integer (0 if uninitialized).
    """
    row = conn.execute(
        "SELECT version FROM schema_version WHERE id = 1"
    ).fetchone()
    return row[0] if row else 0


def _apply_migration(conn: sqlite3.Connection, migration: Migration) -> None:
    """Execute a single migration inside an explicit transaction.

    The migration SQL may contain multiple semicolon-separated statements.
    Each statement is executed individually with conn.execute() (never
    executescript(), which would issue an implicit COMMIT and break atomicity).
    After all statements succeed, the schema_version row is updated and the
    transaction is committed.  On any failure the transaction is rolled back.

    Args:
        conn: Active SQLite connection.
        migration: The Migration to apply.

    Raises:
        sqlite3.Error: If any statement fails; the transaction is rolled back.
    """
    conn.execute("BEGIN")
    try:
        statements = [
            s.strip() for s in migration.sql.split(";") if s.strip()
        ]
        for stmt in statements:
            conn.execute(stmt)
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (id, version) VALUES (1, ?)",
            (migration.version,),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
