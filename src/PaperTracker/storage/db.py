"""SQLite database utilities."""

from __future__ import annotations

import sqlite3
from pathlib import Path


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
    """Initialize database schema.
    
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
        
        CREATE INDEX IF NOT EXISTS idx_seen_doi_norm
          ON seen_papers(doi_norm)
          WHERE doi_norm IS NOT NULL AND doi_norm <> '';
        
        CREATE INDEX IF NOT EXISTS idx_seen_first_seen
          ON seen_papers(first_seen_at);
    """)
    conn.commit()
