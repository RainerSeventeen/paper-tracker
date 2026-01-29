"""Search service layer.

Provides a stable use-case API to the CLI and integrates different data sources
via the `PaperSource` protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from PaperTracker.core.models import Paper
from PaperTracker.core.query import SearchQuery
from PaperTracker.utils.log import log


class PaperSource(Protocol):
    """Protocol for an external paper data source.

    Implementations adapt a provider (arXiv, Semantic Scholar, etc.) into the
    internal `Paper` model.
    """

    name: str

    def search(
        self,
        query: SearchQuery,
        *,
        max_results: int,
        sort_by: str,
        sort_order: str,
    ) -> Sequence[Paper]:
        """Search papers using this source.

        Args:
            query: Source-agnostic structured query.
            max_results: Maximum number of results to return.
            sort_by: arXiv sorting field (source-specific).
            sort_order: Sorting order (source-specific).

        Returns:
            A sequence of Paper.
        """
        raise NotImplementedError


@dataclass(slots=True)
class PaperSearchService:
    """Application service that searches papers via a configured source."""

    source: PaperSource

    def search(
        self,
        query: SearchQuery,
        *,
        max_results: int = 20,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
    ) -> Sequence[Paper]:
        """Search papers via the configured PaperSource.

        Args:
            query: Source-agnostic structured query.
            max_results: Maximum number of results to return.
            sort_by: Sorting field.
            sort_order: Sorting order.

        Returns:
            A sequence of Paper.
        """
        log.debug(
            "Search service start: source=%s max_results=%s sort_by=%s sort_order=%s",
            getattr(self.source, "name", "unknown"),
            max_results,
            sort_by,
            sort_order,
        )
        return self.source.search(
            query,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order,
        )
