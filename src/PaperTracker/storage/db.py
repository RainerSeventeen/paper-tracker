"""SQLite database utilities."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from PaperTracker.storage.migration import run_migrations


class DatabaseManager:
    """Shared database connection manager.

    Uses singleton pattern to ensure only one connection is created per database path.
    This avoids connection resource waste, transaction isolation issues, and concurrent
    write conflicts.

    Supports context manager protocol for automatic connection cleanup.
    """

    _instance = None

    def __new__(cls, db_path: Path):
        """Create or return existing DatabaseManager instance.

        The singleton is assigned only after both ensure_db and run_migrations
        complete successfully. If run_migrations raises, cls._instance remains
        None so the next call can retry with a clean state.

        Args:
            db_path: Absolute path or project-relative path to database file.

        Returns:
            DatabaseManager singleton instance.
        """
        if cls._instance is None:
            instance = super().__new__(cls)
            instance.conn = ensure_db(db_path)
            run_migrations(instance.conn)
            cls._instance = instance
        return cls._instance

    def get_connection(self) -> sqlite3.Connection:
        """Get the shared database connection.

        Returns:
            SQLite connection.
        """
        return self.conn

    def close(self) -> None:
        """Close the database connection and reset singleton instance.

        This ensures the connection is properly closed and allows creating
        a new instance with a different database path if needed.
        """
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            type(self)._instance = None

    def __enter__(self) -> DatabaseManager:
        """Enter context manager.

        Returns:
            Self for use in with statement.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and close connection.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        self.close()


def ensure_db(db_path: Path) -> sqlite3.Connection:
    """Ensure database file exists and return connection.
    
    Args:
        db_path: Absolute path or project-relative path to database file.
        
    Returns:
        SQLite connection.
        
    Raises:
        OSError: If directory creation fails.
        sqlite3.Error: If database connection fails.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    return conn
