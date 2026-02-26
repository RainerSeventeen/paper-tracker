"""Schema migration mechanism for PaperTracker's SQLite database.

Provides versioned, ordered migrations that are applied automatically at
DatabaseManager initialization time. Each migration runs in an explicit
transaction; failures roll back atomically, leaving the database in a safe
state.

Migration SQL lives in individual modules under the ``migrations/`` sub-package
(one file per version, named ``vNNN_<description>.py``).  Each module exposes a
single ``MIGRATION`` constant of type :class:`Migration`.  Add a new version by
dropping a new file into that directory — no changes to this module required.
"""

from __future__ import annotations

import importlib
import pkgutil
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
# Migration registry — populated automatically from the migrations/ sub-package
# ---------------------------------------------------------------------------


def _load_migrations() -> list[Migration]:
    """Discover and return all Migration objects from the migrations sub-package.

    Scans ``PaperTracker.storage.migrations`` for modules that expose a
    ``MIGRATION`` attribute of type :class:`Migration`, then returns them
    sorted ascending by version.  File names should follow the
    ``vNNN_<description>.py`` convention; only the ``MIGRATION`` attribute
    name is significant at runtime.

    Returns:
        Sorted list of Migration objects, one per discovered module.
    """
    import PaperTracker.storage.migrations as _pkg

    result: list[Migration] = []
    for _, module_name, _ in pkgutil.iter_modules(_pkg.__path__):
        mod = importlib.import_module(
            f"PaperTracker.storage.migrations.{module_name}"
        )
        if hasattr(mod, "MIGRATION") and isinstance(mod.MIGRATION, Migration):
            result.append(mod.MIGRATION)
    return sorted(result, key=lambda m: m.version)


MIGRATIONS: list[Migration] = _load_migrations()


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
