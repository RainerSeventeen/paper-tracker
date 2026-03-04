"""Paper Search Service Layer.

Orchestrates querying multiple paper sources, then sorts and deduplicates aggregated results.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Sequence

from PaperTracker.core.dedup import resolve_timestamp
from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.services.deduplicate import deduplicate_cross_source_batch
from PaperTracker.utils.log import log

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
        """Search papers from this source using a structured query.

        Args:
            query: Source-agnostic query object describing search terms and fields.
            max_results: Maximum number of papers to return for this call.

        Returns:
            A sequence of normalized ``Paper`` objects from this source.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Release resources held by this source implementation.
        """
        raise NotImplementedError


@dataclass(slots=True)
class PaperSearchService:
    """Application service that searches papers across configured sources.

    The service does not infer source-level temporal semantics or source
    pagination behavior. It only coordinates cross-source aggregation,
    sorting, and in-batch deduplication using protocol fields.
    """

    sources: tuple[PaperSource, ...]

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
        return unique_papers[:max_results]

    def close(self) -> None:
        """Close all configured sources and release external resources.
        """
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
        """Deduplicate one aggregated batch across sources.

        Source adapters own deduplication while paging within their own fetch
        loops. This method only coordinates duplicate resolution after papers
        from all configured sources have been aggregated.
        """
        return deduplicate_cross_source_batch(
            papers,
            source_rank=self._source_order_map(),
        )

    def _source_order_map(self) -> dict[str, int]:
        """Return source priority map from configured source order."""
        return {getattr(source, "name", ""): index for index, source in enumerate(self.sources)}

    def _sort_papers(self, papers: Sequence[Paper]) -> list[Paper]:
        """Sort papers with stable, deterministic ordering."""
        source_order = self._source_order_map()
        return sorted(
            papers,
            key=lambda paper: (
                -int((resolve_timestamp(paper) or _EPOCH).timestamp()),
                source_order.get(paper.source, len(source_order)),
                paper.id,
            ),
        )
