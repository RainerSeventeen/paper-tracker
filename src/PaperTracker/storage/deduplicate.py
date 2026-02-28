"""Deduplication store implementation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Sequence

from PaperTracker.core.models import Paper
from PaperTracker.utils.log import log

if TYPE_CHECKING:
    from PaperTracker.storage.db import DatabaseManager

_DOI_PREFIX_RE = re.compile(r"^(https?://(dx\.)?doi\.org/|doi:)", re.IGNORECASE)


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

        source_to_ids: dict[str, list[str]] = {}
        for paper in papers:
            source_to_ids.setdefault(paper.source, []).append(paper.id)

        seen_pairs = self._fetch_seen_pairs(source_to_ids)
        seen_doi_norms = self._fetch_seen_doi_norms(papers)

        new_papers: list[Paper] = []
        for paper in papers:
            if (paper.source, paper.id) in seen_pairs:
                continue
            doi_norm = normalize_doi(paper.doi)
            if doi_norm and doi_norm in seen_doi_norms:
                continue
            new_papers.append(paper)

        log.debug("Filtered %d new papers out of %d total", len(new_papers), len(papers))
        return new_papers

    def _fetch_seen_pairs(self, source_to_ids: dict[str, list[str]]) -> set[tuple[str, str]]:
        """Fetch persisted `(source, source_id)` keys for candidates."""
        clauses: list[str] = []
        params: list[str] = []
        for source, ids in source_to_ids.items():
            if not ids:
                continue
            placeholders = ",".join("?" for _ in ids)
            clauses.append(f"(source = ? AND source_id IN ({placeholders}))")
            params.append(source)
            params.extend(ids)

        if not clauses:
            return set()

        query = "SELECT source, source_id FROM seen_papers WHERE " + " OR ".join(clauses)
        cursor = self.conn.execute(query, params)
        return {(row[0], row[1]) for row in cursor}

    def _fetch_seen_doi_norms(self, papers: Sequence[Paper]) -> set[str]:
        """Fetch persisted normalized DOI values for candidates."""
        doi_norms_set: set[str] = set()
        for paper in papers:
            doi_norm = normalize_doi(paper.doi)
            if doi_norm:
                doi_norms_set.add(doi_norm)
        doi_norms = sorted(doi_norms_set)
        if not doi_norms:
            return set()

        placeholders = ",".join("?" for _ in doi_norms)
        query = f"""
            SELECT doi_norm FROM seen_papers
            WHERE doi_norm IN ({placeholders})
        """
        cursor = self.conn.execute(query, doi_norms)
        return {row[0] for row in cursor if isinstance(row[0], str) and row[0]}

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


class ReadOnlyDeduplicateStore:
    """Read-only wrapper for deduplication state.

    Wraps a real `SqliteDeduplicateStore` but blocks database writes.
    `mark_seen()` only updates an in-memory session cache, which allows
    deduplication tests without mutating persisted state.
    """

    def __init__(self, real_store: SqliteDeduplicateStore):
        """Initialize a read-only deduplication wrapper.

        Args:
            real_store: The real deduplication store.
        """
        self.real_store = real_store
        self.session_seen_pairs: set[tuple[str, str]] = set()
        self.session_seen_doi_norms: set[str] = set()

    def filter_new(self, papers: Sequence[Paper]) -> list[Paper]:
        """Filter papers using both DB state and session cache.

        Args:
            papers: Papers to filter.

        Returns:
            Papers that are new in both persistent and session scopes.
        """
        new_from_db = self.real_store.filter_new(papers)

        result: list[Paper] = []
        for paper in new_from_db:
            if (paper.source, paper.id) in self.session_seen_pairs:
                continue
            doi_norm = normalize_doi(paper.doi)
            if doi_norm and doi_norm in self.session_seen_doi_norms:
                continue
            result.append(paper)

        log.debug(
            "Read-only filter: %d papers → %d new from DB → %d after session filter",
            len(papers),
            len(new_from_db),
            len(result),
        )

        return result

    def mark_seen(self, papers: Sequence[Paper]) -> None:
        """Mark papers as seen in memory only.

        Args:
            papers: Papers to mark as seen.
        """
        if not papers:
            return

        for paper in papers:
            self.session_seen_pairs.add((paper.source, paper.id))
            doi_norm = normalize_doi(paper.doi)
            if doi_norm:
                self.session_seen_doi_norms.add(doi_norm)

        log.info(
            "[read-only] Marked %d papers as seen (memory only, no DB write)",
            len(papers),
        )


def normalize_doi(doi: str | None) -> str:
    """Normalize DOI text into a canonical key for deduplication.

    Args:
        doi: Raw DOI value that may include URL or ``doi:`` prefixes.

    Returns:
        Lower-cased DOI without known prefixes, or an empty string when input is missing.
    """
    if doi is None:
        return ""
    normalized = doi.strip().lower()
    normalized = _DOI_PREFIX_RE.sub("", normalized)
    return normalized.strip()
