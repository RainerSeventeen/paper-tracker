"""Deduplication persistence layer.

Tracks seen papers in SQLite and filters incoming batches using DOI-first and fingerprint fallback identities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from PaperTracker.core.dedup import (
    build_title_author_year_fingerprint,
    normalize_doi,
)
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

        source_to_ids: dict[str, list[str]] = {}
        for paper in papers:
            source_to_ids.setdefault(paper.source, []).append(paper.id)

        seen_doi_norms = self._fetch_seen_doi_norms(papers)
        seen_fingerprints = self._fetch_seen_fingerprints(papers)
        seen_pairs = self._fetch_seen_pairs(source_to_ids)
        return self._filter_against_seen(
            papers=papers,
            seen_doi_norms=seen_doi_norms,
            seen_fingerprints=seen_fingerprints,
            seen_pairs=seen_pairs,
        )

    def filter_new_in_source(self, source: str, papers: Sequence[Paper]) -> list[Paper]:
        """Filter papers with persistent state from one source only.

        This method is intended for source-level paged fetching. It only checks
        persisted seen-state within the provided source, and therefore does not
        coordinate duplicates across different sources.

        Args:
            source: Source name that owns the current paged fetch.
            papers: Papers to filter.

        Returns:
            List of papers not seen before within the same source.
        """
        if not papers:
            return []

        source_to_ids = {source: [paper.id for paper in papers]}
        seen_doi_norms = self._fetch_seen_doi_norms(papers, source_scope=source)
        seen_fingerprints = self._fetch_seen_fingerprints(papers, source_scope=source)
        seen_pairs = self._fetch_seen_pairs(source_to_ids)
        return self._filter_against_seen(
            papers=papers,
            seen_doi_norms=seen_doi_norms,
            seen_fingerprints=seen_fingerprints,
            seen_pairs=seen_pairs,
        )

    def _filter_against_seen(
        self,
        *,
        papers: Sequence[Paper],
        seen_doi_norms: set[str],
        seen_fingerprints: set[str],
        seen_pairs: set[tuple[str, str]],
    ) -> list[Paper]:
        """Filter candidate papers with pre-fetched seen-state sets."""

        new_papers: list[Paper] = []
        hit_doi = 0
        hit_fingerprint = 0
        hit_pair = 0
        for paper in papers:
            doi_norm = normalize_doi(paper.doi)
            if doi_norm and doi_norm in seen_doi_norms:
                hit_doi += 1
                continue
            fingerprint = build_title_author_year_fingerprint(paper)
            if fingerprint and fingerprint in seen_fingerprints:
                hit_fingerprint += 1
                continue
            if (paper.source, paper.id) in seen_pairs:
                hit_pair += 1
                continue
            new_papers.append(paper)

        log.debug(
            "Filtered %d new papers out of %d total (dedup_hit_doi=%d dedup_hit_fingerprint=%d dedup_hit_pair=%d)",
            len(new_papers),
            len(papers),
            hit_doi,
            hit_fingerprint,
            hit_pair,
        )
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

    def _fetch_seen_doi_norms(
        self,
        papers: Sequence[Paper],
        *,
        source_scope: str | None = None,
    ) -> set[str]:
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
        if source_scope:
            query = f"""
                SELECT doi_norm FROM seen_papers
                WHERE source = ? AND doi_norm IN ({placeholders})
            """
            cursor = self.conn.execute(query, [source_scope, *doi_norms])
        else:
            query = f"""
                SELECT doi_norm FROM seen_papers
                WHERE doi_norm IN ({placeholders})
            """
            cursor = self.conn.execute(query, doi_norms)
        return {row[0] for row in cursor if isinstance(row[0], str) and row[0]}

    def _fetch_seen_fingerprints(
        self,
        papers: Sequence[Paper],
        *,
        source_scope: str | None = None,
    ) -> set[str]:
        """Fetch persisted title/author/year fingerprints for candidates."""
        fingerprints_set: set[str] = set()
        for paper in papers:
            fingerprint = build_title_author_year_fingerprint(paper)
            if fingerprint:
                fingerprints_set.add(fingerprint)
        fingerprints = sorted(fingerprints_set)
        if not fingerprints:
            return set()

        placeholders = ",".join("?" for _ in fingerprints)
        if source_scope:
            query = f"""
                SELECT title_author_year_fingerprint FROM seen_papers
                WHERE source = ? AND title_author_year_fingerprint IN ({placeholders})
            """
            cursor = self.conn.execute(query, [source_scope, *fingerprints])
        else:
            query = f"""
                SELECT title_author_year_fingerprint FROM seen_papers
                WHERE title_author_year_fingerprint IN ({placeholders})
            """
            cursor = self.conn.execute(query, fingerprints)
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
                INSERT INTO seen_papers (source, source_id, doi, title, title_author_year_fingerprint)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source, source_id) DO UPDATE SET
                    title = excluded.title,
                    doi = excluded.doi,
                    title_author_year_fingerprint = excluded.title_author_year_fingerprint
                """,
                (
                    paper.source,
                    paper.id,
                    paper.doi,
                    paper.title,
                    build_title_author_year_fingerprint(paper),
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
        self.session_seen_fingerprints: set[str] = set()
        self.session_seen_doi_norms_by_source: dict[str, set[str]] = {}
        self.session_seen_fingerprints_by_source: dict[str, set[str]] = {}

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
            fingerprint = build_title_author_year_fingerprint(paper)
            if fingerprint and fingerprint in self.session_seen_fingerprints:
                continue
            if (paper.source, paper.id) in self.session_seen_pairs:
                continue
            result.append(paper)

        log.debug(
            "Read-only filter: %d papers → %d new from DB → %d after session filter",
            len(papers),
            len(new_from_db),
            len(result),
        )

        return result

    def filter_new_in_source(self, source: str, papers: Sequence[Paper]) -> list[Paper]:
        """Filter papers for one source using DB state and source-local session cache.

        Args:
            source: Source name that owns the current paged fetch.
            papers: Papers to filter.

        Returns:
            Papers that are new in both persistent state and source-local session scope.
        """
        new_from_db = self.real_store.filter_new_in_source(source, papers)
        source_seen_doi = self.session_seen_doi_norms_by_source.get(source, set())
        source_seen_fingerprint = self.session_seen_fingerprints_by_source.get(source, set())

        result: list[Paper] = []
        for paper in new_from_db:
            if (paper.source, paper.id) in self.session_seen_pairs:
                continue
            doi_norm = normalize_doi(paper.doi)
            if doi_norm and doi_norm in source_seen_doi:
                continue
            fingerprint = build_title_author_year_fingerprint(paper)
            if fingerprint and fingerprint in source_seen_fingerprint:
                continue
            result.append(paper)
        return result

    def mark_seen(self, papers: Sequence[Paper]) -> None:
        """Mark papers as seen in memory only.

        Args:
            papers: Papers to mark as seen.
        """
        if not papers:
            return

        for paper in papers:
            doi_norm = normalize_doi(paper.doi)
            if doi_norm:
                self.session_seen_doi_norms.add(doi_norm)
                self.session_seen_doi_norms_by_source.setdefault(paper.source, set()).add(doi_norm)
            fingerprint = build_title_author_year_fingerprint(paper)
            if fingerprint:
                self.session_seen_fingerprints.add(fingerprint)
                self.session_seen_fingerprints_by_source.setdefault(paper.source, set()).add(fingerprint)
            self.session_seen_pairs.add((paper.source, paper.id))

        log.info(
            "[read-only] Marked %d papers as seen (memory only, no DB write)",
            len(papers),
        )
