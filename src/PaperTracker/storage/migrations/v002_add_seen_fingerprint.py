"""Migration v002: add and backfill fingerprint identity for seen papers."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from PaperTracker.core.dedup import build_title_author_year_fingerprint
from PaperTracker.core.models import Paper
from PaperTracker.storage.migration import Migration


def _backfill_fingerprint(conn: sqlite3.Connection) -> None:
    """Backfill title_author_year_fingerprint for existing seen_papers rows.

    For each seen_papers row that has no fingerprint, resolves the latest
    paper_content entry and delegates to build_title_author_year_fingerprint,
    guaranteeing byte-for-byte consistency with the runtime dedup path.

    Args:
        conn: Active SQLite connection (called within a migration transaction).
    """
    rows = conn.execute("""
        SELECT sp.source, sp.source_id, pc.title, pc.authors, pc.published_at
        FROM seen_papers sp
        LEFT JOIN (
            SELECT source, source_id, title, authors, published_at,
                   ROW_NUMBER() OVER (
                       PARTITION BY source, source_id
                       ORDER BY fetched_at DESC, id DESC
                   ) AS rn
            FROM paper_content
        ) pc ON pc.source = sp.source AND pc.source_id = sp.source_id AND pc.rn = 1
        WHERE sp.title_author_year_fingerprint IS NULL
    """).fetchall()

    updates = []
    for source, source_id, title, authors_json, published_at in rows:
        try:
            authors = tuple(json.loads(authors_json)) if authors_json else ()
        except (json.JSONDecodeError, TypeError):
            authors = ()
        published = (
            datetime.fromtimestamp(published_at, tz=timezone.utc)
            if published_at is not None
            else None
        )
        paper = Paper(
            source=source,
            id=source_id,
            title=title or "",
            authors=authors,
            abstract="",
            published=published,
            updated=None,
        )
        updates.append((build_title_author_year_fingerprint(paper), source, source_id))

    if updates:
        conn.executemany(
            "UPDATE seen_papers SET title_author_year_fingerprint = ? "
            "WHERE source = ? AND source_id = ?",
            updates,
        )


MIGRATION = Migration(
    version=2,
    description="Add title_author_year_fingerprint to seen_papers",
    sql="""
        ALTER TABLE seen_papers
          ADD COLUMN title_author_year_fingerprint TEXT;

        CREATE INDEX IF NOT EXISTS idx_seen_title_author_year_fingerprint
          ON seen_papers(title_author_year_fingerprint)
          WHERE title_author_year_fingerprint IS NOT NULL
            AND title_author_year_fingerprint <> '';
    """,
    hook=_backfill_fingerprint,
)
