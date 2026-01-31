"""Paper content storage implementation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Sequence

from PaperTracker.core.models import Paper
from PaperTracker.utils.log import log

if TYPE_CHECKING:
    from PaperTracker.storage.db import DatabaseManager


class PaperContentStore:
    """SQLite-based content store for full paper data.

    Stores complete paper metadata, summaries, and LLM-enhanced fields (translation).
    Separated from deduplication storage for cleaner concerns separation.
    """

    def __init__(self, db_manager: DatabaseManager):
        """Initialize content store.

        Args:
            db_manager: Shared database manager instance.
        """
        log.debug("Initializing PaperContentStore")
        self.conn = db_manager.get_connection()

    def save_papers(self, papers: Sequence[Paper]) -> None:
        """Save full paper content to database.

        Args:
            papers: Papers to save (must already exist in seen_papers).

        Note:
            Papers are linked to seen_papers via seen_paper_id foreign key.
            Papers not found in seen_papers will be skipped with a warning.
        """
        if not papers:
            return

        for paper in papers:
            # Get seen_paper_id
            cursor = self.conn.execute(
                "SELECT id FROM seen_papers WHERE source = ? AND source_id = ?",
                (paper.source, paper.id),
            )
            row = cursor.fetchone()
            if not row:
                log.warning("Paper %s not in seen_papers, skipping content save", paper.id)
                continue

            seen_paper_id = row[0]

            # Extract links from extra field
            code_urls = paper.extra.get("code_urls", [])
            project_urls = paper.extra.get("project_urls", [])

            # Insert full content
            self.conn.execute(
                """
                INSERT INTO paper_content (
                    seen_paper_id, source, source_id, title, authors, summary,
                    published_at, updated_at, primary_category, categories,
                    abstract_url, pdf_url, code_urls, project_urls, doi, extra
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    seen_paper_id,
                    paper.source,
                    paper.id,
                    paper.title,
                    json.dumps(list(paper.authors), ensure_ascii=False),
                    paper.summary,
                    int(paper.published.timestamp()) if paper.published else None,
                    int(paper.updated.timestamp()) if paper.updated else None,
                    paper.primary_category,
                    json.dumps(list(paper.categories), ensure_ascii=False),
                    paper.links.abstract,
                    paper.links.pdf,
                    json.dumps(code_urls, ensure_ascii=False),
                    json.dumps(project_urls, ensure_ascii=False),
                    paper.doi,
                    json.dumps(dict(paper.extra), ensure_ascii=False),
                ),
            )

        self.conn.commit()
        log.debug("Saved %d papers to content store", len(papers))

    def update_translation(self, source_id: str, translation: str, language: str) -> None:
        """Update translation for a paper.

        Args:
            source_id: Paper source ID.
            translation: Translated summary content.
            language: Target language code (e.g., 'zh', 'en').
        """
        self.conn.execute(
            "UPDATE paper_content SET translation = ?, language = ? WHERE source_id = ?",
            (translation, language, source_id),
        )
        self.conn.commit()
        log.debug("Updated translation for paper %s to %s", source_id, language)

    def get_recent_papers(self, limit: int = 100, days: int | None = None) -> list[dict]:
        """Get recent papers from content store.

        Args:
            limit: Maximum number of papers to return.
            days: Optional filter for papers fetched in last N days.

        Returns:
            List of paper dictionaries with metadata and translation fields.
        """
        query = """
            SELECT
                c.source_id, c.title, c.authors, c.summary,
                c.published_at, c.fetched_at, c.primary_category,
                c.abstract_url, c.pdf_url, c.code_urls,
                c.translation, c.language
            FROM paper_content c
        """
        params = []

        if days is not None:
            query += " WHERE c.fetched_at > strftime('%s', 'now', ?)"
            params.append(f"-{days} days")

        query += " ORDER BY c.fetched_at DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(query, params)

        return [
            {
                "source_id": row[0],
                "title": row[1],
                "authors": json.loads(row[2]),
                "summary": row[3],
                "published_at": row[4],
                "fetched_at": row[5],
                "primary_category": row[6],
                "abstract_url": row[7],
                "pdf_url": row[8],
                "code_urls": json.loads(row[9]) if row[9] else [],
                "translation": row[10],
                "language": row[11],
            }
            for row in cursor
        ]

    def get_statistics(self) -> dict:
        """Get content store statistics.

        Returns:
            Dictionary with statistics including total records, unique papers,
            categories count, and first/last fetch timestamps.
        """
        cursor = self.conn.execute(
            """
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT source_id) as unique_papers,
                COUNT(DISTINCT primary_category) as categories,
                MIN(fetched_at) as first_fetch,
                MAX(fetched_at) as last_fetch
            FROM paper_content
        """
        )
        row = cursor.fetchone()

        return {
            "total_records": row[0],
            "unique_papers": row[1],
            "categories": row[2],
            "first_fetch": row[3],
            "last_fetch": row[4],
        }
