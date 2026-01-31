"""Deduplication store implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from PaperTracker.core.models import Paper
from PaperTracker.utils.log import log

if TYPE_CHECKING:
    from PaperTracker.storage.db import DatabaseManager


class SqliteDeduplicateStore:
    """SQLite-based deduplication store for tracking seen papers."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize deduplication store.

        Args:
            db_manager: Shared database manager instance.
        """
        log.debug("Initializing SqliteDeduplicateStore")
        self.conn = db_manager.get_connection()
    
    def filter_new(self, papers: Sequence[Paper]) -> list[Paper]:
        """Filter papers to only new ones not seen before.
        
        Args:
            papers: Papers to filter.
            
        Returns:
            List of papers not in the database.
        """
        if not papers:
            return []
        
        placeholders = ",".join("?" * len(papers))
        query = f"""
            SELECT source_id FROM seen_papers 
            WHERE source = ? AND source_id IN ({placeholders})
        """
        
        cursor = self.conn.execute(
            query, 
            [papers[0].source] + [p.id for p in papers]
        )
        seen_ids = {row[0] for row in cursor}
        
        new_papers = [p for p in papers if p.id not in seen_ids]
        log.debug("Filtered %d new papers out of %d total", len(new_papers), len(papers))
        return new_papers
    
    def mark_seen(self, papers: Sequence[Paper]) -> None:
        """Mark papers as seen in the state store.
        
        Args:
            papers: Papers to mark as seen.
        """
        if not papers:
            return
        
        for paper in papers:
            self.conn.execute(
                """
                INSERT INTO seen_papers (source, source_id, doi, title)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source, source_id) DO UPDATE SET
                    title = excluded.title,
                    doi = excluded.doi
                """,
                (
                    paper.source,
                    paper.id,
                    paper.doi,
                    paper.title,
                ),
            )
        
        self.conn.commit()
        log.debug("Marked %d papers as seen", len(papers))
