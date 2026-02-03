"""SQLite database utilities."""

from __future__ import annotations

import sqlite3
from pathlib import Path


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

        Args:
            db_path: Absolute path or project-relative path to database file.

        Returns:
            DatabaseManager singleton instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.conn = ensure_db(db_path)
            init_schema(cls._instance.conn)
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


def init_schema(conn: sqlite3.Connection) -> None:
    """Initialize database schema for both deduplication and content storage.

    Args:
        conn: SQLite connection.
    """
    conn.executescript("""
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
    """)
    conn.commit()
