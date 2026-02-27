"""Search service layer for multi-source paper aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import TYPE_CHECKING, Protocol, Sequence

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.utils.log import log

if TYPE_CHECKING:
    from PaperTracker.storage.deduplicate import SqliteDeduplicateStore

_TITLE_WS_RE = re.compile(r"\s+")
_TITLE_STRIP_RE = re.compile(r"[^a-z0-9 ]")
_TITLE_DEDUP_MIN_LEN = 24
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class PaperSource(Protocol):
    """Protocol for an external paper data source."""

    name: str

    def search(
        self,
        query: SearchQuery,
        *,
        max_results: int,
    ) -> Sequence[Paper]:
        """Search papers using this source."""
        raise NotImplementedError

    def close(self) -> None:
        """Close resources held by source."""
        raise NotImplementedError


@dataclass(slots=True)
class PaperSearchService:
    """Application service that searches papers across configured sources."""

    sources: tuple[PaperSource, ...]
    dedup_store: SqliteDeduplicateStore | None = None

    def search(
        self,
        query: SearchQuery,
        *,
        max_results: int = 20,
    ) -> Sequence[Paper]:
        """Search papers via all configured sources.

        Args:
            query: Source-agnostic structured query.
            max_results: Maximum number of results to return.

        Returns:
            A sequence of Paper.
        """
        if not self.sources:
            raise RuntimeError("No search sources are configured")

        aggregated: list[Paper] = []
        failed_sources: list[str] = []
        for source in self.sources:
            source_name = getattr(source, "name", "unknown")
            try:
                papers = source.search(query, max_results=max_results)
            except Exception as error:  # noqa: BLE001 - source failure must be isolated
                failed_sources.append(source_name)
                log.warning("Search source failed: source=%s error=%s", source_name, error)
                continue

            log.info("Search source completed: source=%s count=%d", source_name, len(papers))
            aggregated.extend(papers)

        if len(failed_sources) == len(self.sources):
            raise RuntimeError(f"All search sources failed: {', '.join(failed_sources)}")

        ranked = self._sort_papers(aggregated)
        unique_papers = self._deduplicate_in_batch(ranked)
        if self.dedup_store:
            unique_papers = self.dedup_store.filter_new(unique_papers)
        return unique_papers[:max_results]

    def close(self) -> None:
        """Close all sources and release external resources."""
        failed_sources: list[str] = []
        for source in self.sources:
            close_func = getattr(source, "close", None)
            if callable(close_func):
                source_name = getattr(source, "name", "unknown")
                try:
                    close_func()
                except Exception as error:  # noqa: BLE001 - close failure must be isolated
                    failed_sources.append(source_name)
                    log.warning("Search source close failed: source=%s error=%s", source_name, error)
        if failed_sources:
            log.warning("Search service close completed with failures: %s", ", ".join(failed_sources))

    def _deduplicate_in_batch(self, papers: Sequence[Paper]) -> list[Paper]:
        """Deduplicate papers inside a single search batch."""
        winners: dict[tuple[str, ...], Paper] = {}
        ordered_keys: list[tuple[str, ...]] = []

        for paper in papers:
            dedup_key = _paper_dedup_key(paper)
            if dedup_key is None:
                unique_key = ("unique", paper.source, paper.id)
                if unique_key in winners:
                    winners[unique_key] = self._pick_winner(winners[unique_key], paper)
                    continue
                ordered_keys.append(unique_key)
                winners[unique_key] = paper
                continue

            existing = winners.get(dedup_key)
            if existing is None:
                winners[dedup_key] = paper
                ordered_keys.append(dedup_key)
                continue

            winners[dedup_key] = self._pick_winner(existing, paper)

        return [winners[key] for key in ordered_keys]

    def _pick_winner(self, left: Paper, right: Paper) -> Paper:
        """Pick deterministic winner between two duplicate papers."""
        source_order = self._source_order_map()
        left_rank = _paper_rank(left, source_order=source_order)
        right_rank = _paper_rank(right, source_order=source_order)
        return left if left_rank <= right_rank else right

    def _source_order_map(self) -> dict[str, int]:
        """Return source priority map from configured source order."""
        return {getattr(source, "name", ""): index for index, source in enumerate(self.sources)}

    def _sort_papers(self, papers: Sequence[Paper]) -> list[Paper]:
        """Sort papers with stable, deterministic ordering."""
        source_order = self._source_order_map()
        return sorted(
            papers,
            key=lambda paper: (
                -int((paper.updated or paper.published or _EPOCH).timestamp()),
                source_order.get(paper.source, len(source_order)),
                paper.id,
            ),
        )


def _paper_dedup_key(paper: Paper) -> tuple[str, ...] | None:
    """Build per-batch dedup key for a paper."""
    doi_norm = _normalize_doi(paper.doi)
    if doi_norm:
        return ("doi", doi_norm)

    title_norm = _normalize_title(paper.title)
    if len(title_norm) < _TITLE_DEDUP_MIN_LEN:
        return None

    year = _paper_year(paper)
    if year is None:
        return None

    return ("title", title_norm, str(year))


def _paper_rank(paper: Paper, *, source_order: dict[str, int]) -> tuple[int, int, str]:
    """Build ranking tuple for deterministic duplicate winner selection."""
    source_rank = source_order.get(paper.source, len(source_order))
    timestamp = paper.updated or paper.published or _EPOCH
    return (source_rank, -int(timestamp.timestamp()), paper.id)


def _paper_year(paper: Paper) -> int | None:
    """Extract comparable year from paper timestamp fields."""
    timestamp = paper.published or paper.updated
    return timestamp.year if timestamp is not None else None


def _normalize_doi(doi: str | None) -> str:
    """Normalize DOI for matching across providers."""
    if doi is None:
        return ""
    normalized = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    return normalized.strip()


def _normalize_title(title: str) -> str:
    """Normalize title for conservative fallback deduplication."""
    lowered = title.casefold()
    no_punctuation = _TITLE_STRIP_RE.sub(" ", lowered)
    return _TITLE_WS_RE.sub(" ", no_punctuation).strip()
